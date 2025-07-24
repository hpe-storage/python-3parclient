# (c) Copyright 2012-2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
""" HPE 3PAR REST Client.

.. module: client
.. moduleauthor: Walter A. Boring IV
.. moduleauthor: Kurt Martin

:Author: Walter A. Boring IV
:Description: This is the 3PAR Client that talks to 3PAR's REST WSAPI Service.
It provides the ability to provision 3PAR volumes, VLUNs, CPGs.  This version
also supports running actions on the 3PAR that use SSH.

This client requires and works with 3PAR InForm 3.1.3 MU1 firmware

"""
import copy
import re
import time
import uuid
import logging

try:
    # For Python 3.0 and later
    from urllib.parse import quote
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import quote

from hpe3parclient import exceptions, http, ssh
from hpe3parclient import showport_parser

logger = logging.getLogger(__name__)

# =================
# 3PAR API VERSION CONSTANTS
# =================
MIN_CLIENT_VERSION = '4.2.10'
DEDUP_API_VERSION = 30201120
FLASH_CACHE_API_VERSION = 30201200
COMPRESSION_API_VERSION = 30301215
SRSTATLD_API_VERSION = 30201200
REMOTE_COPY_API_VERSION = 30202290
API_VERSION_2023 = 100000000

# =================
# 3PAR STATISTICAL CONSTANTS
# =================
# Input/output (total read/write) operations per second.
THROUGHPUT = 'throughput'
# Data processed (total read/write) per unit time: kilobytes per second.
BANDWIDTH = 'bandwidth'
# Response time (total read/write): microseconds.
LATENCY = 'latency'
# IO size (total read/write): kilobytes.
IO_SIZE = 'io_size'
# Queue length for processing IO requests
QUEUE_LENGTH = 'queue_length'
# Average busy percentage
AVG_BUSY_PERC = 'avg_busy_perc'

# =================
# 3PAR VLUN TYPE CONSTANTS
# =================
VLUN_TYPE_EMPTY = 1
VLUN_TYPE_PORT = 2
VLUN_TYPE_HOST = 3
VLUN_TYPE_MATCHED_SET = 4
VLUN_TYPE_HOST_SET = 5

# =================
# 3PAR PROVISIONING CONSTANTS
# =================
THIN = 2
DEDUP = 6
CONVERT_TO_THIN = 1
CONVERT_TO_FULL = 2
CONVERT_TO_DEDUP = 3

# =================
# 3PAR FLASH CACHE CONSTANTS
# =================
FLASH_CACHE_ENABLED = 1
FLASH_CACHE_DISABLED = 2

# =================
# 3PAR REPLICATION CONSTANTS
# =================
SYNC = 1
PERIODIC = 2
RC_ACTION_CHANGE_TO_PRIMARY = 7

# =================
# 3PAR LICENSE CONSTANTS
# =================
PRIORITY_OPT_LIC = "Priority Optimization"
THIN_PROV_LIC = "Thin Provisioning"
REMOTE_COPY_LIC = "Remote Copy"
SYSTEM_REPORTER_LIC = "System Reporter"
COMPRESSION_LIC = "Compression"


class HPE3ParClient(object):
    """ The 3PAR REST API Client.

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080/api/v1
    :type api_url: str

    """

    CHAP_INITIATOR = 1
    CHAP_TARGET = 2

    PORT_MODE_TARGET = 2
    PORT_MODE_INITIATOR = 3
    PORT_MODE_PEER = 4

    PORT_TYPE_HOST = 1
    PORT_TYPE_DISK = 2
    PORT_TYPE_FREE = 3
    PORT_TYPE_IPORT = 4
    PORT_TYPE_RCFC = 5
    PORT_TYPE_PEER = 6
    PORT_TYPE_RCIP = 7
    PORT_TYPE_ISCSI = 8
    PORT_TYPE_CNA = 9

    PORT_PROTO_FC = 1
    PORT_PROTO_ISCSI = 2
    PORT_PROTO_FCOE = 3
    PORT_PROTO_IP = 4
    PORT_PROTO_SAS = 5

    PORT_STATE_READY = 4
    PORT_STATE_SYNC = 5
    PORT_STATE_OFFLINE = 10

    SET_MEM_ADD = 1
    SET_MEM_REMOVE = 2
    SET_RESYNC_PHYSICAL_COPY = 3
    SET_STOP_PHYSICAL_COPY = 4

    STOP_PHYSICAL_COPY = 1
    RESYNC_PHYSICAL_COPY = 2
    GROW_VOLUME = 3
    PROMOTE_VIRTUAL_COPY = 4
    VIRTUAL_COPY = 3

    TUNE_VOLUME = 6
    TPVV = 1
    FPVV = 2
    TDVV = 3
    CONVERT_TO_DECO = 4

    TARGET_TYPE_VVSET = 1
    TARGET_TYPE_SYS = 2

    PRIORITY_LOW = 1
    PRIORITY_NORMAL = 2
    PRIORITY_HIGH = 3

    TASK_TYPE_VV_COPY = 1
    TASK_TYPE_PHYS_COPY_RESYNC = 2
    TASK_TYPE_MOVE_REGIONS = 3
    TASK_TYPE_PROMOTE_SV = 4
    TASK_TYPE_REMOTE_COPY_SYNC = 5
    TASK_TYPE_REMOTE_COPY_REVERSE = 6
    TASK_TYPE_REMOTE_COPY_FAILOVER = 7
    TASK_TYPE_REMOTE_COPY_RECOVER = 8
    TASK_TYPE_REMOTE_COPY_RESTORE = 9
    TASK_TYPE_COMPACT_CPG = 10
    TASK_TYPE_COMPACT_IDS = 11
    TASK_TYPE_SNAPSHOT_ACCOUNTING = 12
    TASK_TYPE_CHECK_VV = 13
    TASK_TYPE_SCHEDULED_TASK = 14
    TASK_TYPE_SYSTEM_TASK = 15
    TASK_TYPE_BACKGROUND_TASK = 16
    TASK_TYPE_IMPORT_VV = 17
    TASK_TYPE_ONLINE_COPY = 18
    TASK_TYPE_CONVERT_VV = 19

    TASK_DONE = 1
    TASK_ACTIVE = 2
    TASK_CANCELLED = 3
    TASK_FAILED = 4

    # build contains major minor mj=3 min=01 main=03 build=230
    # When updating these, make sure desc is appropriate for error messages
    # and make sure the version overrides in file_client are still OK.
    HPE3PAR_WS_MIN_BUILD_VERSION = 30103230
    HPE3PAR_WS_MIN_BUILD_VERSION_DESC = '3.1.3 MU1'

    HPE3PAR_WS_PRIMERA_MIN_BUILD_VERSION = 40000128
    HPE3PAR_WS_PRIMERA_MIN_BUILD_VERSIONDESC = '4.2.0'

    # Minimum build version needed for VLUN query support.
    HPE3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY = 30201292
    HPE3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY_DESC = '3.2.1 MU2'
    HPE3PAR_WS_MIN_FLASH_CACHE_API_VERSION = 30201200
    WSAPI_MIN_VERSION_COMPRESSION_SUPPORT = '1.6.0'

    VLUN_TYPE_EMPTY = 1
    VLUN_TYPE_PORT = 2
    VLUN_TYPE_HOST = 3
    VLUN_TYPE_MATCHED_SET = 4
    VLUN_TYPE_HOST_SET = 5

    VLUN_MULTIPATH_UNKNOWN = 1
    VLUN_MULTIPATH_ROUND_ROBIN = 2
    VLUN_MULTIPATH_FAILOVER = 3

    CPG_RAID_R0 = 1  # RAID 0
    CPG_RAID_R1 = 2  # RAID 1
    CPG_RAID_R5 = 3  # RAID 5
    CPG_RAID_R6 = 4  # RAID 6

    CPG_HA_PORT = 1  # Support failure of a port.
    CPG_HA_CAGE = 2  # Support failure of a drive cage.
    CPG_HA_MAG = 3  # Support failure of a drive magazine.

    # Lowest numbered available chunklets, where transfer rate is the fastest.
    CPG_CHUNKLET_POS_PREF_FIRST = 1
    # Highest numbered available chunklets, where transfer rate is the slowest.
    CPG_CHUNKLET_POS_PREF_LAST = 2

    CPG_DISK_TYPE_FC = 1  # Fibre Channel
    CPG_DISK_TYPE_NL = 2  # Near Line
    CPG_DISK_TYPE_SSD = 3  # SSD

    HOST_EDIT_ADD = 1
    HOST_EDIT_REMOVE = 2

    HOST_PERSONA_GENERIC = 1
    HOST_PERSONA_GENERIC_ALUA = 2
    HOST_PERSONA_GENERIC_LEGACY = 3
    HOST_PERSONA_HPUX_LEGACY = 4
    HOST_PERSONA_AIX_LEGACY = 5
    HOST_PERSONA_EGENERA = 6
    HOST_PERSONA_ONTAP_LEGACY = 7
    HOST_PERSONA_VMWARE = 8
    HOST_PERSONA_OPENVMS = 9
    HOST_PERSONA_HPUX = 10
    HOST_PERSONA_WINDOWS_SERVER = 11

    CHAP_OPERATION_MODE_INITIATOR = 1
    CHAP_OPERATION_MODE_TARGET = 2

    FLASH_CACHE_ENABLED = 1
    FLASH_CACHE_DISABLED = 2

    RC_ACTION_CHANGE_DIRECTION = 6
    RC_ACTION_CHANGE_TO_PRIMARY = 7
    RC_ACTION_MIGRATE_GROUP = 8
    RC_ACTION_CHANGE_TO_SECONDARY = 9
    RC_ACTION_CHANGE_TO_NATURUAL_DIRECTION = 10
    RC_ACTION_OVERRIDE_FAIL_SAFE = 11
    valid_persona_values = ['2 - Generic-ALUA',
                            '1 - Generic',
                            '3 - Generic-legacy',
                            '4 - HPUX-legacy',
                            '5 - AIX-legacy',
                            '6 - EGENERA',
                            '7 - ONTAP-legacy',
                            '8 - VMware',
                            '9 - OpenVMS',
                            '10 - HPUX',
                            '11 - WindowsServer']

    def __init__(self, api_url, debug=False, secure=False, timeout=None,
                 suppress_ssl_warnings=False):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(
            self.api_url, secure=secure,
            timeout=timeout, suppress_ssl_warnings=suppress_ssl_warnings)
        api_version = None
        self.ssh = None
        self.vlun_query_supported = False
        self.primera_supported = False
        self.compression_supported = False

        self.debug_rest(debug)

        try:
            api_version = self.getWsApiVersion()
        except exceptions as ex:
            ex_desc = ex.get_description()

            if (ex_desc and ("Unable to find the server at" in ex_desc or
                             "Only absolute URIs are allowed" in ex_desc)):
                raise exceptions.HTTPBadRequest(ex_desc)
            if (ex_desc and "SSL Certificate Verification Failed" in ex_desc):
                raise exceptions.SSLCertFailed()
            else:
                msg = ('Error: \'%s\' - Error communicating with the 3PAR WS. '
                       'Check proxy settings. If error persists, either the '
                       '3PAR WS is not running or the version of the WS is '
                       'not supported.') % ex_desc
                raise exceptions.UnsupportedVersion(msg)

        # Note the build contains major, minor, maintenance and build
        # e.g. 30102422 is 3 01 02 422
        # therefore all we need to compare is the build
        if (api_version is None or
                api_version['build'] < self.HPE3PAR_WS_MIN_BUILD_VERSION):
            raise exceptions.UnsupportedVersion(
                'Invalid 3PAR WS API, requires version, %s' %
                self.HPE3PAR_WS_MIN_BUILD_VERSION_DESC)

        # Check for VLUN query support.
        if (api_version['build'] >=
                self.HPE3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY):
            self.vlun_query_supported = True
        if (api_version['build'] >=
                self.HPE3PAR_WS_PRIMERA_MIN_BUILD_VERSION):
            self.primera_supported = True

        current_wsapi_version = '{}.{}.{}'.format(api_version.get('major'),
                                                  api_version.get('minor'),
                                                  api_version.get('revision'))
        if current_wsapi_version >= self.WSAPI_MIN_VERSION_COMPRESSION_SUPPORT:
            self.compression_supported = True

    

    def validate_persona(self, persona_value):
        """Validate persona value.

        If the passed in persona_value is not valid, raise InvalidInput,
        otherwise return the persona ID.

        :param persona_value:
        :raises exception.InvalidInput:
        :returns: persona ID
        """
        if persona_value not in self.valid_persona_values:
            err = (_("Must specify a valid persona %(valid)s,"
                     "value '%(persona)s' is invalid.") %
                   {'valid': self.valid_persona_values,
                   'persona': persona_value})
            LOG.error(err)
            raise exception.InvalidInput(reason=err)
        # persona is set by the id so remove the text and return the id
        # i.e for persona '1 - Generic' returns 1
        persona_id = persona_value.split(' ')
        return persona_id[0]
                
    def check_replication_flags(self, options, required_flags):
        for flag in required_flags:
            if not options.get(flag, None):
                msg = (_('%s is not set and is required for the replication '
                         'device to be valid.') % flag)
                LOG.error(msg)
                raise exception.InvalidInput(reason=msg)

    def build_nsp(self, portPos):
        return '%s:%s:%s' % (portPos['node'],
                             portPos['slot'],
                             portPos['cardPort'])

    def build_portPos(self, nsp):
        split = nsp.split(":")
        portPos = {}
        portPos['node'] = int(split[0])
        portPos['slot'] = int(split[1])
        portPos['cardPort'] = int(split[2])
        return portPos

    def get_active_target_ports(self, remote_client=None):
        if remote_client:
            client_obj = remote_client
            ports = remote_client.getPorts()
        else:
            client_obj = self
            ports = self.getPorts()

        target_ports = []
        for port in ports['members']:
            if (
                port['mode'] == client_obj.PORT_MODE_TARGET and
                port['linkState'] == client_obj.PORT_STATE_READY
            ):
                port['nsp'] = self.build_nsp(port['portPos'])
                target_ports.append(port)

        return target_ports

    def get_active_fc_target_ports(self, remote_client=None):
        ports = self.get_active_target_ports(remote_client)
        if remote_client:
            client_obj = remote_client
        else:
            client_obj = self

        fc_ports = []
        for port in ports:
            if port['protocol'] == client_obj.PORT_PROTO_FC:
                fc_ports.append(port)

        return fc_ports

    def get_active_iscsi_target_ports(self, remote_client=None):
        ports = self.get_active_target_ports(remote_client)
        if remote_client:
            client_obj = remote_client
        else:
            client_obj = self

        iscsi_ports = []
        for port in ports:
            if port['protocol'] == client_obj.PORT_PROTO_ISCSI:
                iscsi_ports.append(port)

        return iscsi_ports

    def get_flash_cache_policy(self, hpe3par_keys):
        if hpe3par_keys is not None:
            # First check list of extra spec keys
            val = self._get_key_value(hpe3par_keys, 'flash_cache', None)
            wsapiVersion = api_version['build']
            if val is not None:
                # If requested, see if supported on back end
                if wsapiVersion < HPE3PAR_WS_MIN_FLASH_CACHE_API_VERSION:
                    err = (_("Flash Cache Policy requires "
                             "WSAPI version '%(fcache_version)s' "
                             "version '%(version)s' is installed.") %
                           {'fcache_version': HPE3PAR_WS_MIN_FLASH_CACHE_API_VERSION,
                            'version': wsapiVersion})
                    LOG.error(err)
                    raise exception.InvalidInput(reason=err)
                else:
                    if val.lower() == 'true':
                        return self.client.FLASH_CACHE_ENABLED
                    else:
                        return self.client.FLASH_CACHE_DISABLED

        return None

    def manage_existing_volume_utility(self, client_obj, volume, existing_ref, target_vol_name,
                                     get_volume_callback, get_volume_type_callback,
                                     retype_callback, log_callback):
        """Utility for managing existing 3PAR volumes."""
        try:
            vol = get_volume_callback(target_vol_name)
        except Exception:
            err = (_("Virtual volume '%s' doesn't exist on array.") % target_vol_name)
            return {'success': False, 'error': err}

        # Check for valid persona even if we don't use it until attach time
        if volume.get('volume_type_id', None):
            volume_type = get_volume_type_callback(volume["volume_type_id"])
            hpe3par_keys = self.get_keys_by_volume_type(volume_type, 
                                                       valid_hpe3par_keys={'persona'})
            try:
                self.get_persona_type(volume, hpe3par_keys)
            except Exception as ex:
                reason = (_("Invalid persona specified, "
                          "valid personas are: %(valid)s. "
                          "Error: %(err)s") % 
                        {'valid': self.valid_persona_values, 'err': str(ex)})
                return {'success': False, 'error': reason, 'error_type': 'InvalidInput'}
                
            try:
                retype_callback(volume, volume_type)
            except Exception as ex:
                return {'success': False, 'error': str(ex), 'error_type': 'Retype'}

        # Build the new comment info for the volume
        new_comment = {}
        if volume.get('display_name'):
            display_name = volume['display_name']
            new_comment['display_name'] = display_name
        elif 'comment' in vol:
            display_name = self._get_3par_vol_comment_value(vol['comment'], 'display_name')
            if display_name:
                new_comment['display_name'] = display_name
        else:
            display_name = None

        # Generate the new volume information based on the new ID.
        new_vol_name = self.get_3par_vol_name(volume['id'])
        name = 'volume-' + volume['id']
        new_comment['volume_id'] = volume['id']
        new_comment['name'] = name
        self.add_name_id_to_comment(new_comment, volume)
        if volume.get('display_description'):
            new_comment['description'] = volume['display_description']
        else:
            new_comment['description'] = ""

        new_vals = {'newName': new_vol_name,
                    'comment': self.json_encode_dict(new_comment)}

        # Update the existing volume with new name and comments
        try:
            client_obj.modifyVolume(target_vol_name, new_vals)
        except Exception as ex:
            return {'success': False, 'error': str(ex)}

        log_callback("Virtual volume '%(ref)s' renamed to '%(new)s'.",
                    {'ref': existing_ref.get('source-name', target_vol_name), 'new': new_vol_name})

        updates = {'display_name': display_name}
        log_callback("Virtual volume %(disp)s '%(new)s' is now being managed.",
                    {'disp': display_name, 'new': new_vol_name})

        return {'success': True, 'updates': updates}

    def build_unmanage_params(self, volume, vol_name):
        """Build parameters for unmanaging a volume."""
        new_name = self.get_3par_unm_name(volume['id'])
        display_name = volume.get('display_name', 'Unknown')
        return {
            'current_name': vol_name,
            'new_name': new_name,
            'display_name': display_name
        }

    def create_volume_utility(self, client_obj, volume, type_info, comments, vvs_name, qos,
                             flash_cache, compression, consis_group_snap_type, cg_id,
                             group, hpe_tiramisu, api_version, log_callback):
        """Utility for creating 3PAR volumes with comprehensive parameter handling."""
        try:
            cpg = type_info['cpg']
            snap_cpg = type_info['snap_cpg']
            tpvv = type_info['tpvv']
            tdvv = type_info['tdvv']
            volume_type = type_info['volume_type']
            
            volume_name = self.get_3par_vol_name(volume['id'])
            
            # Encode comments as JSON
            comment_dict = {}
            if isinstance(comments, dict):
                comment_dict = comments.copy()
            self.add_name_id_to_comment(comment_dict, volume)
            
            # Format size in MiB
            size = int(volume['size']) * 1024

            # Additional volume options
            optional = {'comment': self.json_encode_dict(comment_dict),
                       'snapCPG': snap_cpg}
            
            if tpvv:
                optional['tpvv'] = tpvv
            if tdvv:
                optional['tdvv'] = tdvv

            # Handle compression if supported
            if compression is not None and api_version >= self.COMPRESSION_API_VERSION:
                optional['compression'] = compression

            log_callback('CREATE VOLUME (%s) on CPG (%s)', volume_name, cpg)

            # Create the volume
            client_obj.createVolume(volume_name, cpg, size, optional)
            
            replication_flag = False
            
            return {
                'success': True,
                'volume_name': volume_name,
                'cpg': cpg,
                'replication_flag': replication_flag,
                'hpe_tiramisu': hpe_tiramisu
            }

        except Exception as ex:
            error_msg = str(ex)
            if 'Duplicate name' in error_msg or 'already exists' in error_msg:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'Duplicate'
                }
            elif 'Invalid' in error_msg:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'Invalid'
                }
            else:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'CinderException'
                }

    def create_cloned_volume_utility(self, client_obj, volume, src_vref, 
                                   get_vol_name_callback, get_volume_settings_callback,
                                   create_volume_callback, get_model_update_callback,
                                   log_callback):
        """Utility for creating cloned volumes."""
        try:
            orig_name = get_vol_name_callback(src_vref['id'])
            clone_name = get_vol_name_callback(volume['id'])
            
            log_callback('CREATE CLONED VOLUME (%s) from (%s)', clone_name, orig_name)
            
            # Check if source volume exists
            try:
                client_obj.getVolume(orig_name)
            except Exception:
                return {
                    'success': False,
                    'error': f"Source volume {orig_name} not found",
                    'error_type': 'NotFound'
                }

            # Create volume first
            create_result = create_volume_callback(volume)
            
            # Build clone comment
            comment = {}
            self.add_name_id_to_comment(comment, volume)
            comment['cloned_from'] = orig_name
            
            optional = {'comment': self.json_encode_dict(comment)}
            
            # Create physical copy (clone)
            client_obj.createSnapshot(clone_name, orig_name, optional)
            
            return {
                'success': True,
                'clone_name': clone_name,
                'model_update': create_result
            }
            
        except Exception as ex:
            error_msg = str(ex)
            if 'Duplicate' in error_msg:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'Duplicate'
                }
            else:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'CinderException'
                }

    def retype_pre_checks_utility(self, volume, host, new_persona, old_cpg, new_cpg, new_snap_cpg):
        """Utility for retype parameter validation."""
        from cinder import exception
        from cinder.i18n import _
        
        if new_persona:
            self.validate_persona(new_persona)

        if host is not None:
            host_info = host['capabilities']['location_info'].split(':')
            if len(host_info) >= 3:
                host_type, host_id = host_info[0], host_info[1]
                
                if host_type != 'HPE3PARDriver':
                    reason = (_("Cannot retype from HPE3PARDriver to %s.") % host_type)
                    raise exception.InvalidHost(reason=reason)

                sys_info = self.getStorageSystemInfo()
                if host_id != sys_info['serialNumber']:
                    reason = (_("Cannot retype from one 3PAR array to another."))
                    raise exception.InvalidHost(reason=reason)

        # Validate snap_cpg
        if not new_snap_cpg or new_snap_cpg.isspace():
            reason = (_("Invalid new snapCPG name for retype. new_snap_cpg='%s'.") % new_snap_cpg)
            raise exception.InvalidInput(reason)

    def retype_volume_utility(self, client_obj, volume, volume_name, new_type_name, new_type_id, host,
                             new_persona, old_cpg, new_cpg, old_snap_cpg, new_snap_cpg,
                             old_tpvv, new_tpvv, old_tdvv, new_tdvv,
                             old_vvs, new_vvs, old_qos, new_qos,
                             old_flash_cache, new_flash_cache,
                             old_comment, new_compression,
                             retype_pre_checks_callback, task_waiter_callback):
        """Utility for volume retype operations."""
        # Run pre-checks
        retype_pre_checks_callback(volume, host, new_persona, old_cpg, new_cpg, new_snap_cpg)
        
        # Simplified retype logic
        if old_cpg != new_cpg:
            task_optional = {'userCPG': new_cpg, 'snapCPG': new_snap_cpg}
            
            if old_tpvv != new_tpvv:
                if new_tpvv:
                    task_optional['conversionOperation'] = self.CONVERT_TO_THIN
                else:
                    task_optional['conversionOperation'] = self.CONVERT_TO_FULL
                    
            if old_tdvv != new_tdvv and new_tdvv:
                task_optional['conversionOperation'] = self.CONVERT_TO_DECO

            body = client_obj.tuneVolume(volume_name, task_optional)
            task_id = body['taskid']
            status = task_waiter_callback(client_obj, task_id).wait_for_task()
            if status['status'] != self.TASK_DONE:
                raise Exception(f'Tune volume task failed: {status}')

    def do_volume_replication_setup_utility(self, client_obj, volume, replication_targets, api_version,
                                           retype=False, dist_type_id=None,
                                           get_volume_type_callback=None, get_volume_settings_callback=None,
                                           get_vol_name_callback=None, is_volume_in_rcg_callback=None,
                                           destroy_replication_callback=None, log_callback=None):
        """Utility for setting up volume replication."""
        from cinder.volume import volume_utils
        from cinder import exception
        from cinder.i18n import _
        
        rcg_name = self.get_3par_rcg_name(volume)
        vol_name = get_vol_name_callback(volume['id'])
        
        # Check if already in remote copy group
        if is_volume_in_rcg_callback and is_volume_in_rcg_callback(volume):
            try:
                client_obj.startRemoteCopy(rcg_name)
            except Exception:
                pass
            return True

        try:
            # Get replication settings from volume type
            volume_type = get_volume_type_callback(volume["volume_type_id"])
            extra_specs = volume_type.get("extra_specs", {})
            
            replication_mode = extra_specs.get('replication:mode', 'sync')
            replication_mode_num = self._get_remote_copy_mode_num(replication_mode)
            replication_sync_period = extra_specs.get('replication:sync_period', 900)
            
            if replication_sync_period:
                replication_sync_period = int(replication_sync_period)
                
            vol_settings = get_volume_settings_callback(volume)
            local_cpg = vol_settings['cpg']

            # Build RCG targets
            rcg_targets = []
            for target in replication_targets:
                if target['replication_mode'] == replication_mode_num:
                    cpg = self.get_cpg_from_cpg_map(target['cpg_map'], local_cpg)
                    rcg_target = {'targetName': target['backend_id'],
                                  'mode': replication_mode_num,
                                  'userCPG': cpg}
                    rcg_targets.append(rcg_target)

            # Create remote copy group
            optional = {'localUserCPG': local_cpg}
            pool = volume_utils.extract_host(volume['host'], level='pool')
            domain = self.get_domain(pool)
            if domain:
                optional["domain"] = domain
                
            client_obj.createRemoteCopyGroup(rcg_name, rcg_targets, optional)
            
            # Add volume to RCG
            rcg_vol_targets = []
            for target in replication_targets:
                if target['replication_mode'] == replication_mode_num:
                    rcg_target = {'targetName': target['backend_id'],
                                  'secVolumeName': vol_name}
                    rcg_vol_targets.append(rcg_target)
                    
            client_obj.addVolumeToRemoteCopyGroup(rcg_name, vol_name,
                                                 rcg_vol_targets,
                                                 optional={'volumeAutoCreation': True})

            # Start remote copy
            client_obj.startRemoteCopy(rcg_name)
            return True
            
        except Exception as ex:
            if destroy_replication_callback:
                destroy_replication_callback(volume, retype=retype)
            raise ex

    def do_volume_replication_destroy_utility(self, client_obj, volume, rcg_name, retype,
                                             get_vol_name_callback, delete_vvset_callback, log_callback):
        """Utility for destroying volume replication."""
        from hpe3parclient import exceptions as hpeexceptions
        
        if not rcg_name:
            rcg_name = self.get_3par_rcg_name(volume)
        vol_name = get_vol_name_callback(volume['id'])

        # Stop remote copy
        try:
            client_obj.stopRemoteCopy(rcg_name)
        except Exception:
            pass

        # Remove volume from remote copy group
        try:
            client_obj.removeVolumeFromRemoteCopyGroup(rcg_name, vol_name, removeFromTarget=True)
        except Exception:
            pass

        # Remove remote copy group
        try:
            client_obj.removeRemoteCopyGroup(rcg_name)
        except Exception:
            pass

        # Delete volume
        try:
            if not retype:
                client_obj.deleteVolume(vol_name)
        except hpeexceptions.HTTPConflict as ex:
            if ex.get_code() == 34:
                delete_vvset_callback(volume)
                client_obj.deleteVolume(vol_name)
        except Exception:
            pass

    def stop_remote_copy_group_utility(self, client_obj, rcg_name, log_callback):
        """Utility for stopping remote copy group."""
        try:
            client_obj.stopRemoteCopy(rcg_name)
            return True
        except Exception as ex:
            log_callback(f"Failed to stop remote copy group {rcg_name}: {str(ex)}")
            return False

    def start_remote_copy_group_utility(self, client_obj, rcg_name, log_callback):
        """Utility for starting remote copy group."""
        try:
            client_obj.startRemoteCopy(rcg_name)
            return True
        except Exception as ex:
            log_callback(f"Failed to start remote copy group {rcg_name}: {str(ex)}")
            return False

    def delete_group_utility(self, client_obj, group, volumes,
                            remove_volumes_rcg_callback, delete_volume_callback,
                            get_vvs_name_callback, log_callback):
        """Utility for deleting volume groups."""
        from hpe3parclient import exceptions as hpeexceptions
        from cinder.objects import fields
        
        if group.is_replicated:
            remove_volumes_rcg_callback(group, volumes)
            
        try:
            cg_name = get_vvs_name_callback(group.id)
            client_obj.deleteVolumeSet(cg_name)
        except hpeexceptions.HTTPNotFound:
            log_callback(f"Virtual Volume Set '{cg_name}' doesn't exist on array.")
        except hpeexceptions.HTTPConflict as e:
            log_callback(f"Conflict detected in Virtual Volume Set {cg_name}: {e}")

        volume_model_updates = []
        for volume in volumes:
            volume_update = {'id': volume.get('id')}
            try:
                delete_volume_callback(volume)
                volume_update['status'] = 'deleted'
            except Exception as ex:
                volume_update['status'] = 'error'
            volume_model_updates.append(volume_update)
            
        model_update = {'status': group.status}
        return model_update, volume_model_updates

    def update_group_utility(self, client_obj, group, add_volumes, remove_volumes,
                            get_vvs_name_callback, get_vol_name_callback,
                            check_rep_status_callback, stop_rcg_callback, start_rcg_callback,
                            check_replication_matched_callback, add_vol_to_rcg_callback,
                            remove_vol_from_rcg_callback, log_callback):
        """Utility for updating group membership."""
        from cinder.objects import fields
        from cinder import exception
        from cinder.i18n import _
        from hpe3parclient import exceptions as hpeexceptions
        
        add_volume = []
        remove_volume = []
        vol_rep_status = fields.ReplicationStatus.ENABLED
        volume_set_name = get_vvs_name_callback(group.id)

        if group.is_replicated:
            check_rep_status_callback(group)
            stop_rcg_callback(group)

        # Process volumes to add
        if add_volumes:
            for volume in add_volumes:
                volume_name = get_vol_name_callback(volume)
                vol_snap_enable = self.is_volume_group_snap_type(volume.get('volume_type'))
                
                if vol_snap_enable:
                    check_replication_matched_callback(volume, group)
                    if group.is_replicated:
                        add_vol_to_rcg_callback(group, volume)
                        update = {'id': volume.get('id'), 'replication_status': vol_rep_status}
                        add_volume.append(update)
                    client_obj.addVolumeToVolumeSet(volume_set_name, volume_name)
                else:
                    msg = (_('Volume with volume id %s is not supported') % volume['id'])
                    raise exception.InvalidInput(reason=msg)

        # Process volumes to remove
        if remove_volumes:
            for volume in remove_volumes:
                volume_name = get_vol_name_callback(volume)
                if group.is_replicated:
                    remove_vol_from_rcg_callback(group, volume)
                    update = {'id': volume.get('id'), 'replication_status': None}
                    remove_volume.append(update)
                client_obj.removeVolumeFromVolumeSet(volume_set_name, volume_name)

        if group.is_replicated:
            start_rcg_callback(group)

        return None, add_volume, remove_volume

    def create_group_snapshot_utility(self, client_obj, group_snapshot, snapshots,
                                     get_snap_name_callback, log_callback):
        """Utility for creating group snapshots."""
        from cinder.objects import fields
        from cinder import exception
        from cinder.i18n import _
        
        cg_id = group_snapshot.group_id
        snap_shot_name = get_snap_name_callback(group_snapshot.id)
        copy_of_name = self.get_3par_vvs_name(cg_id)
        
        # Build comment
        extra = {'volume_id': group_snapshot.id,
                 'group_id': cg_id,
                 'display_name': group_snapshot.name or "",
                 'description': group_snapshot.description or ""}

        optional = {'comment': self.json_encode_dict(extra)}

        try:
            client_obj.createSnapshotOfVolumeSet(snap_shot_name, copy_of_name, optional=optional)
        except Exception as ex:
            msg = _('There was an error creating the cgsnapshot: %s') % str(ex)
            log_callback(msg)
            raise exception.InvalidInput(reason=msg)

        snapshot_model_updates = []
        for snapshot in snapshots:
            snapshot_update = {'id': snapshot['id'],
                               'status': fields.SnapshotStatus.AVAILABLE}
            snapshot_model_updates.append(snapshot_update)

        model_update = {'status': fields.GroupSnapshotStatus.AVAILABLE}
        return model_update, snapshot_model_updates

    def delete_group_snapshot_utility(self, client_obj, group_snapshot, snapshots,
                                     get_snap_name_callback, log_callback):
        """Utility for deleting group snapshots."""
        from cinder.objects import fields
        from hpe3parclient import exceptions as hpeexceptions
        
        cgsnap_name = get_snap_name_callback(group_snapshot.id)
        snapshot_model_updates = []
        
        for i, snapshot in enumerate(snapshots):
            snapshot_update = {'id': snapshot['id']}
            try:
                snap_name = cgsnap_name + "-" + str(i)
                client_obj.deleteVolume(snap_name)
                snapshot_update['status'] = fields.SnapshotStatus.DELETED
            except hpeexceptions.HTTPNotFound as ex:
                log_callback(f"Delete Snapshot id not found. Removing from cinder: {snapshot['id']}")
                snapshot_update['status'] = fields.SnapshotStatus.ERROR
            except Exception as ex:
                snapshot_update['status'] = fields.SnapshotStatus.ERROR
            snapshot_model_updates.append(snapshot_update)

        model_update = {'status': fields.GroupSnapshotStatus.DELETED}
        return model_update, snapshot_model_updates

    def manage_existing_get_size_utility(self, client_obj, target_name, 
                                        check_reserved_callback, log_callback):
        """Utility for getting size of existing volumes/snapshots."""
        from hpe3parclient import exceptions as hpeexceptions
        from cinder import exception
        from cinder.i18n import _
        from oslo_utils import units
        import math
        
        # Check if name is reserved
        if check_reserved_callback(target_name):
            reason = _("Reference must be for an unmanaged volume/snapshot.")
            raise exception.ManageExistingInvalidReference(
                existing_ref=target_name,
                reason=reason)

        # Check if volume exists
        try:
            vol = client_obj.getVolume(target_name)
        except hpeexceptions.HTTPNotFound:
            err = (_("Volume '%s' doesn't exist on array.") % target_name)
            log_callback(err)
            raise exception.InvalidInput(reason=err)

        return int(math.ceil(float(vol['sizeMiB']) / units.Ki))

    def unmanage_snapshot_utility(self, snapshot, get_snap_name_callback, 
                                 get_ums_name_callback, log_callback):
        """Utility for unmanaging snapshots."""
        from cinder import exception
        from cinder.i18n import _
        
        # Check if snapshot is from failed-over volume
        volume = snapshot['volume']
        if volume.get('replication_status') == 'failed-over':
            err = (_("Unmanaging of snapshots from failed-over volumes is not allowed."))
            raise exception.SnapshotIsBusy(snapshot_name=snapshot['id'])

        # Rename snapshot
        snap_name = get_snap_name_callback(snapshot['id'])
        new_snap_name = get_ums_name_callback(snapshot['id'])
        self.modifyVolume(snap_name, {'newName': new_snap_name})

        log_callback("Snapshot %(disp)s '%(vol)s' is no longer managed. "
                    "Snapshot renamed to '%(new)s'.",
                    {'disp': snapshot['display_name'],
                     'vol': snap_name,
                     'new': new_snap_name})

    def create_volume_with_features_utility(self, client_obj, volume, perform_replica,
                                           get_volume_settings_callback, get_vol_name_callback,
                                           check_rep_status_callback, add_vol_to_remote_group_callback,
                                           add_volume_to_vvs_callback, do_volume_replication_callback,
                                           api_version, log_callback):
        """Comprehensive utility for creating volumes with all features."""
        from cinder import exception
        
        try:
            # Build basic volume parameters
            comments = {'volume_id': volume['id'], 'name': volume['name'], 'type': 'OpenStack'}
            self.add_name_id_to_comment(comments, volume)
            
            hpe_tiramisu = False
            if volume.get('display_name'):
                comments['display_name'] = volume['display_name']

            # Get volume type settings
            type_info = get_volume_settings_callback(volume)
            volume_type = type_info['volume_type']
            vvs_name = type_info['vvs_name']
            qos = type_info['qos']
            flash_cache = self.get_flash_cache_policy(type_info['hpe3par_keys'])
            compression = self.get_compression_policy(type_info['hpe3par_keys'])

            consis_group_snap_type = False
            if volume_type is not None:
                consis_group_snap_type = self.is_volume_group_snap_type(volume_type)

            cg_id = volume.get('group_id', None)
            group = volume.get('group', None)

            # Create the basic volume
            result = self.create_volume_utility(
                client_obj, volume, type_info, comments, vvs_name, qos,
                flash_cache, compression, consis_group_snap_type, cg_id,
                group, hpe_tiramisu, api_version, log_callback
            )
            
            if not result['success']:
                if result['error_type'] == 'Duplicate':
                    raise exception.Duplicate(result['error'])
                elif result['error_type'] == 'Invalid':
                    raise exception.Invalid(result['error'])
                else:
                    raise exception.CinderException(result['error'])

            volume_name = result['volume_name']
            cpg = result['cpg']
            replication_flag = result['replication_flag']
            hpe_tiramisu = result['hpe_tiramisu']

            # Handle group operations
            if consis_group_snap_type and self.volume_of_hpe_tiramisu_type(volume):
                hpe_tiramisu = True

            if group is not None and hpe_tiramisu and group.is_replicated:
                check_rep_status_callback(group)
                add_vol_to_remote_group_callback(group, volume)
                replication_flag = True

            # Handle volume set operations
            if qos or vvs_name or flash_cache is not None:
                try:
                    add_volume_to_vvs_callback(volume, volume_name, cpg, vvs_name, qos, flash_cache)
                except exception.InvalidInput as ex:
                    client_obj.deleteVolume(volume_name)
                    raise exception.CinderException(str(ex))

            # Handle replication
            if perform_replica and self.volume_of_replicated_type(volume, hpe_tiramisu_check=True):
                if do_volume_replication_callback(volume):
                    replication_flag = True

            return self.get_model_update(volume['host'], cpg,
                                       replication=replication_flag,
                                       provider_location=self.id,
                                       hpe_tiramisu=hpe_tiramisu)

        except (exception.Duplicate, exception.Invalid, exception.InvalidInput, exception.CinderException):
            raise
        except Exception as ex:
            raise exception.CinderException(str(ex))

    def delete_snapshot_with_cleanup_utility(self, client_obj, snapshot,
                                            get_snap_name_callback, convert_to_base_callback,
                                            log_callback):
        """Utility for deleting snapshots with child volume cleanup."""
        from cinder import exception
        from cinder.i18n import _
        from hpe3parclient import exceptions as hpeexceptions
        
        snap_name = get_snap_name_callback(snapshot['id'])
        
        try:
            # Try to delete snapshot
            client_obj.deleteVolume(snap_name)
            return True
            
        except hpeexceptions.HTTPNotFound:
            # Snapshot doesn't exist, consider it deleted
            log_callback(f"Snapshot {snap_name} not found, considering it deleted")
            return True
            
        except hpeexceptions.HTTPConflict as ex:
            if ex.get_code() == 34:
                # Snapshot has children, need to handle them
                log_callback(f"Snapshot {snap_name} has children, processing...")
                
                # Get snapshot info to find children
                try:
                    snap_info = client_obj.getVolume(snap_name)
                    children = snap_info.get('copyOf', [])
                    
                    # Handle children volumes
                    if children:
                        for child_name in children:
                            try:
                                log_callback(f"Found child volume {child_name}")
                                
                                # Get volume details for conversion
                                child_vol = client_obj.getVolume(child_name)
                                
                                # Build volume object for conversion
                                v2 = child_vol.copy()
                                v2['volume_type_id'] = self._get_3par_vol_comment_value(
                                    child_vol['comment'], 'volume_type_id')
                                v2['id'] = self._get_3par_vol_comment_value(
                                    child_vol['comment'], 'volume_id')
                                v2['_name_id'] = self._get_3par_vol_comment_value(
                                    child_vol['comment'], '_name_id')
                                v2['host'] = '#' + child_vol['userCPG']
                                
                                log_callback(f'Converting to base volume type: {v2["id"]}')
                                convert_to_base_callback(v2)
                                
                            except Exception as child_ex:
                                log_callback(f"Error processing child {child_name}: {str(child_ex)}")
                                raise exception.SnapshotIsBusy(
                                    message=_("Snapshot has children and cannot be deleted"))
                    
                    # Retry deletion after handling children
                    client_obj.deleteVolume(snap_name)
                    return True
                    
                except Exception as cleanup_ex:
                    raise exception.SnapshotIsBusy(
                        message=_("Snapshot has children and cannot be deleted"))
            else:
                raise exception.SnapshotIsBusy(message=str(ex))
                
        except Exception as ex:
            raise exception.CinderException(str(ex))

    def _get_key_value(self, hpe3par_keys, key, default=None):
        if hpe3par_keys is not None and key in hpe3par_keys:
            return hpe3par_keys[key]
        else:
            return default

    def _get_boolean_key_value(self, hpe3par_keys, key, default=False):
        value = self._get_key_value(
            hpe3par_keys, key, default)
        if isinstance(value, str):
            if value.lower() == 'true':
                value = True
            else:
                value = False
        return value

    def _check_license_enabled(self, valid_licenses,
                               license_to_check, capability):
        """Check a license against valid licenses on the array."""
        if valid_licenses:
            for license in valid_licenses:
                if license_to_check in license.get('name'):
                    return True
            LOG.debug("'%(capability)s' requires a '%(license)s' "
                      "license which is not installed.",
                      {'capability': capability,
                       'license': license_to_check})
        return False

    def get_compression_policy(self, hpe3par_keys):
        if hpe3par_keys is not None:
            # here it should return true/false/None
            val = self._get_key_value(hpe3par_keys, 'compression', None)
            compression_support = False
        if val is not None:
            info = self.getStorageSystemInfo()
            if 'licenseInfo' in info:
                if 'licenses' in info['licenseInfo']:
                    valid_licenses = info['licenseInfo']['licenses']
                    compression_support = self._check_license_enabled(
                        valid_licenses, self.COMPRESSION_LIC,
                        "Compression")
            # here check the wsapi version
            if self.API_VERSION < COMPRESSION_API_VERSION:
                err = (_("Compression Policy requires "
                         "WSAPI version '%(compression_version)s' "
                         "version '%(version)s' is installed.") %
                       {'compression_version': COMPRESSION_API_VERSION,
                        'version': self.API_VERSION})
                LOG.error(err)
                raise exception.InvalidInput(reason=err)
            else:
                if val.lower() == 'true':
                    if not compression_support:
                        msg = _('Compression is not supported on '
                                'underlying hardware')
                        LOG.error(msg)
                        raise exception.InvalidInput(reason=msg)
                    return True
                else:
                    return False
        return None

    def _get_3par_vol_comment(self, volume_name):
        vol = self.getVolume(volume_name)
        if 'comment' in vol:
            return vol['comment']
        return None   

    def _get_3par_vol_comment_value(self, vol_comment, key):
        comment_dict = dict(ast.literal_eval(vol_comment))
        if key in comment_dict:
            return comment_dict[key]
        return None

    def get_next_word(self, s, search_string):
        """Return the next word.

        Search 's' for 'search_string', if found return the word preceding
        'search_string' from 's'.
        """
        word = re.search(search_string.strip(' ') + ' ([^ ]*)', s)
        return word.groups()[0].strip(' ')

    def is_volume_group_snap_type(self, volume_type):
        consis_group_snap_type = False
        if volume_type:
            extra_specs = volume_type.get('extra_specs')
            if 'consistent_group_snapshot_enabled' in extra_specs:
                gsnap_val = extra_specs['consistent_group_snapshot_enabled']
                consis_group_snap_type = (gsnap_val == "<is> True")
        return consis_group_snap_type

    def _is_volume_type_replicated(self, volume_type):
        replicated_type = False
        extra_specs = volume_type.get('extra_specs')
        if extra_specs and 'replication_enabled' in extra_specs:
            rep_val = extra_specs['replication_enabled']
            replicated_type = (rep_val == "<is> True")

        return replicated_type

    def _check_replication_configuration_on_volume_types(self, volume_types):
        for volume_type in volume_types:
            replicated_type = self._is_volume_type_replicated(volume_type)
            if not replicated_type:
                msg = _("replication is not set on volume type: "
                        "(id)%s") % {'id': volume_type.get('id')}
                LOG.error(msg)
                raise exception.VolumeBackendAPIException(data=msg)

    def _get_remote_copy_mode_num(self, mode):
        ret_mode = None
        if mode == "sync":
            ret_mode = self.SYNC
        if mode == "periodic":
            ret_mode = self.PERIODIC
        return ret_mode

    def is_primera_array(self):
        return self.primera_supported

    def setSSHOptions(self, ip, login, password, port=22,
                      conn_timeout=None, privatekey=None,
                      **kwargs):
        """Set SSH Options for ssh calls.

        This is used to set the SSH credentials for calls
        that use SSH instead of REST HTTP.

        """
        self.ssh = ssh.HPE3PARSSHClient(ip, login, password, port,
                                        conn_timeout, privatekey,
                                        **kwargs)

    def _run(self, cmd):
        if self.ssh is None:
            raise exceptions.SSHException('SSH is not initialized. Initialize'
                                          ' it by calling "setSSHOptions".')
        else:
            self.ssh.open()
            return self.ssh.run(cmd)

    def getWsApiVersion(self):
        """Get the 3PAR WS API version.

        :returns: Version dict

        """
        try:
            # remove everything down to host:port
            host_url = self.api_url.split('/api')
            self.http.set_url(host_url[0])
            # get the api version
            response, body = self.http.get('/api')
            return body
        finally:
            # reset the url
            self.http.set_url(self.api_url)

    def debug_rest(self, flag):
        """This is useful for debugging requests to 3PAR.

        :param flag: set to True to enable debugging
        :type flag: bool

        """
        self.http.set_debug_flag(flag)
        if self.ssh:
            self.ssh.set_debug_flag(flag)

    def login(self, username, password, optional=None):
        """This authenticates against the 3PAR wsapi server and creates a
           session.

        :param username: The username
        :type username: str
        :param password: The Password
        :type password: str

        :returns: None

        """
        try:
            self.http.authenticate(username, password, optional)
        except exceptions.HTTPUnauthorized as ex:
            msg = (_("Failed to Login to storage system (%(url)s) because %(err)s") %
                   {'url': self.api_url, 'err': ex})
            LOG.error(msg)
            raise exception.InvalidInput(reason=msg)

    def logout(self):
        """This destroys the session and logs out from the 3PAR server.
           The SSH connection to the 3PAR server is also closed.

        :returns: None

        """
        self.http.unauthenticate()
        if self.ssh:
            self.ssh.close()

    def getStorageSystemInfo(self):
        """Get the Storage System Information

        :returns: Dictionary of Storage System Info

        """
        response, body = self.http.get('/system')
        return body

    def getWSAPIConfigurationInfo(self):
        """Get the WSAPI Configuration Information.

        :returns: Dictionary of WSAPI configurations

        """
        response, body = self.http.get('/wsapiconfiguration')
        return body

    def getOverallSystemCapacity(self):
        """Get the overall system capacity for the 3PAR server.

        :returns: Dictionary of system capacity information

        .. code-block:: python

            capacity = {
              "allCapacity": {                        # Overall system capacity
                                                      # includes FC, NL, SSD
                                                      # device types
                "totalMiB": 20054016,                 # Total system capacity
                                                      # in MiB
                "allocated": {                        # Allocated space info
                  "totalAllocatedMiB": 12535808,      # Total allocated
                                                      # capacity
                  "volumes": {                        # Volume capacity info
                    "totalVolumesMiB": 10919936,      # Total capacity
                                                      # allocated to volumes
                    "nonCPGsMiB": 0,                  # Total non-CPG capacity
                    "nonCPGUserMiB": 0,               # The capacity allocated
                                                      # to non-CPG user space
                    "nonCPGSnapshotMiB": 0,           # The capacity allocated
                                                      # to non-CPG snapshot
                                                      # volumes
                    "nonCPGAdminMiB": 0,              # The capacity allocated
                                                      # to non-CPG
                                                      # administrative volumes
                    "CPGsMiB": 10919936,              # Total capacity
                                                      # allocated to CPGs
                    "CPGUserMiB": 7205538,            # User CPG space
                    "CPGUserUsedMiB": 7092550,        # The CPG allocated to
                                                      # user space that is
                                                      # in use
                    "CPGUserUnusedMiB": 112988,       # The CPG allocated to
                                                      # user space that is not
                                                      # in use
                    "CPGSnapshotMiB": 2411870,        # Snapshot CPG space
                    "CPGSnapshotUsedMiB": 210256,     # CPG allocated to
                                                      # snapshot that is in use
                    "CPGSnapshotUnusedMiB": 2201614,  # CPG allocated to
                                                      # snapshot space that is
                                                      # not in use
                    "CPGAdminMiB": 1302528,           # Administrative volume
                                                      # CPG space
                    "CPGAdminUsedMiB": 115200,        # The CPG allocated to
                                                      # administrative space
                                                      # that is in use
                    "CPGAdminUnusedMiB": 1187328,     # The CPG allocated to
                                                      # administrative space
                                                      # that is not in use
                    "unmappedMiB": 0                  # Allocated volume space
                                                      # that is unmapped
                  },
                  "system": {                    # System capacity info
                     "totalSystemMiB": 1615872,  # System space capacity
                     "internalMiB": 780288,      # The system capacity
                                                 # allocated to internal
                                                 # resources
                     "spareMiB": 835584,         # Total spare capacity
                     "spareUsedMiB": 0,          # The system capacity
                                                 # allocated to spare resources
                                                 # in use
                     "spareUnusedMiB": 835584    # The system capacity
                                                 # allocated to spare resources
                                                 # that are unused
                    }
                },
                  "freeMiB": 7518208,             # Free capacity
                  "freeInitializedMiB": 7518208,  # Free initialized capacity
                  "freeUninitializedMiB": 0,      # Free uninitialized capacity
                  "unavailableCapacityMiB": 0,    # Unavailable capacity in MiB
                  "failedCapacityMiB": 0          # Failed capacity in MiB
              },
              "FCCapacity": {   # System capacity from FC devices only
                  ...           # Same structure as above
              },
              "NLCapacity": {   # System capacity from NL devices only
                  ...           # Same structure as above
              },
              "SSDCapacity": {  # System capacity from SSD devices only
                  ...           # Same structure as above
              }
            }

        """
        response, body = self.http.get('/capacity')
        return body

    # Volume methods
    def getVolumes(self):
        """Get the list of Volumes

        :returns: list of Volumes

        """
        response, body = self.http.get('/volumes')
        return body

    def getVolume(self, name):
        """Get information about a volume.

        :param name: The name of the volume to find
        :type name: str

        :returns: volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - volume doesn't exist

        """
        response, body = self.http.get('/volumes/%s' % name)
        return body

    def createVolume(self, name, cpgName, sizeMiB, optional=None):
        """Create a new volume.
        For the primera array there is support for only thin and DECO volume.
        To create DECO volume 'tdvv' and 'compression' both must be True.
        If only one of them is specified, it results in HTTPBadRequest.

        :param name: the name of the volume
        :type name: str
        :param cpgName: the name of the destination CPG
        :type cpgName: str
        :param sizeMiB: size in MiB for the volume
        :type sizeMiB: int
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
             'id': 12,                    # Volume ID. If not specified, next
                                          # available is chosen
             'comment': 'some comment',   # Additional information up to 511
                                          # characters
             'policies: {                 # Specifies VV policies
                'staleSS': False,         # True allows stale snapshots.
                'oneHost': True,          # True constrains volume export to
                                          # single host or host cluster
                'zeroDetect': True,       # True requests Storage System to
                                          # scan for zeros in incoming write
                                          # data
                'system': False,          # True special volume used by system
                                          # False is normal user volume
                'caching': True},         # Read-only. True indicates write &
                                          # read caching & read ahead enabled
             'snapCPG': 'CPG name',       # CPG Used for snapshots
             'ssSpcAllocWarningPct': 12,  # Snapshot space allocation warning
             'ssSpcAllocLimitPct': 22,    # Snapshot space allocation limit
             'tpvv': True,                # True: Create TPVV
                                          # False (default) Create FPVV
             'usrSpcAllocWarningPct': 22, # Enable user space allocation
                                          # warning
             'usrSpcAllocLimitPct': 22,   # User space allocation limit
             'expirationHours': 256,      # Relative time from now to expire
                                          # volume (max 43,800 hours)
             'retentionHours': 256        # Relative time from now to retain
                                          # volume (max 43,800 hours)
            }

        :returns: List of Volumes

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Invalid Parameter
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - TOO_LARGE - Volume size above limit
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not Enough space is available
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_SV - Volume Exists already

        """
        info = {'name': name, 'cpg': cpgName, 'sizeMiB': sizeMiB}
        # For primera array there is no compression and tdvv keys
        # removing tdvv, compression and
        # replacing compression+tdvv with reduce key for DECO
        if not optional and self.primera_supported:
            optional = {'tpvv': True}
        if optional:
            if self.primera_supported:
                for key in ['tpvv', 'compression', 'tdvv']:
                    option = optional.get(key)
                    if option and option not in [True, False]:
                        # raising exception for junk compression input
                        ex_desc = "39 - invalid input: wrong type for key "\
                            "[%s]. Valid values are [True, False]" % key
                        raise exceptions.HTTPBadRequest(ex_desc)

                if optional.get('compression') is True:
                    combination = ['tdvv', 'compression']
                    len_diff = len(set(combination) - set(optional.keys()))
                    msg = "invalid input: For compressed and deduplicated "\
                          "volumes both 'compression' and " \
                          "'tdvv' must be specified as true"
                    if len_diff == 1:
                        raise exceptions.HTTPBadRequest(msg)
                    if optional.get('tdvv') is True \
                            and optional.get('compression') is True:
                        optional['reduce'] = True

                    if optional.get('tdvv') is False \
                            and optional.get('compression') is True:
                        raise exceptions.HTTPBadRequest(msg)
                else:
                    msg = "invalid input: For compressed and deduplicated "\
                          "volumes both 'compression' and "\
                          "'tdvv' must be specified as true"
                    if optional.get('tdvv') is False \
                            and optional.get('compression') is False:
                        optional['reduce'] = False
                    if optional.get('tdvv') is True \
                            and optional.get('compression') is False:
                        raise exceptions.HTTPBadRequest(msg)

                if 'compression' in optional:
                    optional.pop('compression')
                if 'tdvv' in optional:
                    optional.pop('tdvv')
            info = self._mergeDict(info, optional)
        logger.debug("Parameters passed for create volume %s" % info)

        try:
            response, body = self.http.post('/volumes', body=info)
            return body
        except exceptions.HTTPBadRequest as ex:
            if self.primera_supported:
                ex_desc = 'invalid input: one of the parameters is required'
                ex_code = ex.get_code()
                # INV_INPUT_ONE_REQUIRED => 78
                if ex_code == 78 and \
                   ex.get_description() == ex_desc and \
                   ex.get_ref() == 'tpvv,reduce':
                    new_ex_desc = "invalid input: Either tpvv must be true "\
                                  "OR for compressed and deduplicated "\
                                  "volumes both 'compression' and 'tdvv' "\
                                  "must be specified as true"
                    raise exceptions.HTTPBadRequest(new_ex_desc)
            raise ex

    def deleteVolume(self, name):
        """Delete a volume.

        :param name: the name of the volume
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RETAINED - Volume retention time has not expired
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - HAS_RO_CHILD - Volume has read-only child
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - HAS_CHILD - The volume has a child volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - IN_USE - The volume is in use by VV set, VLUN, etc

        """
        response, body = self.http.delete('/volumes/%s' % name)
        return body

    def modifyVolume(self, name, volumeMods, appType=None):
        """Modify a volume.

        :param name: the name of the volume
        :type name: str
        :param volumeMods: dictionary of volume attributes to change
        :type volumeMods: dict
        .. code-block:: python

            volumeMods = {
             'newName': 'newName',         # New volume name
             'comment': 'some comment',    # New volume comment
             'snapCPG': 'CPG name',        # Snapshot CPG name
             'policies: {                  # Specifies VV policies
                'staleSS': False,          # True allows stale snapshots.
                'oneHost': True,           # True constrains volume export to
                                           # single host or host cluster
                'zeroDetect': True,        # True requests Storage System to
                                           # scan for zeros in incoming write
                                           # data
                'system': False,           # True special volume used by system
                                           # False is normal user volume
                'caching': True},          # Read-only. True indicates write &
                                           # read caching & read ahead enabled
             'ssSpcAllocWarningPct': 12,   # Snapshot space allocation warning
             'ssSpcAllocLimitPct': 22,     # Snapshot space allocation limit
             'tpvv': True,                 # True: Create TPVV
                                           # False: (default) Create FPVV
             'usrSpcAllocWarningPct': 22,  # Enable user space allocation
                                           # warning
             'usrSpcAllocLimitPct': 22,    # User space allocation limit
             'userCPG': 'User CPG name',   # User CPG name
             'expirationHours': 256,       # Relative time from now to expire
                                           # volume (max 43,800 hours)
             'retentionHours': 256,        # Relative time from now to retain
                                           # volume (max 43,800 hours)
             'rmSsSpcAllocWarning': False, # True removes snapshot space
                                           # allocation warning.
                                           # False sets it when value > 0
             'rmUsrSpcAllocWarwaning': False, # True removes user space
                                           #  allocation warning.
                                           # False sets it when value > 0
             'rmExpTime': False,           # True resets expiration time to 0.
                                           # False sets it when value > 0
             'rmSsSpcAllocLimit': False,   # True removes snapshot space
                                           # allocation limit.
                                           # False sets it when value > 0
             'rmUsrSpcAllocLimit': False   # True removes user space
                                           # allocation limit.
                                           # False sets it when value > 0
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WARN_GT_LIMIT - Allocation warning level is higher than
            the limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_USR_ALRT_NON_TPVV - User space allocation alerts are
            valid only with a TPVV.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_RETAIN_GT_EXPIRE - Retention time is greater than
            expiration time.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_VV_POLICY - Invalid policy specification (for example,
            caching or system is set to true).
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: string length exceeds
            limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TIME - Invalid time specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_MODIFY_USR_CPG_TPVV - usr_cpg cannot be modified
            on a TPVV.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - UNLICENSED_FEATURE - Retention time cannot be modified on a
            system without the Virtual Lock license.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN_SAME_DOMAIN - Snap CPG is not in the same domain as
            the user CPG.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - Cannot modify a peer volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPInternalServerError`
            - INT_SERV_ERR - Metadata of the VV is corrupted.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - Cannot modify retention time on a
            system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Cannot modify an internal
            volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_NOT_DEFINED_ALL_NODES - Cannot modify a
            volume until the volume is defined on all volumes.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_ONLINE_COPY_IN_PROGRESS - Cannot modify a
            volume when an online copy for that volume is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Cannot modify a
            volume in the middle of a conversion operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_SNAPSPACE_NOT_MOVED_TO_CPG - Snapshot space
            of a volume needs to be moved to a CPG before the user space.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_ACCOUNTING_IN_PROGRESS - The volume
            cannot be renamed until snapshot accounting has finished.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_ZERO_DETECT_TPVV - The zero_detect policy can be
            used only on TPVVs.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_CPG_ON_SNAPSHOT - CPG cannot be assigned to a
            snapshot.

        """
        response = self.http.put('/volumes/%s' % name, body=volumeMods)

        if appType is not None:
            if 'newName' in volumeMods and volumeMods['newName']:
                name = volumeMods['newName']

            try:
                self.setVolumeMetaData(name, 'hpe_ecosystem_product', appType)
            except Exception:
                pass

        return response

    def growVolume(self, name, amount):
        """Grow an existing volume by 'amount' Mebibytes.

        :param name: the name of the volume
        :type name: str
        :param amount: the additional size in MiB to add, rounded up to the
                       next chunklet size (e.g. 256 or 1000 MiB)
        :type amount: int

        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_UNSUPPORTED_VV_TYPE - Invalid operation: Cannot
            grow this type of volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_TUNE_IN_PROGRESS - Invalid operation: Volume
            tuning is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: String length exceeds
            limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_VV_GROW_SIZE - Invalid grow size.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NEW_SIZE_EXCEEDS_CPG_LIMIT - New volume size exceeds CPG limit
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - This operation is not allowed
            on an internal volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV
            conversion is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_COPY_IN_PROGRESS - Invalid operation:
            online copy is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is
            in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_SIZE_CANNOT_REDUCE - New volume size is smaller than the
            current size.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NEW_SIZE_EXCEEDS_LIMITS - New volume size exceeds the limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_SA_SD_SPACE_REMOVED - Invalid operation: Volume
            SA/SD space is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_IS_BUSY - Invalid operation: Volume is currently
            busy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_IS_PCOPY - Invalid operation: Volume is a
            physical copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Invalid operation: Volume
            promotion is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PARENT_OF_PCOPY - Invalid operation: Volume is
            the parent of physical copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Insufficent space for requested operation.

        """
        info = {'action': self.GROW_VOLUME,
                'sizeMiB': int(amount)}

        response, body = self.http.put('/volumes/%s' % name, body=info)
        return body

    def promoteVirtualCopy(self, snapshot, optional=None):
        """Revert a volume to snapshot.

        :param snapshot: the snapshot name
        :type snapshot: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'online': False,                # should execute promote
                                                # operation on online volume?
                'allowRemoteCopyParent': 'False',
                                                # allow promote operation if
                                                # volume is in remote copy
                                                # volume group?
                'priority': 1                   # taskPriorityEnum (does not
                                                # apply to online copy)
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_CANNOT_STOP_ONLINE_PROMOTE - The online
            promote cannot be stopped.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_BASE_VOLUME - The volume is a base volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PCOPY_IN_PROGRESS - The destination volume has
            a physical copy in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_PARENT_PCOPY_IN_PROGRESS - The parent is involved
            in a physical copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_TUNE_IN_PROGRESS - Volume tuning is in
            progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_IN_REMOTE_COPY - The volume is involved in
            Remote Copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_PARENT_VV_EXPORTED - Parent volume is exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_EXPORTED - Parent volume is exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_PROMOTE_TARGET_NOT_BASE_VV - The promote target is
            not a base volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_PARENT_SIZE_HAS_INCREASED - The parent volume size
            has increased.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_PARAM_CONFLICT - Parameters cannot be present at
            the same time.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_IS_BUSY - Volume is currently busy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Volume promotion is in
            progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PROMOTE_IS_NOT_IN_PROGRESS - Volume promotion
            is not in progress.

        """
        info = {'action': self.PROMOTE_VIRTUAL_COPY}
        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.put('/volumes/%s' % snapshot, body=info)
        return body

    def copyVolume(self, src_name, dest_name, dest_cpg, optional=None):
        """Copy/Clone a volume.

        :param src_name: the source volume name
        :type src_name: str
        :param dest_name: the destination volume name
        :type dest_name: str
        :param dest_cpg: the destination CPG
        :type dest_cpg: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'online': False,                # should physical copy be
                                                # performed online?
                'tpvv': False,                  # use thin provisioned space
                                                # for destination
                                                # (online copy only)
                'snapCPG': 'OpenStack_SnapCPG', # snapshot CPG for the
                                                # destination
                                                # (online copy only)
                'saveSnapshot': False,          # save the snapshot of the
                                                # source volume
                'priority': 1                   # taskPriorityEnum (does not
                                                # apply to online copy)
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid
            range(1-3).
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a
            base volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved
            in a remote copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the
            same as the parent.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a
            read-only snapshot.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the
            base volume of a parent volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a
            conversion operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must
            allow snapshots.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume
            for the volume is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of
            the destination volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a
            peer volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the
            normal state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has
            a physical copy in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the
            destination volume has failed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent
            volume is larger than the size of the destination volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VVCOPY - Physical copy not found.

        """
        # Virtual volume sets are not supported with the -online option
        parameters = {'destVolume': dest_name,
                      'destCPG': dest_cpg}
        # For online copy, there has to be tpvv/tdvv(Non primera array)
        # and tpvv/compression(primera array) has to be passed from caller side
        # For offline copy, parameters tpvv/tdvv/compression are invalid,
        # has to be taken care by caller side
        if optional:
            if self.primera_supported:
                for key in ['tpvv', 'compression', 'tdvv']:
                    option = optional.get(key)
                    if option and option not in [True, False]:
                        # raising exception for junk compression input
                        ex_desc = "39 - invalid input: wrong type for key " \
                            "[%s]. Valid values are [True, False]" % key
                        raise exceptions.HTTPBadRequest(ex_desc)
                if optional.get('compression') is True:
                    combination = ['tdvv', 'compression']
                    len_diff = len(set(combination) - set(optional.keys()))
                    msg = "invalid input: For compressed and deduplicated "\
                          "volumes both 'compression' and " \
                          "'tdvv' must be specified as true"
                    if len_diff == 1:
                        raise exceptions.HTTPBadRequest(msg)
                    if optional.get('tdvv') is True \
                            and optional.get('compression') is True:
                        optional['reduce'] = True

                    if optional.get('tdvv') is False \
                            and optional.get('compression') is True:
                        raise exceptions.HTTPBadRequest(msg)
                else:
                    msg = "invalid input: For compressed and deduplicated "\
                          "volumes both 'compression' and "\
                          "'tdvv' must be specified as true"
                    if optional.get('tdvv') is False \
                            and optional.get('compression') is False:
                        optional['reduce'] = False
                    if optional.get('tdvv') is True \
                            and optional.get('compression') is False:
                        raise exceptions.HTTPBadRequest(msg)

                if 'compression' in optional:
                    optional.pop('compression')
                if 'tdvv' in optional:
                    optional.pop('tdvv')
            parameters = self._mergeDict(parameters, optional)
        if 'online' not in parameters or not parameters['online']:
            # 3Par won't allow destCPG to be set if it's not an online copy.
            parameters.pop('destCPG', None)

        info = {'action': 'createPhysicalCopy',
                'parameters': parameters}
        logger.debug("Parameters passed for copy volume %s" % info)
        try:
            response, body = self.http.post('/volumes/%s' % src_name,
                                            body=info)
            return body
        except exceptions.HTTPBadRequest as ex:
            if self.primera_supported:
                ex_desc = 'invalid input: one of the parameters is required'
                ex_code = ex.get_code()
                # INV_INPUT_ONE_REQUIRED => 78
                if ex_code == 78 and \
                   ex.get_description() == ex_desc and \
                   ex.get_ref() == 'tpvv,reduce':
                    new_ex_desc = "invalid input: Either tpvv must be true "\
                                  "OR for compressed and deduplicated "\
                                  "volumes both 'compression' and 'tdvv' "\
                                  "must be specified as true."
                    raise exceptions.HTTPBadRequest(new_ex_desc)
            raise ex

    def isOnlinePhysicalCopy(self, name):
        """Is the volume being created by process of online copy?

        :param name: the name of the volume
        :type name: str

        """
        task = self._findTask(name, active=True)
        if task is None:
            return False
        else:
            return True

    def stopOnlinePhysicalCopy(self, name):
        """Stopping a online physical copy operation.

        :param name: the name of the volume
        :type name: str

        """
        # first we have to find the active copy
        task = self._findTask(name)
        task_id = None
        if task is None:
            # couldn't find the task
            self.deleteVolume(name)
            msg = "Couldn't find the copy task for '%s'" % name
            raise exceptions.HTTPNotFound(error={'desc': msg})
        else:
            task_id = task[0]

        # now stop the copy
        if task_id is not None:
            self._cancelTask(task_id)
        else:
            self.deleteVolume(name)
            msg = "Couldn't find the copy task for '%s'" % name
            raise exceptions.HTTPNotFound(error={'desc': msg})

        # we have to make sure the task is cancelled
        # before moving on. This can sometimes take a while.
        ready = False
        while not ready:
            time.sleep(1)
            task = self._findTask(name, True)
            if task is None:
                ready = True

        # now cleanup the dead snapshots
        vol = self.getVolume(name)
        if vol:
            if 'copyOf' in vol:
                snap1 = self.getVolume(vol['copyOf'])
                snap2 = self.getVolume(snap1['copyOf'])
            self.deleteVolume(name)
            if 'copyOf' in vol:
                self.deleteVolume(snap1['name'])
                self.deleteVolume(snap2['name'])

    def getAllTasks(self):
        """Get the list of all Tasks

        :returns: list of all Tasks

        """
        response, body = self.http.get('/tasks')
        return body

    def getTask(self, taskId):
        """Get the status of a task.

        :param taskId: the task id
        :type taskId: int

        :returns: the status of the task

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BELOW_RANGE - Bad Request Task ID must be a positive
            value.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - Bad Request Task ID is too large.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_TASK - Task with the specified task ID does not
            exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - Task ID is not an integer.

        """
        response, body = self.http.get('/tasks/%s' % taskId)
        return body

    def _findTask(self, name, active=True):
        uri = '/tasks'
        response, body = self.http.get(uri)

        task_type = {1: 'vv_copy', 2: 'phys_copy_resync', 3: 'move_regions',
                     4: 'promote_sv', 5: 'remote_copy_sync',
                     6: 'remote_copy_reverse', 7: 'remote_copy_failover',
                     8: 'remote_copy_recover', 18: 'online_vv_copy'}

        status = {1: 'done', 2: 'active', 3: 'cancelled', 4: 'failed'}

        priority = {1: 'high', 2: 'med', 3: 'low'}

        for task_obj in body['members']:
            if(task_obj['name'] == name):
                if(active and task_obj['status'] != 2):
                    # if active flag is True, but status of task is not True
                    # then it means task got completed/cancelled/failed
                    return None

                task_details = []
                task_details.append(task_obj['id'])

                value = task_obj['type']
                if value in task_type:
                    type_str = task_type[value]
                else:
                    type_str = 'n/a'
                task_details.append(type_str)

                task_details.append(task_obj['name'])

                value = task_obj['status']
                task_details.append(status[value])

                # Phase and Step feilds are not found
                task_details.append('---')
                task_details.append('---')
                task_details.append(task_obj['startTime'])
                task_details.append(task_obj['finishTime'])

                if('priority' in task_obj):
                    value = task_obj['priority']
                    task_details.append(priority[value])
                else:
                    task_details.append('n/a')

                task_details.append(task_obj['user'])

                return task_details

        return None

    def _convert_cli_output_to_collection_like_wsapi(self, cli_output):
        return HPE3ParClient.convert_cli_output_to_wsapi_format(cli_output)

    def getPatches(self, history=True):
        """Get all the patches currently affecting the system.

        :param history: Specify the history of all patches and updates applied
                        to the system.
        :returns: dict with total and members
                  (see convert_cli_output_to_collection_like_wsapi())

        """
        cmd = ['showpatch']
        if history:
            cmd.append('-hist')
        return self._convert_cli_output_to_collection_like_wsapi(
            self._run(cmd))

    def getPatch(self, patch_id):
        """Get details on a specified patch ID if it has been applied to the
           system.

        :param patch_id:  The ID of the patch.
        :returns: list of str (raw lines of CLI output as strings)

        """
        return self._run(['showpatch', '-d', patch_id])

    def stopOfflinePhysicalCopy(self, name):
        """Stopping a offline physical copy operation.

        :param name: the name of the volume
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid
            range(1-3).
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a
            base volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved
            in a remote copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the
            same as the parent.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a
            read-only snapshot.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the
            base volume of a parent volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a
            conversion operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must
            allow snapshots.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume
            for the volume is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of
            the destination volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a
            peer volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the
            normal state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has
            a physical copy in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the
            destination volume has failed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent
            volume is larger than the size of the destination volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VVCOPY - Physical copy not found.

        """
        info = {'action': self.STOP_PHYSICAL_COPY}

        response, body = self.http.put('/volumes/%s' % name, body=info)
        return body

    def createSnapshot(self, name, copyOfName, optional=None):
        """Create a snapshot of an existing Volume.

        :param name: Name of the Snapshot
        :type name: str
        :param copyOfName: The volume you want to snapshot
        :type copyOfName: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'id': 12,                   # Specifies the ID of the volume,
                                            # next by default
                'comment': "some comment",
                'readOnly': True,           # Read Only
                'expirationHours': 36,      # time from now to expire
                'retentionHours': 12        # time from now to expire
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied

        """
        parameters = {'name': name}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action': 'createSnapshot',
                'parameters': parameters}

        response, body = self.http.post('/volumes/%s' % copyOfName, body=info)
        return body

    # Host Set methods
    def findHostSet(self, name):
        """
        Find the Host Set name for a host.

        :param name: the host name
        :type name: str
        """

        host_set_name = None

        # If ssh isn't available search all host sets for this host
        if self.ssh is None:
            host_sets = self.getHostSets()
            if host_sets is not None and 'members' in host_sets:
                for host_set in host_sets['members']:
                    if 'setmembers' in host_set:
                        for host_name in host_set['setmembers']:
                            if host_name == name:
                                return host_set['name']

        # Using ssh we can ask for the host set for this host
        else:
            cmd = ['showhostset', '-host', name]
            out = self._run(cmd)
            host_set_name = None
            if out and len(out) > 1:
                info = out[1].split(",")
                host_set_name = info[1]

        return host_set_name

    def getHostSets(self):
        """
        Get information about every Host Set on the 3Par array

        :returns: list of Host Sets
        """
        response, body = self.http.get('/hostsets')
        return body

    def getHostSet(self, name):
        """
        Get information about a Host Set

        :param name: The name of the Host Set to find
        :type name: str

        :returns: host set dict
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exist
        """
        response, body = self.http.get('/hostsets/%s' % name)
        return body

    def createHostSet(self, name, domain=None, comment=None, setmembers=None):
        """
        This creates a new host set

        :param name: the host set to create
        :type set_name: str
        :param domain: the domain where the set lives
        :type domain: str
        :param comment: a comment for the host set
        :type comment: str
        :param setmembers: the hosts to add to the host set, the existence
        of the host will not be checked
        :type setmembers: list of str
        :returns: id of host set created
        :rtype: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain
            to perform this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        """
        info = {'name': name}

        if domain:
            info['domain'] = domain

        if comment:
            info['comment'] = comment

        if setmembers:
            members = {'setmembers': setmembers}
            info = self._mergeDict(info, members)

        response, body = self.http.post('/hostsets', body=info)
        if response is not None and 'location' in response:
            host_set_id = response['location'].rsplit(
                '/api/v1/hostsets/', 1)[-1]
            return host_set_id
        else:
            return None

    def deleteHostSet(self, name):
        """
        This removes a host set.

        :param name: the host set to remove
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXPORTED_VLUN - The host set has exported VLUNs.
        """
        self.http.delete('/hostsets/%s' % name)

    def modifyHostSet(self, name, action=None, newName=None, comment=None,
                      setmembers=None):
        """
        This modifies a host set by adding or removing a hosts from the set.
        It's action is based on the enums SET_MEM_ADD or SET_MEM_REMOVE.

        :param name: the host set name
        :type name: str
        :param action: add or remove host(s) from the set
        :type action: enum
        :param newName: new name of set
        :type newName: str
        :param comment: new comment for the set
        :type comment: str
        :param setmembers: the host(s) to add to the set, the existence of the
                           host(s) will not be checked
        :type setmembers: list str

        :returns: headers - dict of HTTP Response headers.  Upon successful
                  modification of a host set HTTP code 200 OK is returned and
                  the URI of the updated host set will be returned in the
                  location portion of the headers.
        :returns: body - the body of the response.  None if successful.

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - MEMBER_NOT_IN_SET - The object is not part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain
            to perform this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Invalid input (parameters cannot be
            present at the same time).
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid contains one or more illegal
            characters.
        """
        info = {}

        if action:
            info['action'] = action

        if newName:
            info['newName'] = newName

        if comment:
            info['comment'] = comment

        if setmembers:
            members = {'setmembers': setmembers}
            info = self._mergeDict(info, members)

        response = self.http.put('/hostsets/%s' % name, body=info)
        return response

    def addHostToHostSet(self, set_name, name):
        """
        This adds a host to a host set.

        :param set_name: the host set name
        :type set_name: str
        :param name: the host name to add
        :type name: str

        :returns: headers - dict of HTTP Response headers.  Upon successful
                  modification of a host set HTTP code 200 OK is returned and
                  the URI of the updated host set will be returned in the
                  location portion of the headers.
        :returns: body - the body of the response.  None if successful.
        """
        return self.modifyHostSet(set_name, action=self.SET_MEM_ADD,
                                  setmembers=[name])

    def removeHostFromHostSet(self, set_name, name):
        """
        Remove a host from a host set.

        :param set_name: the host set name
        :type set_name: str
        :param name: the host name to remove
        :type name: str

        :returns: headers - dict of HTTP Response headers.  Upon successful
                  modification of a host set HTTP code 200 OK is returned and
                  the URI of the updated host set will be returned in the
                  location portion of the headers.
        :returns: body - the body of the response.  None if successful.
        """
        return self.modifyHostSet(set_name, action=self.SET_MEM_REMOVE,
                                  setmembers=[name])

    def removeHostFromItsHostSet(self, name):
        """
        Remove a host from its host set if it is a member of one.

        :param name: the host name to remove
        :type name: str

        :returns: None if host has no host set, else (headers, body)
        :returns: headers - dict of HTTP Response headers.  Upon successful
                  modification of a host set HTTP code 200 OK is returned and
                  the URI of the updated host set will be returned in the
                  location portion of the headers.
        :returns: body - the body of the response.  None if successful.
        """

        host_set_name = self.findHostSet(name)
        if host_set_name is None:
            return None

        return self.removeHostFromHostSet(host_set_name, name)

    def getHosts(self):
        """Get information about every Host on the 3Par array.

        :returns: list of Hosts
        """
        response, body = self.http.get('/hosts')
        return body

    def getHost(self, name):
        """Get information about a Host.

        :param name: The name of the Host to find
        :type name: str

        :returns: host dict
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST doesn't exist

        """
        response, body = self.http.get('/hosts/%s' % name)
        return body

    def createHost(self, name, iscsiNames=None, FCWwns=None, optional=None):
        """Create a new Host entry.

        :param name: The name of the host
        :type name: str
        :param iscsiNames: Array if iscsi iqns
        :type name: array
        :param FCWwns: Array if Fibre Channel World Wide Names
        :type name: array
        :param optional: The optional stuff
        :type optional: dict

        .. code-block:: python

            optional = {
                'persona': 1,                   # ID of the persona to assign
                                                # to the host.
                                                # 3.1.3 default: Generic-ALUA
                                                # 3.1.2 default: General
                'domain': 'myDomain',           # Create the host in the
                                                # specified domain, or default
                                                # domain if unspecified.
                'forceTearDown': False,         # If True, force to tear down
                                                # low-priority VLUN exports.
                'descriptors':
                    {'location': 'earth',       # The host's location
                     'IPAddr': '10.10.10.10',   # The host's IP address
                     'os': 'linux',             # The operating system running
                                                # on the host.
                     'model': 'ex',             # The host's model
                     'contact': 'Smith',        # The host's owner and contact
                     'comment': "Joe's box"}    # Additional host information
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Name not specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - FCWWNs and iSCSINames are both
            specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Host name, domain name, or iSCSI name
            is too long.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EMPTY_STR - Input string (for domain name, iSCSI name,
            etc.) is empty.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Any error from host-name or domain-name
            parsing.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI
            names are specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - The length of WWN is not 16. WWN
            specification contains non-hexadecimal digit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_PATH - host WWN/iSCSI name already used by another host
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_HOST - host name is already used.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - No space to create host.

        """
        info = {'name': name}

        if iscsiNames:
            iscsi = {'iSCSINames': iscsiNames}
            info = self._mergeDict(info, iscsi)

        if FCWwns:
            fc = {'FCWWNs': FCWwns}
            info = self._mergeDict(info, fc)

        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/hosts', body=info)
        return body

    def modifyHost(self, name, mod_request):
        """Modify an existing Host entry.

        :param name: The name of the host
        :type name: str
        :param mod_request: Objects for Host Modification Request
        :type mod_request: dict

        .. code-block:: python

            mod_request = {
                'newName': 'myNewName',         # New name of the host
                'pathOperation': 1,             # If adding, adds the WWN or
                                                # iSCSI name to the existing
                                                # host.
                'FCWWNs': [],                   # One or more WWN to set for
                                                # the host.
                'iSCSINames': [],               # One or more iSCSI names to
                                                # set for the host.
                'forcePathRemoval': False,      # If True, remove SSN(s) or
                                                # iSCSI(s) even if there are
                                                # VLUNs exported to host
                'persona': 1,                   # ID of the persona to modify
                                                # the host's persona to.
                'descriptors':
                    {'location': 'earth',       # The host's location
                     'IPAddr': '10.10.10.10',   # The host's IP address
                     'os': 'linux',             # The operating system running
                                                # on the host.
                     'model': 'ex',             # The host's model
                     'contact': 'Smith',        # The host's owner and contact
                     'comment': 'Joes box'}     # Additional host information
                'chapOperation': HOST_EDIT_ADD, # Add or remove
                'chapOperationMode': CHAP_INITIATOR, # Initator or target
                'chapName': 'MyChapName',       # The chap name
                'chapSecret': 'xyz',            # The chap secret for the host
                                                # or the target
                'chapSecretHex': False,         # If True, the chapSecret is
                                                # treated as Hex.
                'chapRemoveTargetOnly': True    # If True, then remove target
                                                # chap only
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Missing host name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Both iSCSINames & FCWWNs are
            specified. (lot of other possibilities)
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ONE_REQUIRED - iSCSINames or FCWwns missing.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ONE_REQUIRED - No path operation specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - Invalid enum value.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Required fields missing.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Host descriptor argument length, new
            host name, or iSCSI name is too long.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Error parsing host or iSCSI name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_HOST - New host name is already used.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - Host to be modified does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI
            names are specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - Input value is of the wrong type.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_PATH - WWN or iSCSI name is already claimed by other
            host.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_LENGTH - CHAP hex secret length is not 16 bytes, or
            chap ASCII secret length is not 12 to 16 characters.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NO_INITIATOR_CHAP - Setting target CHAP without initiator CHAP.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CHAP - Remove non-existing CHAP.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - NON_UNIQUE_CHAP_SECRET - CHAP secret is not unique.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXPORTED_VLUN - Setting persona with active export; remove a host
            path on an active export.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NON_EXISTENT_PATH - Remove a non-existing path.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - LUN_HOSTPERSONA_CONFLICT - LUN number and persona capability
            conflict.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_PATH - Duplicate path specified.

        """
        response = self.http.put('/hosts/%s' % name, body=mod_request)
        return response

    def deleteHost(self, name):
        """Delete a Host.

        :param name: Host Name
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            -  IN_USE - The HOST Cannot be removed because it's in use.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied

        """
        response, body = self.http.delete('/hosts/%s' % name)

    def findHost(self, iqn=None, wwn=None):
        """Find a host from an iSCSI initiator or FC WWN.

        :param iqn: lookup based on iSCSI initiator
        :type iqn: str
        :param wwn: lookup based on WWN
        :type wwn: str

        """

        # for now there is no search in the REST API
        # so we can do a create looking for a specific
        # error.  If we don't get that error, we nuke the
        # fake host.

        def _hostname():
            # create a safe, random hostname that won't
            # create a collision when findHost is called
            # in parallel, before the temp host is removed.
            uuid_str = str(uuid.uuid4()).replace("-", "")[:20]
            return uuid_str

        cmd = ['createhost']
        # create a random hostname
        hostname = _hostname()
        if iqn:
            cmd.append('-iscsi')

        cmd.append(hostname)

        if iqn:
            cmd.append(iqn)
        else:
            cmd.append(wwn)

        result = self._run(cmd)
        test = ' '.join(result)
        search_str = "already used by host "
        if search_str in test:
            # host exists, return name used by 3par
            hostname_3par = self._get_next_word(test, search_str)
            return hostname_3par
        else:
            # host creation worked...so we need to remove it.
            # this means we didn't find an existing host that
            # is using the iqn or wwn.
            self.deleteHost(hostname)
            return None

    def queryHost(self, iqns=None, wwns=None):
        """Find a host from an iSCSI initiator or FC WWN.

        :param iqns: lookup based on iSCSI initiator list
        :type iqns: list
        :param wwns: lookup based on WWN list
        :type wwns: list

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Invalid URI syntax.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hpe3parclient.exceptions.HTTPInternalServerError`
            - INTERNAL_SERVER_ERR - Internal server error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Host name contains invalid character.

        """
        wwnsQuery = ''
        if wwns:
            tmpQuery = []
            for wwn in wwns:
                tmpQuery.append('wwn==%s' % wwn)
            wwnsQuery = ('FCPaths[%s]' % ' OR '.join(tmpQuery))

        iqnsQuery = ''
        if iqns:
            tmpQuery = []
            for iqn in iqns:
                tmpQuery.append('name==%s' % iqn)
            iqnsQuery = ('iSCSIPaths[%s]' % ' OR '.join(tmpQuery))

        query = ''
        if wwnsQuery and iqnsQuery:
            query = ('%(wwns)s OR %(iqns)s' % ({'wwns': wwnsQuery,
                                                'iqns': iqnsQuery}))
        elif wwnsQuery:
            query = wwnsQuery
        elif iqnsQuery:
            query = iqnsQuery

        query = '"%s"' % query

        response, body = self.http.get('/hosts?query=%s' %
                                       quote(query.encode("utf8")))
        return body

    def getHostVLUNs(self, hostName):
        """Get all of the VLUNs on a specific Host.

        :param hostName: Host name
        :type hostNane: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST Not Found

        """
        # calling getHost to see if the host exists and raise not found
        # exception if it's not found.
        self.getHost(hostName)

        vluns = []
        # Check if the WSAPI supports VLUN querying. If it is supported
        # request only the VLUNs that are associated with the host.
        if self.vlun_query_supported:
            query = '"hostname EQ %s"' % hostName
            response, body = self.http.get('/vluns?query=%s' %
                                           quote(query.encode("utf8")))

            for vlun in body.get('members', []):
                vluns.append(vlun)
        else:
            allVLUNs = self.getVLUNs()

            if allVLUNs:
                for vlun in allVLUNs['members']:
                    if 'hostname' in vlun and vlun['hostname'] == hostName:
                        vluns.append(vlun)

        if len(vluns) < 1:
            raise exceptions.HTTPNotFound(
                {'code': 'NON_EXISTENT_VLUNS',
                 'desc': "No VLUNs for host '%s' found" % hostName})
        return vluns

    # PORT Methods
    def _getIscsiVlan(self, nsp):
        """Get iSCSI VLANs for an iSCSI port

        :param nsp: node slot port Eg. '0:2:1'
        :type nsp: str

        :returns: list of iSCSI VLANs

        """
        response, body = self.http.get('/ports/' + nsp + '/iSCSIVlans/')

        return body

    def getPorts(self):
        """Get the list of ports on the 3PAR.

        :returns: list of Ports

        """
        response, body = self.http.get('/ports')

        # if any of the ports are iSCSI ports and
        # are vlan tagged (as obtained by _getIscsiVlan), then
        # the vlan information is merged with the
        # returned port information.
        for port in body['members']:
            if (port['protocol'] == self.PORT_PROTO_ISCSI and
                    'iSCSIPortInfo' in port and
                    port['iSCSIPortInfo']['vlan'] == 1):

                portPos = port['portPos']
                nsp_array = [str(portPos['node']), str(portPos['slot']),
                             str(portPos['cardPort'])]
                nsp = ":".join(nsp_array)
                vlan_body = self._getIscsiVlan(nsp)
                if vlan_body:
                    port['iSCSIVlans'] = vlan_body['iSCSIVlans']

        return body

    def _getProtocolPorts(self, protocol, state=None):
        return_ports = []
        ports = self.getPorts()
        if ports:
            for port in ports['members']:
                if port['protocol'] == protocol:
                    if state is None:
                        return_ports.append(port)
                    elif port['linkState'] == state:
                        return_ports.append(port)

        return return_ports

    def _cloneISCSIPorts(self, real_ports, vlan_ports):
        cloned_ports = []
        for port in vlan_ports:
            matching_ports = [
                x for x in real_ports['members']
                if (x['protocol'] == self.PORT_PROTO_ISCSI and
                    x['iSCSIPortInfo']['vlan'] == 1 and
                    x['portPos'] == port['portPos'])
            ]

            # should only be one
            if len(matching_ports) > 1:
                err = ("Found {} matching ports for vlan tagged iSCSI port "
                       "{}.  There should only be one.")
                raise exceptions.\
                    NoUniqueMatch(err.format(len(matching_ports), port))

            if len(matching_ports) == 1:
                new_port = copy.deepcopy(matching_ports[0])
                new_port.update(port)
                cloned_ports.append(new_port)

        return cloned_ports

    def getFCPorts(self, state=None):
        """Get a list of Fibre Channel Ports.

        :returns: list of Fibre Channel Ports

        """
        return self._getProtocolPorts(1, state)

    def getiSCSIPorts(self, state=None):
        """Get a list of iSCSI Ports.

        :returns: list of iSCSI Ports

        """
        return self._getProtocolPorts(2, state)

    def getIPPorts(self, state=None):
        """Get a list of IP Ports.

        :returns: list of IP Ports

        """
        return self._getProtocolPorts(4, state)

    # CPG methods
    def getCPGs(self):
        """Get entire list of CPGs.

        :returns: list of cpgs

        """
        try:
            response, body = self.http.get('/cpgs')
            return body
        except Exception as e:
            raise e

    def getCPG(self, name):
        """Get information about a CPG.

        :param name: The name of the CPG to find
        :type name: str

        :returns: cpg dict
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            -  NON_EXISTENT_CPG - CPG doesn't exist

        """
        try:
            response, body = self.http.get('/cpgs/%s' % name)
        except exceptions.HTTPNotFound:
            err = (_("CPG (%s) doesn't exist on array") % cpg_name)
            LOG.error(err)
            raise exception.InvalidInput(reason=err)
        return body

    def get_domain(self, cpg_name):
        try:
            cpg = self.getCPG(cpg_name)
        except exceptions.HTTPNotFound:
            err = (_("Failed to get domain because CPG (%s) doesn't "
                     "exist on array.") % cpg_name)
            LOG.error(err)
            raise exception.InvalidInput(reason=err)

        if 'domain' in cpg:
            return cpg['domain']
        return None

    def getCPGAvailableSpace(self, name):
        """Get available space information about a CPG.

        :param name: The name of the CPG to find
        :type name: str

        :returns: Available space dict

        .. code-block:: python

            info = {
                "rawFreeMiB": 1000000,    # Raw free capacity in MiB
                "usableFreeMiB": 5000     # LD free capacity in MiB
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - CPG Not Found

        """
        info = {'cpg': name}

        response, body = self.http.post('/spacereporter', body=info)
        return body

    def createCPG(self, name, optional=None):
        """Create a CPG.

        :param name: CPG Name
        :type name: str
        :param optional: Optional parameters
        :type optional: dict

        .. code-block:: python

            optional = {
                'growthIncrementMiB': 100,    # Growth increment in MiB for
                                              # each auto-grown operation
                'growthLimitMiB': 1024,       # Auto-grow operation is limited
                                              # to specified storage amount
                'usedLDWarningAlertMiB': 200, # Threshold to trigger warning
                                              # of used logical disk space
                'domain': 'MyDomain',         # Name of the domain object
                'LDLayout': {
                    'RAIDType': 1,            # Disk Raid Type
                    'setSize': 100,           # Size in number of chunklets
                    'HA': 0,                  # Layout supports failure of
                                              # one port pair (1),
                                              # one cage (2),
                                              # or one magazine (3)
                    'chunkletPosPref': 2,     # Chunklet location perference
                                              # characteristics.
                                              # Lowest Number/Fastest transfer
                                              # = 1
                                              # Higher Number/Slower transfer
                                              # = 2
                    'diskPatterns': []}       # Patterns for candidate disks
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT Invalid URI Syntax.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NON_EXISTENT_DOMAIN - Domain doesn't exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not Enough space is available.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - BAD_CPG_PATTERN  A Pattern in a CPG specifies illegal values.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_CPG - CPG Exists already

        """
        info = {'name': name}
        if optional:
            if self.primera_supported:
                for key, value in dict(optional).items():
                    if key == 'LDLayout':
                        ldlayout = value
                        for keys, val in dict(ldlayout).items():
                            if keys == 'setSize' or \
                                    (keys == 'RAIDType' and
                                     ldlayout.get('RAIDType') == 1):
                                ldlayout.pop(keys)
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/cpgs', body=info)
        return body

    def deleteCPG(self, name):
        """Delete a CPG.

        :param name: CPG Name
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - CPG Not Found
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            -  IN_USE - The CPG Cannot be removed because it's in use.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied

        """
        response, body = self.http.delete('/cpgs/%s' % name)

    # VLUN methods
    #
    # Virtual-LUN, or VLUN, is a pairing between a virtual volume and a
    # logical unit number (LUN), expressed as either a VLUN template or
    # an active VLUN.
    # A VLUN template sets up an association between a virtual volume and a
    # LUN-host, LUN-port, or LUN-host-port combination by establishing the
    # export rule or the manner in which the Volume is exported.

    def getVLUNs(self):
        """Get VLUNs.

        :returns: Array of VLUNs

        """
        response, body = self.http.get('/vluns')
        return body

    def getVLUN(self, volumeName):
        """Get information about a VLUN.

        :param volumeName: The volume name of the VLUN to find
        :type name: str

        :returns: VLUN

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            -  NON_EXISTENT_VLUN - VLUN doesn't exist

        """
        # Check if the WSAPI supports VLUN querying. If it is supported
        # request only the VLUNs that are associated with the volume.
        if self.vlun_query_supported:
            query = '"volumeName EQ %s"' % volumeName
            response, body = self.http.get('/vluns?query=%s' %
                                           quote(query.encode("utf8")))

            # Return the first VLUN found for the volume.
            for vlun in body.get('members', []):
                return vlun
        else:
            vluns = self.getVLUNs()
            if vluns:
                for vlun in vluns['members']:
                    if vlun['volumeName'] == volumeName:
                        return vlun

        raise exceptions.HTTPNotFound({'code': 'NON_EXISTENT_VLUN',
                                       'desc': "VLUN '%s' was not found" %
                                               volumeName})

    def createVLUN(self, volumeName, lun=None, hostname=None, portPos=None,
                   noVcn=None, overrideLowerPriority=None, auto=False):
        """Create a new VLUN.

        When creating a VLUN, the volumeName is required. The lun member is
        not required if auto is set to True.
        Either hostname or portPos (or both in the case of matched sets) is
        also required.  The noVcn and overrideLowerPriority members are
        optional.

        :param volumeName: Name of the volume to be exported
        :type volumeName: str
        :param lun: The new LUN id
        :type lun: int
        :param hostname:  Name of the host which the volume is to be exported.
        :type hostname: str
        :param portPos: 'portPos' (dict) - System port of VLUN exported to. It
                        includes node number, slot number, and card port number
        :type portPos: dict
        .. code-block:: python

            portPos = {'node': 1,   # System node (0-7)
                       'slot': 2,   # PCI bus slot in the node (0-5)
                       'port': 1}   # Port number on the FC card (0-4)

        :param noVcn: A VLUN change notification (VCN) not be issued after
                      export (-novcn). Default: False.
        :type noVcn: bool
        :param overrideLowerPriority: Existing lower priority VLUNs will
                be overridden (-ovrd). Use only if hostname member exists.
                Default: False.
        :type overrideLowerPriority: bool

        :returns: the location of the VLUN

        """
        info = {'volumeName': volumeName}

        if lun is not None:
            info['lun'] = lun

        if hostname:
            info['hostname'] = hostname

        if portPos:
            info['portPos'] = portPos

        if noVcn:
            info['noVcn'] = noVcn

        if overrideLowerPriority:
            info['overrideLowerPriority'] = overrideLowerPriority

        if auto:
            info['autoLun'] = True
            info['maxAutoLun'] = 0
            info['lun'] = 0

        headers, body = self.http.post('/vluns', body=info)
        if headers:
            location = headers['location'].replace('/api/v1/vluns/', '')
            return location
        else:
            return None

    def deleteVLUN(self, volumeName, lunID, hostname=None, port=None):
        """Delete a VLUN.

        :param volumeName: the volume name of the VLUN
        :type name: str
        :param lunID: The LUN ID
        :type lunID: int
        :param hostname: Name of the host which the volume is exported.
                         For VLUN of port type,the value is empty
        :type hostname: str
        :param port: Specifies the system port of the VLUN export.  It includes
                     the system node number, PCI bus slot number, and card port
                     number on the FC card in the format
                     <node>:<slot>:<cardPort>
        :type port: dict
        .. code-block:: python

            port = {'node': 1,   # System node (0-7)
                    'slot': 2,   # PCI bus slot in the node (0-5)
                    'port': 1}   # Port number on the FC card (0-4)

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Incomplete VLUN info. Missing
            volumeName or lun, or both hostname and port.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PORT_SELECTION - Specified port is invalid.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - The LUN specified exceeds expected
            range.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VLUN - The VLUN does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_PORT - The port does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        """

        vlun = "%s,%s" % (volumeName, lunID)

        if hostname:
            vlun += ",%s" % hostname
        else:
            if port:
                vlun += ","

        if port:
            vlun += ",%s:%s:%s" % (port['node'],
                                   port['slot'],
                                   port['cardPort'])

        response, body = self.http.delete('/vluns/%s' % vlun)

    # VolumeSet methods
    def findVolumeSet(self, name):
        """
        Find the first Volume Set that contains a target volume.  If a
        volume set other than the first one found is desired use
        findAllVolumeSets and search the results.

        :param name: the volume name
        :type name: str

        :returns: The name of the first volume set that contains the target
        volume, otherwise None.
        """

        vvset_names = self.findAllVolumeSets(name)
        vvset_name = None
        if vvset_names:
            vvset_name = vvset_names[0]['name']

        return vvset_name

    def findAllVolumeSets(self, name):
        """
        Return a list of every Volume Set the given volume is a part of.
        The list can contain zero, one, or multiple items.

        :param name: the volume name
        :type name: str

        :returns: a list of Volume Set dicts

        .. code-block:: python

            vvset_names = [{
                'name': "volume_set_1",       # The name of the volume set
                'comment': 'Samplet VVSet',   # The volume set's comment
                'domain': 'my_domain',        # The volume set's domain
                'setmembers': ['V1', 'V2']    # List of strings containing
                                              # the volumes that are members
                                              # of this volume set
            },
            ...
            ]

        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - Internal inconsistency error in vol
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - Illegal op on system vol
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Illegal op on internal vol
        """
        vvset_names = []
        volume_sets = self.getVolumeSets()
        for volume_set in volume_sets['members']:
            if 'setmembers' in volume_set and name in volume_set['setmembers']:
                vvset_names.append(volume_set)
        return vvset_names

    def getVolumeSets(self):
        """
        Get Volume Sets

        :returns: Array of Volume Sets
        """
        response, body = self.http.get('/volumesets')
        return body

    def getVolumeSet(self, name):
        """
        Get information about a Volume Set

        :param name: The name of the Volume Set to find
        :type name: str

        :returns: Volume Set

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set doesn't exist
        """
        response, body = self.http.get('/volumesets/%s' % name)
        return body

    def createVolumeSet(self, name, domain=None, comment=None,
                        setmembers=None):
        """
        This creates a new volume set

        :param name: the volume set to create
        :type set_name: str
        :param domain: the domain where the set lives
        :type domain: str
        :param comment: the comment for on the vv set
        :type comment: str
        :param setmembers: the vv to add to the set, the existence of the vv
        will not be checked
        :type setmembers: array

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to
            perform this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal
            inconsistency error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        """
        info = {'name': name}

        if domain:
            info['domain'] = domain

        if comment:
            info['comment'] = comment

        if setmembers:
            members = {'setmembers': setmembers}
            info = self._mergeDict(info, members)

        response, body = self.http.post('/volumesets', body=info)

    def deleteVolumeSet(self, name):
        """
        This removes a volume set. You must clear all QOS rules before a volume
        set can be deleted.

        :param name: the volume set to remove
        :type name: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXPORTED_VLUN - The host set has exported VLUNs. The VV set was
            exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - VVSET_QOS_TARGET - The object is already part of the set.
        """
        response, body = self.http.delete('/volumesets/%s' % name)

    def modifyVolumeSet(self, name, action=None, newName=None, comment=None,
                        flashCachePolicy=None, setmembers=None):
        """
        This modifies a volume set by adding or remove a volume from the volume
        set. It's actions is based on the enums SET_MEM_ADD or SET_MEM_REMOVE.

        :param action: add or remove volume from the set
        :type action: enum
        :param name: the volume set name
        :type name: str
        :param newName: new name of set
        :type newName: str
        :param comment: the comment for on the vv set
        :type comment: str
        :param flashCachePolicy: the flash-cache policy for the vv set
        :type comment: FLASH_CACHED_ENABLED or FLASH_CACHE_DISABLED
        :param setmembers: the vv to add to the set, the existence of the vv
                           will not be checked
        :type setmembers: array

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - MEMBER_NOT_IN_SET - The object is not part of the set.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to
            perform this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal
            inconsistency error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Invalid input (parameters cannot be
            present at the same time).
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid contains one or more illegal
            characters.
        """
        info = {}

        if action:
            info['action'] = action

        if newName:
            info['newName'] = newName

        if comment:
            info['comment'] = comment

        if flashCachePolicy:
            info['flashCachePolicy'] = flashCachePolicy

        if setmembers:
            members = {'setmembers': setmembers}
            info = self._mergeDict(info, members)

        response = self.http.put('/volumesets/%s' % name, body=info)
        return response

    # QoS Priority Optimization methods
    def addVolumeToVolumeSet(self, set_name, name):
        """
        This adds a volume to a volume set

        :param set_name: the volume set name
        :type set_name: str
        :param name: the volume name to add
        :type name: str
        """
        return self.modifyVolumeSet(set_name, action=self.SET_MEM_ADD,
                                    setmembers=[name])

    def removeVolumeFromVolumeSet(self, set_name, name):
        """
        Remove a volume from a volume set

        :param set_name: the volume set name
        :type set_name: str
        :param name: the volume name to add
        :type name: str
        """
        return self.modifyVolumeSet(set_name, action=self.SET_MEM_REMOVE,
                                    setmembers=[name])

    def createSnapshotOfVolumeSet(self, name, copyOfName, optional=None):
        """Create a snapshot of an existing Volume Set.

        :param name: Name of the Snapshot. The vvname pattern is described in
                     "VV Name Patterns" in the HPE 3PAR Command Line Interface
                     Reference, which is available at the following
                     website: http://www.hp.com/go/storage/docs
        :type name: str
        :param copyOfName: The volume set you want to snapshot
        :type copyOfName: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'id': 12,                   # Specifies ID of the volume set
                                            # set, next by default
                'comment': "some comment",
                'readOnly': True,           # Read Only
                'expirationHours': 36,      # time from now to expire
                'retentionHours': 12        # time from now to expire
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INVALID_INPUT_VV_PATTERN - Invalid volume pattern specified
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - EMPTY_SET - The set is empty
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - VV_LIMIT_REACHED - Maximum number of volumes reached
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The storage volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_TO_READONLY_SNAP - Creating a
            read-only copy from a read-only volume is not permitted
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - NO_SNAP_CPG - No snapshot CPG has been configured for the volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SNAP_PARENT_SAME_BASE - Two parent
            snapshots share thesame base volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS - Invalid
            operation. Online copyis in progress
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - VV_ID_LIMIT_REACHED - Max number of volumeIDs has been reached
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_UNAVAILABLE - The volume is not accessible
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - SNAPSHOT_LIMIT_REACHED - Max number of snapshots has been reached
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - CPG_ALLOCATION_WARNING_REACHED - The CPG has reached the
            allocation warning
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV
            conversion is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is
            in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - Cannot modify a peer volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Illegal op on internal vol
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - EXISTENT_ID - An ID exists
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - Internal inconsistency error in vol
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_RETAIN_GT_EXPIRE - Retention time is greater than
            expiration time.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TIME - Invalid time specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_SNAPSHOT_NOT_SAME_TYPE - Some snapshots in the
            volume set are read-only, some are read-write
        """

        parameters = {'name': name}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action': 'createSnapshot',
                'parameters': parameters}

        response, body = self.http.post('/volumesets/%s' % copyOfName,
                                        body=info)
        return body

    # QoS Priority Optimization methods
    def setQOSRule(self, set_name, max_io=None, max_bw=None):
        """
        Set a QOS Rule on a volume set

        :param set_name: the volume set name for the rule.
        :type set_name: str
        :param max_io: the maximum IOPS value
        :type max_io: int
        :param max_bw: The maximum Bandwidth
        :type max_bw:
        """
        cmd = ['setqos']
        if max_io is not None:
            cmd.extend(['-io', '%s' % max_io])
        if max_bw is not None:
            cmd.extend(['-bw', '%sM' % max_bw])
        cmd.append('vvset:' + set_name)
        result = self._run(cmd)

        if result:
            msg = result[0]
        else:
            msg = None

        if msg:
            if 'no matching QoS target found' in msg:
                raise exceptions.HTTPNotFound(error={'desc': msg})
            else:
                raise exceptions.SetQOSRuleException(message=msg)

    def queryQoSRules(self):
        """
        Get QoS Rules

        :returns: Array of QoS Rules
        """
        response, body = self.http.get('/qos')
        return body

    def queryQoSRule(self, targetName, targetType='vvset'):
        """
        Query a QoS rule

        :param targetType: target type is vvset or sys
        :type targetType: str
        :param targetName: the name of the target. When targetType is sys,
                           target name must be sys:all_others.
        :type targetName: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
           - NON_EXISTENT_QOS_RULE - QoS rule does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
           - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        """
        response, body = self.http.get('/qos/%(targetType)s:%(targetName)s' %
                                       {'targetType': targetType,
                                        'targetName': targetName})
        return body

    def createQoSRules(self, targetName, qosRules,
                       target_type=TARGET_TYPE_VVSET):
        """
        Create QOS rules

        The QoS rule can be applied to VV sets. By using sys:all_others,
        you can apply the rule to all volumes in the system for which no
        QoS rule has been defined.

        ioMinGoal and ioMaxLimit must be used together to set I/O limits.
        Similarly, bwMinGoalKB and bwMaxLimitKB must be used together.

        If ioMaxLimitOP is set to 2 (no limit), ioMinGoalOP must also be
        to set to 2 (zero), and vice versa. They cannot be set to
        'none' individually. Similarly, if bwMaxLimitOP is set to 2 (no
        limit), then bwMinGoalOP must also be set to 2.

        If ioMaxLimitOP is set to 1 (no limit), ioMinGoalOP must also be
        to set to 1 (zero) and vice versa. Similarly, if bwMaxLimitOP is
        set to 1 (zero), then bwMinGoalOP must also be set to 1.

        The ioMinGoalOP and ioMaxLimitOP fields take precedence over
        the ioMinGoal and ioMaxLimit fields.

        The bwMinGoalOP and bwMaxLimitOP fields take precedence over
        the bwMinGoalKB and bwMaxLimitKB fields

        :param target_type: Type of QoS target, either enum
                            TARGET_TYPE_VVS or TARGET_TYPE_SYS.
        :type target_type: enum
        :param targetName: the name of the target object on which the QoS
                           rule will be created.
        :type targetName: str
        :param qosRules: QoS options
        :type qosRules: dict

        .. code-block:: python

            qosRules = {
                'priority': 2,         # priority enum
                'bwMinGoalKB': 1024,   # bandwidth rate minimum goal in
                                       #   kilobytes per second
                'bwMaxLimitKB': 1024,  # bandwidth rate maximum limit in
                                       #   kilobytes per second
                'ioMinGoal': 10000,    # I/O-per-second minimum goal
                'ioMaxLimit': 2000000, # I/0-per-second maximum limit
                'enable': True,        # QoS rule for target enabled?
                'bwMinGoalOP': 1,      # zero none operation enum, when set to
                                       #   1, bandwidth minimum goal is 0
                                       # when set to 2, the bandwidth mimumum
                                       #   goal is none (NoLimit)
                'bwMaxLimitOP': 1,     # zero none operation enum, when set to
                                       #   1, bandwidth maximum limit is 0
                                       # when set to 2, the bandwidth maximum
                                       #   limit is none (NoLimit)
                'ioMinGoalOP': 1,      # zero none operation enum, when set to
                                       #   1, I/O minimum goal is 0
                                       # when set to 2, the I/O minimum goal is
                                       #   none (NoLimit)
                'ioMaxLimitOP': 1,     # zero none operation enum, when set to
                                       #   1, I/O maximum limit is 0
                                       # when set to 2, the I/O maximum limit
                                       #   is none (NoLimit)
                'latencyGoal': 5000,   # Latency goal in milliseconds
                'defaultLatency': False # Use latencyGoal or defaultLatency?
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected
          range.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
          - NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit
          should be greater than the minimum goal.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit
          should be greater than the mimimum goal.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_BELOW_RANGE - I/O-per-second limit is below range.
          Bandwidth limit is below range.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
          - UNLICENSED_FEATURE - The system is not licensed for QoS.
        """
        info = {'name': targetName,
                'type': target_type}

        info = self._mergeDict(info, qosRules)

        response, body = self.http.post('/qos', body=info)
        return body

    def modifyQoSRules(self, targetName, qosRules, targetType='vvset'):
        """
        Modify an existing QOS rules

        The QoS rule can be applied to VV sets. By using sys:all_others,
        you can apply the rule to all volumes in the system for which no
        QoS rule has been defined.

        ioMinGoal and ioMaxLimit must be used together to set I/O limits.
        Similarly, bwMinGoalKB and bwMaxLimitKB must be used together.

        If ioMaxLimitOP is set to 2 (no limit), ioMinGoalOP must also be
        to set to 2 (zero), and vice versa. They cannot be set to
        'none' individually. Similarly, if bwMaxLimitOP is set to 2 (no
        limit), then bwMinGoalOP must also be set to 2.

        If ioMaxLimitOP is set to 1 (no limit), ioMinGoalOP must also be
        to set to 1 (zero) and vice versa. Similarly, if bwMaxLimitOP is
        set to 1 (zero), then bwMinGoalOP must also be set to 1.

        The ioMinGoalOP and ioMaxLimitOP fields take precedence over
        the ioMinGoal and ioMaxLimit fields.

        The bwMinGoalOP and bwMaxLimitOP fields take precedence over
        the bwMinGoalKB and bwMaxLimitKB fields

        :param targetName: the name of the target object on which the QoS
                           rule will be created.
        :type targetName: str
        :param targetType: Type of QoS target, either vvset or sys
        :type targetType: str
        :param qosRules: QoS options
        :type qosRules: dict

        .. code-block:: python

            qosRules = {
                'priority': 2,         # priority enum
                'bwMinGoalKB': 1024,   # bandwidth rate minimum goal in
                                       # kilobytes per second
                'bwMaxLimitKB': 1024,  # bandwidth rate maximum limit in
                                       # kilobytes per second
                'ioMinGoal': 10000,    # I/O-per-second minimum goal.
                'ioMaxLimit': 2000000, # I/0-per-second maximum limit
                'enable': True,        # QoS rule for target enabled?
                'bwMinGoalOP': 1,      # zero none operation enum, when set to
                                       # 1, bandwidth minimum goal is 0
                                       # when set to 2, the bandwidth minimum
                                       # goal is none (NoLimit)
                'bwMaxLimitOP': 1,     # zero none operation enum, when set to
                                       # 1, bandwidth maximum limit is 0
                                       # when set to 2, the bandwidth maximum
                                       # limit is none (NoLimit)
                'ioMinGoalOP': 1,      # zero none operation enum, when set to
                                       # 1, I/O minimum goal minimum goal is 0
                                       # when set to 2, the I/O minimum goal is
                                       # none (NoLimit)
                'ioMaxLimitOP': 1,     # zero none operation enum, when set to
                                       # 1, I/O maximum limit is 0
                                       # when set to 2, the I/O maximum limit
                                       # is none (NoLimit)
                'latencyGoal': 5000,   # Latency goal in milliseconds
                'defaultLatency': False # Use latencyGoal or defaultLatency?
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected
            range.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_IO_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit
            should be greater than the minimum goal.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit
            should be greater than the minimum goal.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_BELOW_RANGE - I/O-per-second limit is below
            range. Bandwidth limit is below range.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
                     UNLICENSED_FEATURE - The system is not licensed for QoS.
        """
        response = self.http.put('/qos/%(targetType)s:%(targetName)s' %
                                 {'targetType': targetType,
                                  'targetName': targetName},
                                 body=qosRules)
        return response

    def deleteQoSRules(self, targetName, targetType='vvset'):
        """Clear and Delete QoS rules.

        :param targetType: target type is vvset or sys
        :type targetType: str
        :param targetName: the name of the target. When targetType is sys,
                           target name must be sys:all_others.
        :type targetName: str

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound` -
                        NON_EXISTENT_QOS_RULE - QoS rule does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest` -
                        INV_INPUT_ILLEGAL_CHAR - Illegal character in the input

        """
        response, body = self.http.delete(
            '/qos/%(targetType)s:%(targetName)s' %
            {'targetType': targetType, 'targetName': targetName})
        return body

    def setVolumeMetaData(self, name, key, value):
        """This is used to set a key/value pair metadata into a volume.
        If the key already exists on the volume the value will be updated.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str
        :param value: the metadata value
        :type value: str


        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: string length exceeds
            limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Required fields missing
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_UNREC_NAME - Unrecognized name
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist

        """
        key_exists = False
        info = {
            'key': key,
            'value': value
        }

        try:
            response, body = self.http.post('/volumes/%s/objectKeyValues' %
                                            name, body=info)
        except exceptions.HTTPConflict:
            key_exists = True
        except Exception:
            raise

        if key_exists:
            info = {
                'value': value
            }
            response, body = self.http.put(
                '/volumes/%(name)s/objectKeyValues/%(key)s' %
                {'name': name, 'key': key}, body=info)

        return response

    def getVolumeMetaData(self, name, key):
        """This is used to get a key/value pair metadata from a volume.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str

        :returns: dict with the requested key's data.

        .. code-block:: python

            data = {
                # time of creation in seconds format
                'creationTimeSec': 1406074222
                # the date/time the key was added
                'date_added': 'Mon Jul 14 16:09:36 PDT 2014',
                'value': 'data'     # the value associated with the key
                'key': 'key_name'   # the key name
                # time of creation in date format
                'creationTime8601': '2014-07-22T17:10:22-07:00'
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_OBJECT_KEY - Object key does not exist

        """
        response, body = self.http.get(
            '/volumes/%(name)s/objectKeyValues/%(key)s' %
            {'name': name, 'key': key})

        return body

    def getAllVolumeMetaData(self, name):
        """This is used to get all key/value pair metadata from a volume.

        :param name: the volume name
        :type name: str

        :returns: dict with all keys and associated data.

        .. code-block:: python

            keys = {
                'total': 2,
                'members': [
                    {
                        # time of creation in seconds format
                        'creationTimeSec': 1406074222
                        # the date/time the key was added
                        'date_added': 'Mon Jul 14 16:09:36 PDT 2014',
                        'value': 'data'     # the value associated with the key
                        'key': 'key_name'   # the key name
                        # time of creation in date format
                        'creationTime8601': '2014-07-22T17:10:22-07:00'
                    },
                    {
                        # time of creation in seconds format
                        'creationTimeSec': 1406074222
                        # the date/time the key was added
                        'date_added': 'Mon Jul 14 16:09:36 PDT 2014',
                        'value': 'data'     # the value associated with the key
                        'key': 'key_name_2' # the key name
                        # time of creation in date format
                        'creationTime8601': '2014-07-22T17:10:22-07:00'
                    }
                ]
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist

        """
        response, body = self.http.get('/volumes/%s/objectKeyValues' % name)

        return body

    def removeVolumeMetaData(self, name, key):
        """This is used to remove a metadata key/value pair from a volume.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str

        :returns: None

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_OBJECT_KEY - Object key does not exist

        """
        response, body = self.http.delete(
            '/volumes/%(name)s/objectKeyValues/%(key)s' %
            {'name': name, 'key': key})

        return body

    def findVolumeMetaData(self, name, key, value):
        """Determines whether a volume contains a specific key/value pair.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str
        :param value: the metadata value
        :type value: str

        :returns: bool

        """
        try:
            contents = self.getVolumeMetaData(name, key)
            if contents['value'] == value:
                return True
        except Exception:
            pass

        return False

    def getRemoteCopyInfo(self):
        """
        Querying Overall Remote-Copy Information

        :returns: Overall Remote Copy Information
        """
        response, body = self.http.get('/remotecopy')
        return body

    def getRemoteCopyGroups(self):
        """
        Returns information on all Remote Copy Groups

        :returns: list of Remote Copy Groups

        """
        response, body = self.http.get('/remotecopygroups')
        return body

    def getRemoteCopyGroup(self, name):
        """
        Returns information on one Remote Copy Group

        :param name: the remote copy group name
        :type name: str

        :returns: Remote Copy Group

        """
        response, body = self.http.get('/remotecopygroups/%s' % name)
        return body

    def getRemoteCopyGroupVolumes(self, remoteCopyGroupName):
        """
        Returns information on all volumes in a Remote Copy Groups
         :param remoteCopyGroupName: the remote copy group name
        :type name: str
         :returns: list of volumes in a Remote Copy Groups
         """
        response, body = self.http.get(
            '/remotecopygroups/%s/volumes' % (remoteCopyGroupName)
        )
        return body

    def getRemoteCopyGroupVolume(self, remoteCopyGroupName, volumeName):
        """
        Returns information on one volume of a Remote Copy Group
         :param remoteCopyGroupName: the remote copy group name
        :type name: str
        :param volumeName: the remote copy group name
        :type name: str
         :returns: RemoteVolume
         """
        response, body = self.http.get(
            '/remotecopygroups/%s/volumes/%s' %
            (remoteCopyGroupName, volumeName)
        )
        return body

    def createRemoteCopyGroup(self, name, targets, optional=None):
        """
        Creates a remote copy group

        :param name: the remote copy group name
        :type name: str
        :param targets: Specifies the attributes of the target of the
                        remote-copy group.
        :type targets: list
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            targets = [
                {
                    "targetName": "name",      # Target name associated with
                                               # the remote-copy group to be
                                               # created
                    "mode": 2,                 # Specifies the volume group
                                               # mode.
                                               # 1 - The remote-copy group mode
                                               #     is synchronous.
                                               # 2 - The remote-copy group mode
                                               #     is periodic.
                                               # 3 - The remote-copy group mode
                                               #     is periodic.
                                               # 4 - Remote-copy group mode is
                                               #     asynchronous.
                    "userCPG": "SOME_CPG",     # Specifies the user CPG
                                               # that will be used for
                                               # volumes that are
                                               # autocreated on the
                                               # target.
                    "snapCPG": "SOME_SNAP_CPG" # Specifies the snap CPG
                                               # that will be used for
                                               # volumes that are
                                               # autocreated on the
                                               # target.
                }
            ]

            optional = {
                "localSnapCPG" : "SNAP_CPG",   # Specifies the local snap
                                               # CPG that will be used for
                                               # volumes that are autocreated.
                "localUserCPG" : "SOME_CPG",   # Specifies the local user
                                               # CPG that will be used for
                                               # volumes that are autocreated.
                "domain" : "some-domain"       # Specifies the attributes of
                                               # the target of the
                                               # remote-copy group.
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid character in the remote-copy
            group or volume name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - EXISTENT_RCOPY_GROUP - The remote-copy group already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_TOO_MANY_TARGETS - Too many remote-copy group targets
            have been specified.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - The mode is not valid.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_TARGET_NOT_UNIQUE - The remote-copy group target is
            not unique.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_IS_NOT_READY - The remote-copy configuration is not ready
            for commands.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MODE_NOT_SUPPORTED - The remote-copy group mode is
            not supported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_MAX_GROUP_REACHED_PERIODIC - The maximum number of
            remote-copy groups in periodic mode has been reached.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_MAX_GROUP_REACHED_PERIODIC - The maximum number of
            remote-copy groups in periodic mode has been reached.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_SECONDARY_GROUP_MORE_THAN_ONE_BACKUP_TARGET -
            Secondary groups should have only one target that is not a
            backup.
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - RCOPY_GROUP_MORE_THAN_ONE_SYNC_TARGET - Remote-copy groups can
            have no more than one synchronous-mode target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - RCOPY_GROUP_MORE_THAN_ONE_PERIODIC_TARGET - Remote-copy groups
            can have no more than one periodic-mode target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_ONE_TO_ONE_CONFIG_FOR_MIXED_MODE - Mixed mode is
            supported in a 1-to-1 remote-copy configuration.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotImplemented`
            - RCOPY_TARGET_IN_PEER_PERSISTENCE_SYNC_GROUP_ONLY - The
            remote-copy target is configured with peer persistence; only
            synchronous groups can be added.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotImplemented`
            - RCOPY_TARGET_MODE_NOT_SUPPORTED - The remote-copy target
            mode is not supported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotImplemented`
            - RCOPY_TARGET_MULTI_TARGET_NOT_SUPPORTED - The remote-copy target
            was created in an earlier version of the HP 3PAR OS that does not
            support multiple targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotImplemented`
            - RCOPY_TARGET_VOL_AUTO_CREATION_NOT_SUPPORTED - The remote-copy
            target is in an older version of the HP 3PAR OS that does not
            support autocreation of
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_MIXED_MODES_ON_ONE_TARGET - Remote-copy groups
            with different modes on a single target are not supported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN_SAME_DOMAIN - Snap CPG is not in the same domain as
            the user CPG.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NON_EXISTENT_DOMAIN - Domain doesn't exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_HAS_NO_CPG - No CPG has been defined for the
            remote-copy group on the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - RCOPY_MAX_SYNC_TARGET_REACHED - The maximum number of remote-copy
            synchronous targets has been reached.
        :raises: :class:`~hpe3parclient.exceptions.HTTPServiceUnavailable`
            - RCOPY_MAX_PERIODIC_TARGET_REACHED - The maximum number of
            remote-copy periodic targets has been reached.
        """
        parameters = {'name': name, 'targets': targets}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.post('/remotecopygroups',
                                        body=parameters)
        return body

    def removeRemoteCopyGroup(self, name, keep_snap=False):
        """
        Deletes a remote copy group

        :param name: the remote copy group name
        :type name: str
        :param keep_snap: used to retain the local volume resynchronization
                          snapshot. NOTE: to retain the snapshot pass 'true'
                          to keep_snap
        :type keep_snap: bool

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_BUSY - The remote-copy group is currently busy;
            retry later.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_TARGET_IS_NOT_READY - The remote-copy group target is not
            ready.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation
            should be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_RENAME_RESYNC_SNAPSHOT_FAILED - Renaming of the
            remote-copy group resynchronization snapshot failed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IN_FAILOVER_STATE - The remote-copy group is in
            failover state; both the source system and the target system
            are in the primary state.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - RCOPY_GROUP_TARGET_VOLUME_MISMATCH - Secondary group on target
            system has a mismatched volume configuration.
        """
        if keep_snap:
            snap_query = 'true'
        else:
            snap_query = 'false'

        response, body = self.http.delete(
            '/remotecopygroups/%(name)s?keepSnap=%(snap_query)s' %
            {'name': name, 'snap_query': snap_query})
        return body

    def modifyRemoteCopyGroup(self, name, optional=None):
        """
        Modifies a remote copy group

        :param name: the remote copy group name
        :type name: str
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
                "localUserCPG": "CPG",      # Specifies the local user
                                            # CPG that will be used for
                                            # autocreated volumes.
                "localSnapCPG": "SNAP_CPG", # Specifies the local snap
                                            # CPG that will be used for
                                            # autocreated volumes.
                "targets": targets,         # Specifies the attributes of
                                            # the remote-copy group
                                            # target.
                "unsetUserCPG": False,      # If True, this option
                                            # unsets the localUserCPG and
                                            # remoteUserCPG of the
                                            # remote-copy group.
                "unsetSnapCPG": Flase       # If True, this option
                                            # unsets the localSnapCPG and
                                            # remoteSnapCPG of the
                                            # remote-copy group.
            }

            targets = [
                {
                    "targetName": "name",        # Specifies the target name
                                                 # associated with the
                                                 # remote-copy group to be
                                                 # created.
                    "remoteUserCPG": "CPG",      # Specifies the user CPG
                                                 # on the target that will be
                                                 # used for autocreated
                                                 # volumes.
                    "remoteSnapCPG": "SNAP_CPG", # Specifies the snap CPG
                                                 # on the target that will be
                                                 # used for autocreated
                                                 # volumes.
                    "syncPeriod": 300,           # Specifies that asynchronous
                                                 # periodic remote-copy groups
                                                 # should be synchronized
                                                 # periodically to the
                                                 # <period_value>.
                                                 # Range is 300 - 31622400
                                                 # seconds (1 year).
                    "rmSyncPeriod": False,       # If True, this option
                                                 # resets the syncPeriod
                                                 # time to 0 (zero).
                                                 # If False, the
                                                 # syncPeriod value is 0
                                                 # (zero), then Ignore.
                                                 # If False, and the
                                                 # syncPeriod value is
                                                 # positive, then then the
                                                 # synchronizaiton period
                                                 # is set.
                    "mode": 2,                   # Volume group mode. Can be
                                                 # either synchronous or
                                                 # periodic.
                                                 # 1 - The remote-copy group
                                                 #     mode is synchronous.
                                                 # 2 - The remote-copy group
                                                 #     mode is periodic.
                                                 # 3 - The remote-copy group
                                                 #     mode is periodic.
                                                 # 4 - Remote-copy group mode
                                                 #     is asynchronous.
                    "snapFrequency": 300,        # Async mode only. Specifies
                                                 # the interval in seconds at
                                                 # which Remote Copy takes
                                                 # coordinated snapshots. Range
                                                 # is 300-31622400 seconds
                                                 # (1 year).
                    "rmSnapFrequency": False,    # If True, this option resets
                                                 # the snapFrequency time
                                                 # rmSnapFrequency to 0 (zero).
                                                 # If False and the
                                                 # snapFrequency value is 0
                                                 # (zero), then Ignore. If
                                                 # False, and the snapFrequency
                                                 # value is positive, sets the
                                                 # snapFrequency value.
                    "policies": policies         # The policy assigned to
                                                 # the remote-copy group.
                }
            ]

            policies = {
                "autoRecover": False,       # If the remote copy is stopped
                                            # as a result of links going
                                            # down, the remote-copy group
                                            # can be automatically
                                            # restarted after the links
                                            # come back up.
                "overPeriodAlert": False,   # If synchronization of an
                                            # asynchronous periodic
                                            # remote-copy group takes
                                            # longer to complete than its
                                            # synchronization period, an
                                            # alert is generated.
                "autoFailover": False,      # Automatic failover on a
                                            # remote-copy group.
                "pathManagement": False     # Automatic failover on a
                                            # remote-copy group.
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation should
            be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_NOT_PERIODIC - Target in group is not periodic.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_POLICY_FOR_PERIODIC_GROUP - Invalid policy for a
            periodic group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_POLICY_FOR_SYNC_GROUP - Invalid policy for a
            synchronous target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN_SAME_DOMAIN - Snap CPG is not in the same domain as
            the user CPG.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BELOW_RANGE - The minimum allowable period is 300
            seconds.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - Invalid input: the period is too long.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_OPERATION_ON_MULTIPLE_TARGETS - The operation is
            not supported on multiple targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_TARGET_NOT_UNIQUE - The remote-copy group target is
            not unique.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET_NUMBER - The wrong number of targets is
            specified for the remote-copy group.
        """
        parameters = {}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.put('/remotecopygroups/%s' % name,
                                       body=parameters)
        return body

    def addVolumeToRemoteCopyGroup(self, name, volumeName, targets,
                                   optional=None, useHttpPost=False):
        """
        Adds a volume to a remote copy group

        :param name: Name of the remote copy group
        :type name: string
        :param volumeName: Specifies the name of the existing virtual
                           volume to be admitted to an existing remote-copy
                           group.
        :type volumeName: string
        :param targets: Specifies the attributes of the target of the
                        remote-copy group.
        :type targets: list
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            targets = [
                {
                    "targetName": "name",            # The target name
                                                     # associated with this
                                                     # group.
                    "secVolumeName": "sec_vol_name"  # Specifies the name of
                                                     # the secondary volume
                                                     # on the target system.
                }
            ]

            optional = {
                "snapshotName": "snapshot_name", # The optional read-only
                                                 # snapshotName is a
                                                 # starting snapshot when
                                                 # the group is started
                                                 # without performing a
                                                 # full resynchronization.
                                                 # Instead, for
                                                 # synchronized groups,
                                                 # the volume
                                                 # synchronizes deltas
                                                 # between this
                                                 # snapshotName and
                                                 # the base volume. For
                                                 # periodic groups, the
                                                 # volume synchronizes
                                                 # deltas between this
                                                 # snapshotName and a
                                                 # snapshot of the base.
                "volumeAutoCreation": False,     # If set to true, the
                                                 # secondary volumes
                                                 # should be created
                                                 # automatically on the
                                                 # target using the CPG
                                                 # associated with the
                                                 # remote-copy group on
                                                 # that target.
                "skipInitialSync": False         # If set to true, the
                                                 # volume should skip the
                                                 # initial sync. This is
                                                 # for the admission of
                                                 # volumes that have
                                                 # been pre-synced with
                                                 # the target volume.
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - volume doesn't exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SNAPSHOT - The specified snapshot does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_SNAPSHOT_IS_RW - The specified snapshot can only be
            read-only.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_IS_RO - The volume to be admitted to the
            remote-copy group cannot be read-only.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_HAS_NO_CPG - No CPG has been defined for the
            remote-copy group on the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_EXISTENT_VOL - The specified volume is
            already in the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_EXISTENT_VOL_ON_TARGET - The specified secondary
            volume to be automatically created already exists on the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_SIZE_NOT_MATCH - The size of the volume added to
            the remote-copy group does not match the size of the volume on
            the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - RCOPY_GROUP_NON_EXISTENT_VOL_ON_TARGET - The specified secondary
            volume does not exist on the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_NO_SNAPSHOT_SPACE - The volume to be admitted
            into the remote-copy group requires that snapshot space be
            allocated.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_TARGET_VOL_NO_SNAPSHOT_SPACE - The specified
            secondary volumes on the target require snapshot space.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_IS_PHYSICAL_COPY - A physical copy cannot
            be added to a remote-copy group
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MAX_VOL_REACHED_PERIODIC - The number of
            periodic-mode volumes on the system has reached the limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MAX_VOL_REACHED_SYNC - The number of
            synchronous-mode volumes on the system has reached the limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MAX_VOL_REACHED - The number of volumes on the
            system has reached the limit.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_IS_NOT_READY - The remote-copy configuration is not ready
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_INTERNAL_CONSISTENCY_ERR - The volume to be
            admitted into the remote-copy group has an internal consistency
            error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_BEING_REMOVED - The volume to be admitted into the
            remote-copy group is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUPSNAPSHOT_PARENT_MISMATCH - The names of the snapshot
            and its parent do not match.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_TARGET_VOL_EXPORTED - Secondary volumes cannot be
            admitted when they are exported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_IS_PEER_PROVISIONED - A peer-provisioned volume
            cannot be admitted into a remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_ONLINE_CONVERSION - Online volume conversions do
            not support remote copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_ONLINE_PROMOTE - Online volume promotes do not
            support remote copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_ONLINE_COPY - Online volume copies do not support
            remote copy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_CLEAN_UP - Cleanup of internal volume is in
            progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_IS_INTERNAL - Internal volumes cannot be admitted
            into a remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_NOT_IN_SAME_DOMAIN - The remote-copy group has a
            different domain than the volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_BUSY - The remote-copy group is currently busy;
            retry later.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_VOL_IN_OTHER_GROUP - The volume is already in
            another remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET_NUMBER - The wrong number of targets is
            specified for the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_NOT_SUPPORT_VOL_ID - The target for the remote-copy
            group does not support volume IDs.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_SELF_MIRRORED - The target is self-mirrored.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_TARGET_VOL_IS_RO - The remote-copy target volume
            cannot be read-only.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation should
            be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_TARGET_IS_NOT_READY - The remote-copy group target is not
            ready.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotImplemented`
            - RCOPY_UNSUPPORTED_TARGET_VERSION - The target HP 3PAR OS version
            is not supported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MULTIPLE_VOL_IN_SAME_FAMILY - A remote-copy group
            cannot contain multiple volumes in the same family tree.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_MULTIPLE_RW_SNAPSHOT_IN_SAME_FAMILY - Only one
            read/write snapshot in the same family can be added to a
            remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_SYNC_SNAPSHOT_IN_MULTIPLE_TARGET - A synchronization
            snapshot cannot be set with multiple targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_ADD_VOL_FAILED - Failed to add volume to the
            remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_ADD_VOL_FAILED_PARTIAL - Adding volume to
            remote-copy group succeeded on some targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_SET_AUTO_CREATED - The set was created
            automatically Members cannot be added or removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_SECONDARY_DOES_NOT_MATCH_PRIMARY - The remote-copy
            group is in the failover state. Both systems are in the primary
            state.
        """
        if not useHttpPost:
            parameters = {'action': 1,
                          'volumeName': volumeName,
                          'targets': targets}
            if optional:
                parameters = self._mergeDict(parameters, optional)

            response, body = self.http.put('/remotecopygroups/%s' % name,
                                           body=parameters)
        else:
            parameters = {'volumeName': volumeName,
                          'targets': targets}
            if optional:
                parameters = self._mergeDict(parameters, optional)
            response, body = self.http.post(
                '/remotecopygroups/%s/volumes' %
                name, body=parameters
            )
        return body

    def removeVolumeFromRemoteCopyGroup(self, name, volumeName,
                                        optional=None,
                                        removeFromTarget=False,
                                        useHttpDelete=True):
        """
        Removes a volume from a remote copy group

        :param name: Name of the remote copy group
        :type name: string
        :param volumeName: Specifies the name of the existing virtual
                           volume to be removed from an existing remote-copy
                           group.
        :type volumeName: string
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
                "keepSnap": False  # If true, the resynchronization
                                   # snapshot of the local volume is
                                   # retained.
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - volume doesn't exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_IS_NOT_READY - The remote-copy configuration is not ready
            for commands.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_BUSY - The remote-copy group is currently busy;
            retry later.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - RCOPY_GROUP_VOL_NOT_IN_GROUP - The volume is not in the
            remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_RENAME_RESYNC_SNAPSHOT_FAILED - Renaming of the
            remote-copy group resynchronization snapshot failed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - RCOPY_GROUP_CREATED_MIRROR_CONFIG_OFF - The remote-copy group was
            created when the configuration mirroring policy was turned off on
            the target. However, this policy is now turned on. In order to
            dismiss a volume from the remote-copy group, the configuration
            mirroring policy must be turned off. Retry after turning the
            policy off.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation should
            be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_TARGET_IS_NOT_READY - The remote-copy group target is
            not ready.
        """
        # Now this feature is supported in the WSAPI.
        if not useHttpDelete:
            # Retaining this code (ssh) for backward compatibility only.
            if removeFromTarget:
                if optional:
                    keep_snap = optional.get('keepSnap', False)
                else:
                    keep_snap = False

                if keep_snap:
                    cmd = ['dismissrcopyvv', '-f', '-keepsnap', '-removevv',
                           volumeName, name]
                else:
                    cmd = ['dismissrcopyvv', '-f', '-removevv', volumeName,
                           name]
                self._run(cmd)
            else:
                parameters = {'action': 2,
                              'volumeName': volumeName}
                if optional:
                    parameters = self._mergeDict(parameters, optional)

                response, body = self.http.put('/remotecopygroups/%s' % name,
                                               body=parameters)
                return body
        else:
            option = None
            if optional and optional.get('keepSnap') and removeFromTarget:
                raise Exception("keepSnap and removeFromTarget cannot be both\
                    true while removing the volume from remote copy group")
            elif optional and optional.get('keepSnap'):
                option = 'keepSnap'
            elif removeFromTarget:
                option = 'removeSecondaryVolume'
            delete_url = '/remotecopygroups/%s/volumes/%s' % (name, volumeName)
            if option:
                delete_url += '?%s=true' % option
            response, body = self.http.delete(delete_url)
            return body

    def startRemoteCopy(self, name, optional=None):
        """
        Starts a remote copy

        :param name: Name of the remote copy group
        :type name: string
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            # All the volumes in the group must be specified. While specifying
            # the pair, the starting snapshot is optional. If it is not
            # specified, a full resynchronization of the volume is performed.
            startingSnapshots = [
                {
                    "volumeName": "vol_name",    # Volume name
                    "snapshotName": "snap_name"  # Snapshot name
                }
            ]

            optional = {
                "skipInitialSync": False,    # If True, the volume
                                             # should skip the initial
                                             # synchronization and
                                             # sets the volumes to
                                             # a synchronized state.
                "targetName": "target_name", # The target name associated
                                             # with this group.
                "startingSnapshots": startingSnapshots
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_EMPTY - The remote-copy group must contain volumes
            before being started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation
            should be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_TARGET_NOT_SPECIFIED - A target must be specified to
            complete this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_NOT_ALL_VOLUMES_SPECIFIED - All the volumes in the
            remote-copy group must be specified to complete this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - RCOPY_GROUP_EXISTENT_VOL_WWN_ON_TARGET - Secondary volume WWN
            already exists on the target.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - RCOPY_GROUP_VOLUME_ALREADY_SYNCED - Volume is already
            synchronized.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_INCORRECT_SNAPSHOT_OR_VOLUME_SPECIFIED - An incorrect
            starting snapshot or volume was specified, or the snapshot or
            volume does not exist.
        """
        parameters = {'action': 3}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.put('/remotecopygroups/%s' % name,
                                       body=parameters)
        return body

    def stopRemoteCopy(self, name, optional=None):
        """
        Stops a remote copy

        :param name: Name of the remote copy group
        :type name: string
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
                "noSnapshot": False,        # If true, this option turns
                                            # off creation of snapshots
                                            # in synchronous and
                                            # periodic modes, and
                                            # deletes the current
                                            # synchronization snapshots.
                "targetName": "target_name" # The target name associated
                                            # with this group
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_TARGET_IS_NOT_READY - The remote-copy group target is not
            ready.
        """
        parameters = {'action': 4}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.put('/remotecopygroups/%s' % name,
                                       body=parameters)
        return body

    def synchronizeRemoteCopyGroup(self, name, optional=None):
        """
        Synchronizing a remote copy group

        :param name: Name of the remote copy group
        :type name: string
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
                "noResyncSnapshot": False,   # If true, does not save
                                             # the resynchronization
                                             # snapshot. Applicable
                                             # only to remote-copy
                                             # groups in asychronous
                                             # periodic mode.
                "targetName": "target_name", # The target name
                                             # assoicated with the
                                             # remote-copy group.
                "fullSync": False            # If true, this option
                                             # forces a full
                                             # synchronization of the
                                             # remote-copy group, even
                                             # if the volumes are
                                             # already synchronized.
                                             # This option, which
                                             # applies only to volume
                                             # groups in synchronous
                                             # mode, can be used to
                                             # resynchronize volumes
                                             # that have become
                                             # inconsistent.
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - The operation
            should be performed only on the primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - UNLICENSED_FEATURE - The system is not licensed for this feature.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_TARGET - The specified target is not a target of
            the remote-copy group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_TARGET_IS_NOT_READY - The remote-copy group target is not
            ready.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INVOLVED_IN_SYNCHRONIZATION - The remote-copy group
            is already involved in synchronization.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - The remote-copy group has already been
            started.
        """
        parameters = {'action': 5}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.put('/remotecopygroups/%s' % name,
                                       body=parameters)
        return body

    def recoverRemoteCopyGroupFromDisaster(self, name, action, optional=None):
        """
        Recovers a remote copy group from a disaster

        :param name: Name of the remote copy group
        :type name: string
        :param action: Specifies the action to be taken on the specified group.
                       The action may be any of values 6 through 11:
                       * RC_ACTION_CHANGE_DIRECTION - Changes the current
                       direction of the remote-copy groups.
                       * RC_ACTION_CHANGE_TO_PRIMARY - Changes the secondary
                       groups to primary groups on the active system.
                       * RC_ACTION_MIGRATE_GROUP - Migrates the remote-copy
                       group from the primary system to the secondary system
                       without impacting I/O.
                       * RC_ACTION_CHANGE_TO_SECONDARY - Changes the primary
                       remote-copy group on the backup system to the
                       secondary remote-copy group.
                       * RC_ACTION_CHANGE_TO_NATURUAL_DIRECTION - Changes all
                       remote-copy groups to their natural direction and
                       starts them.
                       * RC_ACTION_OVERRIDE_FAIL_SAFE - Overrides the failsafe
                       state that is applied to the remote-copy group.
        :type action: int
        :param optional: dict of other optional items
        :type optional: dict

        .. code-block:: python

            optional = {
                "targetName": "target_name",  # The target name
                                              # associated with this
                                              # group.
                "skipStart": False,           # If true, groups are not
                                              # started after role reversal
                                              # is completed. Valid for
                                              # only FAILOVER, RECOVER,
                                              # and RESTORE operations.
                "skipSync": False,            # If true, the groups are
                                              # not synchronized after
                                              # role reversal is
                                              # completed. Valid only for
                                              # FAILOVER, RECOVER, and
                                              # RESTORE operations.
                "discardNewData": False,      # If true and the group
                                              # has multiple targets,
                                              # don't check other targets
                                              # of the group to see if
                                              # newer data should be
                                              # pushed from them.
                                              # Valid only for FAILOVER
                                              # operation.
                "skipPromote": False,         # If true, the snapshots of
                                              # the groups that are
                                              # switched from secondary
                                              # to primary are not
                                              # promoted to the base
                                              # volume. Valid only for
                                              # FAILOVER and REVERSE
                                              # operations.
                "noSnapshot": False,          # If true, the snapshots
                                              # are not taken of the
                                              # groups that are switched
                                              # from secondary to
                                              # primary. Valid for
                                              # FAILOVER, REVERSE, and
                                              # RESTORE operations.
                "stopGroups": False,          # If true, the groups are
                                              # stopped before performing
                                              # the reverse operation.
                                              # Valid only for REVERSE
                                              # operation.
                "localGroupsDirection": False # If true, the group's
                                              # direction is changed only
                                              # on the system where the
                                              # operation is run. Valid
                                              # only for REVERSE operation
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_RCOPY_GROUP - The remote-copy group does not exist.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - UNLICENSED_FEATURE - System is not licensed for this feature.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - RCOPY_GROUP_INV_TARGET - Specified target is not in remote copy
            group.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_MISSING_REQUIRED - Group has multiple targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_RCOPY_GROUP_ROLE_CONFLICT - Group is not in correct
            role for this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_INV_OPERATION_ON_MULTIPLE_TARGETS - The operation is
            not supported on multiple targets.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_NOT_STOPPED - Remote copy group is not stopped.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_RCOPY_GROUP_ROLE_CONFLICT - Group is not in correct
            role for this operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_NOT_STARTED - Remote copy not started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_PARAM_CONFLICT - Parameters cannot be present at the
            same time.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Volume promotion is
            in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_IS_BUSY - Remote copy group is currently busy.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_STARTED - Remote copy group has already been started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_EMPTY - Remote copy group does not contain any
            volumes.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_PRIMARY_SIDE - Operation should
            only be issued on primary side.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - RCOPY_GROUP_OPERATION_ONLY_ON_SECONDARY_SIDE - Operation should
            only be issued on secondary side.
        """
        parameters = {'action': action}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        response, body = self.http.post('/remotecopygroups/%s' % name,
                                        body=parameters)
        return body

    def toggleRemoteCopyConfigMirror(self, target, mirror_config=True):
        """
        Used to toggle config mirroring policies on a target device.

        :param target: The 3PAR target name to enable/disable config mirroring.
        :type target: string
        :param mirror_config: Specifies whether to enable or disable config
                              mirroring.
        :type mirror_config: bool
        """

        obj = {'mirrorConfig': mirror_config}
        info = {'policies': obj}
        try:
            self.http.put('/remotecopytargets/%s' % target, body=info)
        except exceptions.HTTPBadRequest as ex:
            pass

    def getVolumeSnapshots(self, name, live_test=True):
        """
        Shows all snapshots associated with a given volume.

        :param name: The volume name
        :type name: str

        :returns: List of snapshot names
        """

        uri = '/volumes?query="copyOf EQ %s"' % (name)
        response, body = self.http.get(uri)

        if live_test:
            snapshots = []
            for volume in body['members']:
                if 'copyOf' in volume:
                    if (volume['copyOf'] == name and
                            volume['copyType'] == self.VIRTUAL_COPY):
                        snapshots.append(volume['name'])

            return snapshots
        else:
            snapshots = []
            for volume in body['members']:
                if re.match('SNAP', volume['name']):
                    snapshots.append(volume['name'])

            return snapshots

    def _mergeDict(self, dict1, dict2):
        """
        Safely merge 2 dictionaries together

        :param dict1: The first dictionary
        :type dict1: dict
        :param dict2: The second dictionary
        :type dict2: dict

        :returns: dict

        :raises Exception: dict1, dict2 is not a dictionary
        """
        if type(dict1) is not dict:
            raise Exception("dict1 is not a dictionary")
        if type(dict2) is not dict:
            raise Exception("dict2 is not a dictionary")

        dict3 = dict1.copy()
        dict3.update(dict2)
        return dict3

    def _get_next_word(self, s, search_string):
        """Return the next word.

        Search 's' for 'search_string', if found return the word preceding
        'search_string' from 's'.
        """
        word = re.search(search_string.strip(' ') + ' ([^ ]*)', s)
        return word.groups()[0].strip(' ')

    def getCPGStatData(self, name, interval='daily', history='7d'):
        """
        Requests CPG performance data at a sampling rate (interval) for a
        given length of time to sample (history)

        :param name: a valid CPG name
        :type name: str
        :param interval: hourly, or daily
        :type interval: str
        :param history: xm for x minutes, xh for x hours, or xd for x days
                        (e.g. 30m, 1.5h, 7d)
        :type history: str

        :returns: dict

        :raises: :class:`~hpe3parclient.exceptions.SrstatldException`
            - srstatld gives invalid output
        """
        if interval not in ['daily', 'hourly']:
            raise exceptions.ClientException("Input interval not valid")
        if not re.compile("(\d*\.\d+|\d+)[mhd]").match(history):
            raise exceptions.ClientException("Input history not valid")
        cmd = ['srstatld', '-cpg', name, '-' + interval, '-btsecs',
               '-' + history]
        output = self._run(cmd)
        if not isinstance(output, list):
            raise exceptions.SrstatldException("srstatld output not a list")
        elif len(output) < 4:
            raise exceptions.SrstatldException("srstatld output list too "
                                               "short")
        elif len(output[-1].split(',')) < 16:
            raise exceptions.SrstatldException("srstatld output last line "
                                               "invalid")
        else:
            return self._format_srstatld_output(output)

    def _format_srstatld_output(self, out):
        """
        Formats the output of the 3PAR CLI command srstatld
        Takes the total read/write value when possible

        :param out: the output of srstatld
        :type out: list

        :returns: dict
        """
        line = out[-1].split(',')
        formatted = {
            'throughput': float(line[4]),
            'bandwidth': float(line[7]),
            'latency': float(line[10]),
            'io_size': float(line[13]),
            'queue_length': float(line[14]),
            'avg_busy_perc': float(line[15])
        }
        return formatted

    def getSnapshotsOfVolume(self, snapcpgName, volName):
        """Gets list of snapshots of a volume.

        :param snapcpgName: The name of the CPG in which the volume
                        snapshot(s) are present
        :type snapcpgName: str
        :param volName: The volume name for which the list of
                        snapshots needs to be retrieved
        :type volName: str

        :returns: list of snapshots of volName

        """
        uri = '/volumes?query="snapCPG EQ %s"' % (snapcpgName)
        response, body = self.http.get(uri)
        snapshots = []
        for volume in body['members']:
            if 'copyOf' in volume:
                if (volume['copyOf'] == volName and
                        volume['copyType'] == self.VIRTUAL_COPY):
                    snapshots.append(volume['name'])
        return snapshots

    def getFlashCache(self):
        """Get information about flash cache on the 3Par array.
        :returns: list of Hosts
        """
        response, body = self.http.get('/flashcache')
        return body

    def createFlashCache(self, sizeInGib, mode):
        """Creates a new FlashCache

        :param sizeInGib: Specifies the node pair size of the Flash Cache on
                          the system.
        :type: int
        :param: mode    : Simulator: 1
                          Real: 2 (default)
        :type: int
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not enough space is available for the operation.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - A JSON input object contains a
            name-value pair with a numeric value that exceeds the expected
            range. Flash Cache exceeds the expected range. The HTTP ref
            member contains the name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
           - EXISTENT_FLASH_CACHE - The Flash Cache already exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - FLASH_CACHE_NOT_SUPPORTED - Flash Cache is not supported.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_FLASH_CACHE_SIZE - Invalid Flash Cache size. The size
            must be a multiple of 16 G.
        """
        flash_cache = {'sizeGiB': sizeInGib}

        if mode is not None:
            mode = {'mode': mode}
            flash_cache = self._mergeDict(flash_cache, mode)

        info = {'flashCache': flash_cache}
        response, body = self.http.post('/', body=info)
        return body

    def deleteFlashCache(self):
        """Deletes an existing Flash Cache
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - FLASH_CACHE_IS_BEING_REMOVED - Unable to delete the
            Flash Cache, the Flash Cache is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - FLASH_CACHE_NOT_SUPPORTED - Flash Cache is not supported
            on this system.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
           - NON_EXISTENT_FLASH_CACHE - The Flash Cache does not exist.
        """
        self.http.delete('/flashcache')

    def resyncPhysicalCopy(self, volume_name):
        """Resynchronizes a physical copy.
        :param name - The name of the volume
        :type - string
        """
        info = {'action': self.RESYNC_PHYSICAL_COPY}
        response = self.http.put("/volumes/%s" % (volume_name), body=info)
        return response[1]

    def admitRemoteCopyLinks(
            self, targetName, source_port, target_port_wwn_or_ip):
        """Adding remote copy link from soure to target.
        :param targetName - The name of target system
        :type - string
        :source_port - Source ethernet/Fibre channel port
        :type- string
        :target_port_wwn_or_ip- Target system's peer port WWN/IP
        :type- string
        """
        source_target_port_pair = source_port + ':' + target_port_wwn_or_ip

        cmd = ['admitrcopylink', targetName, source_target_port_pair]
        response = self._run(cmd)
        if response != []:
            raise exceptions.SSHException(response)
        return response

    def dismissRemoteCopyLinks(
            self, targetName, source_port, target_port_wwn_or_ip):
        """Dismiss remote copy link from soure to target.
        :param targetName - The name of target system
        :type - string
        :source_port - Source ethernet/Fibre channel port
        :type- string
        :target_port_wwn_or_ip- Target system's peer port WWN/IP
        :type- string
        """
        source_target_port_pair = source_port + ':' + target_port_wwn_or_ip

        cmd = ['dismissrcopylink', targetName, source_target_port_pair]
        response = self._run(cmd)
        if response != []:
            raise exceptions.SSHException(response)
        return response

    def startrCopy(self):
        """Starting remote copy service
        :param No
        """
        cmd = ['startrcopy']
        response = self._run(cmd)
        if response != []:
            raise exceptions.SSHException(response)
        return response

    def rcopyServiceExists(self):
        """Checking remote copy service status.
        :returns: True if remote copy service status is 'Started'
        :         False if remote copy service status is 'Stopped'
        """
        cmd = ['showrcopy']
        response = self._run(cmd)
        rcopyservice_status = False
        if 'Started' in response[2]:
            rcopyservice_status = True
        return rcopyservice_status

    def getRemoteCopyLink(self, link_name):
        """
        Querying specific remote copy link
        :returns: Specific remote copy link info
        """
        response, body = self.http.get('/remotecopylinks/%s' % link_name)
        return body

    def rcopyLinkExists(self, targetName, local_port, target_system_peer_port):
        """Checking remote copy link from soure to target.
        :param targetName - The name of target system
        :type - string
        :source_port - Source ethernet/Fibre channel port
        :type- string
        :target_port_wwn_or_ip- Target system's peer port WWN/IP
        :type- string
        :returns: True if remote copy link exists
        :         False if remote copy link doesn't exist
        """
        cmd = ['showrcopy', 'links']
        response = self._run(cmd)
        for item in response:
            if item.startswith(targetName):
                link_info = item.split(',')
                if link_info[0] == targetName and \
                        link_info[1] == local_port and \
                        link_info[2] == target_system_peer_port:
                    return True
        return False

    def admitRemoteCopyTarget(self, targetName, mode, remote_copy_group_name,
                              optional=None):
        """Adding target to remote copy group
        :param targetName - The name of target system
        :type - string
        :mode - synchronization mode
        :type - string
        :remote_copy_group_name
        :type - string
        :optional
        :type - dict

        .. code-block:: python

            optional = {
                "volumePairs": [{
                    "sourceVolumeName": "source_name",  # The target volume
                                                        # name associated with
                                                        # this group.
                    "targetVolumeName": "target_name"   # The target volume
                                                        # name associated with
                                                        # this group.
                }]
            }
        """

        cmd = ['admitrcopytarget', targetName,
               mode, remote_copy_group_name]
        if optional:
            volumePairs = optional.get('volumePairs')
            if volumePairs is not None:
                for volumePair in volumePairs:
                    source_target_pair = \
                        volumePair['sourceVolumeName'] + ':' + \
                        volumePair['targetVolumeName']
                    cmd.append(source_target_pair)
        response = self._run(cmd)
        err_resp = self.check_response_for_admittarget(response, targetName)
        if err_resp:
            err = (("Admit remote copy target failed Error is\
 '%(err_resp)s' ") % {'err_resp': err_resp})
            raise exceptions.SSHException(err)
        return response

    def dismissRemoteCopyTarget(self, targetName, remote_copy_group_name):
        """Removing target from remote copy group
        :param targetName - The name of target system
        :type - string
        :remote_copy_group_name
        :type - string
        """
        option = '-f'
        cmd = ['dismissrcopytarget', option, targetName,
               remote_copy_group_name]

        response = self._run(cmd)
        for message in response:
            if "has been dismissed from group" in message:
                return response
        raise exceptions.SSHException(response)

    def targetInRemoteCopyGroupExists(
            self, target_name, remote_copy_group_name):
        """Determines whether target is present in remote copy group.
         :param name: target_name
        :type name: str
        :remote_copy_group_name
        :type key: str
         :returns: bool
         """
        try:
            contents = self.getRemoteCopyGroup(remote_copy_group_name)
            for item in contents['targets']:
                if item['target'] == target_name:
                    return True
        except Exception:
            pass
        return False

    def remoteCopyGroupStatusCheck(
            self, remote_copy_group_name):
        """
        Determines whether all volumes syncStatus is synced or not
        when remote copy group status is started. If all volumes
        syncStatus is 'synced' then it will return true else false
        :param remote_copy_group_name - Remote copy group name
        :type remote_copy_group_name: str
        :return: True: If remote copy group is started and all
        :              volume syncStatus is 'synced' i.e. 3
        :        False: If remote copy group is started and some
        :              volume status is not 'synced'.
        """
        response = self.getRemoteCopyGroup(remote_copy_group_name)
        for target in response['targets']:
            if target['state'] != 3:
                return False
        for volume in response['volumes']:
            for each_target_volume in volume['remoteVolumes']:
                if each_target_volume['syncStatus'] != 3:
                    return False
        return True

    def check_response_for_admittarget(self, resp, targetName):
        """
        Checks whether command response having valid output
        or not if output is invalid then return that response.
        """
        for r in resp:
            if 'error' in str.lower(r) or 'invalid' in str.lower(r) \
                    or 'must specify a mapping' in str.lower(r) \
                    or 'not exist' in str.lower(r) \
                    or 'no target' in str.lower(r) \
                    or 'group contains' in str.lower(r) \
                    or 'Target is already in this group.' in str(r) \
                    or 'could not locate an indicated volume.' in str(r) \
                    or 'Target system %s could not be contacted' % targetName \
                    in str(r) \
                    or 'Target %s could not get info on secondary target' \
                    % targetName in str(r) \
                    or 'Target %s is not up and ready' % targetName in str(r) \
                    or 'A group may have only a single synchronous target.' \
                    in str(r) or \
                    'cannot have groups with more than one ' \
                    'synchronization mode' \
                    in str.lower(r):
                return r

    def check_response(self, resp):
        for r in resp:
            if 'error' in str.lower(r) or 'invalid' in str.lower(r):
                err_resp = r.strip()
                return err_resp

    def createSchedule(self, schedule_name, task, taskfreq):
        """Create Schedule for volume snapshot.
        :param schedule_name - The name of the schedule
        :type - string
        :param task - command to for which schedule is created
        :type - string
        :param taskfreq - frequency of schedule
        :type - string
        """
        cmd = ['createsched']
        cmd.append("\"" + task + "\"")
        if '@' not in taskfreq:
            cmd.append("\"" + taskfreq + "\"")
        else:
            cmd.append(taskfreq)
        cmd.append(schedule_name)
        try:
            resp = self._run(cmd)

            err_resp = self.check_response(resp)
            if err_resp:
                raise exceptions.SSHException(err_resp)
            else:
                for r in resp:
                    if str.lower('The schedule format is <minute> <hour> <dom>\
 <month> <dow> or by @hourly @daily @monthly @weekly @monthly \
@yearly') in str.lower(r):
                        raise exceptions.SSHException(r.strip())
        except exceptions.SSHException as ex:
            raise exceptions.SSHException(ex)

    def deleteSchedule(self, schedule_name):
        """Delete Schedule
        :param schedule_name - The name of the schedule to delete
        :type - string
        """
        cmd = ['removesched', '-f', schedule_name]
        try:
            resp = self._run(cmd)

            err_resp = self.check_response(resp)
            if err_resp:
                err = (("Delete snapschedule failed Error is\
 '%(err_resp)s' ") % {'err_resp': err_resp})
                raise exceptions.SSHException(reason=err)
        except exceptions.SSHException as ex:
            raise exceptions.SSHException(reason=ex)

    def getSchedule(self, schedule_name):
        """Get Schedule
        :param schedule_name - The name of the schedule to get information
        :type - string
        """
        cmd = ['showsched ', schedule_name]
        try:
            result = self._run(cmd)
            for r in result:
                if 'No scheduled tasks ' in r:
                    msg = "Couldn't find the schedule '%s'" % schedule_name
                    raise exceptions.SSHNotFoundException(msg)
        except exceptions.SSHNotFoundException as ex:
            raise exceptions.SSHNotFoundException(ex)
        return result

    def modifySchedule(self, name, schedule_opt):
        """Modify Schedule.
        :param name - The name of the schedule
        :type - string
        :param schedule_opt -
        :type schedule_opt - dictionary of option to be modified
        .. code-block:: python
            mod_request = {
                'newName': 'myNewName',         # New name of the schedule
                'taskFrequency': '0 * * * *'    # String containing cron or
                                                # @monthly, @hourly, @daily,
                                                # @yearly and @weekly.
        }
        """

        cmd = ['setsched']
        if 'newName' in schedule_opt:
            cmd.append('-name')
            cmd.append(schedule_opt['newName'])

        if 'taskFrequency' in schedule_opt:
            cmd.append('-s')
            if '@' not in schedule_opt['taskFrequency']:
                cmd.append("\"" + schedule_opt['taskFrequency'] + "\"")
            else:
                cmd.append(schedule_opt['taskFrequency'])
        cmd.append(name)
        try:
            resp = self._run(cmd)

            err_resp = self.check_response(resp)
            if err_resp:
                raise exceptions.SSHException(err_resp)
            else:
                for r in resp:
                    if str.lower('The schedule format is <minute> <hour> \
<dom> <month> <dow> or by @hourly @daily @monthly @weekly @monthly \
@yearly') in str.lower(r):
                        raise exceptions.SSHException(r.strip())

        except exceptions.SSHException as ex:
            raise exceptions.SSHException(ex)

    def suspendSchedule(self, schedule_name):
        """Suspend Schedule
        :param schedule_name - The name of the schedule to get information
        :type - string
        """
        cmd = ['setsched', '-suspend', schedule_name]
        try:
            resp = self._run(cmd)
            err_resp = self.check_response(resp)
            if err_resp:
                err = (("Schedule suspend failed Error is\
 '%(err_resp)s' ") % {'err_resp': err_resp})
                raise exceptions.SSHException(reason=err)
        except exceptions.SSHException as ex:
            raise exceptions.SSHException(reason=ex)

    def resumeSchedule(self, schedule_name):
        """Resume Schedule
        :param schedule_name - The name of the schedule to get information
        :type - string
        """
        cmd = ['setsched', '-resume', schedule_name]
        try:
            resp = self._run(cmd)
            err_resp = self.check_response(resp)
            if err_resp:
                err = (("Schedule resume failed Error is\
 '%(err_resp)s' ") % {'err_resp': err_resp})
                raise exceptions.SSHException(reason=err)
        except exceptions.SSHException as ex:
            raise exceptions.SSHException(reason=ex)

    def remoteCopyGroupStatusStartedCheck(
            self, remote_copy_group_name):
        """
        Checks whether remote copy group status is started or not
        :param remote_copy_group_name - Remote copy group name
        :type remote_copy_group_name: str
        :return: True: If remote copy group is in started
        :              state i.e. 3
        :        False: If remote copy group is not in started
        :              state
        """
        response = self.getRemoteCopyGroup(remote_copy_group_name)
        status_started_counter = 0
        for target in response['targets']:
            if target['state'] == 3:
                status_started_counter += 1

        if status_started_counter == len(response['targets']):
            return True
        else:
            return False

    def remoteCopyGroupStatusStoppedCheck(
            self, remote_copy_group_name):
        """
        Checks whether remote copy group status is stopped or not
        :param remote_copy_group_name - Remote copy group name
        :type remote_copy_group_name: str
        :return: True: If remote copy group is in stopped
        :              state i.e. 5
        :        False: If remote copy group is not in started
        :              state
        """
        response = self.getRemoteCopyGroup(remote_copy_group_name)
        status_stopped_counter = 0
        for target in response['targets']:
            if target['state'] == 5:
                status_stopped_counter += 1

        if status_stopped_counter == len(response['targets']):
            return True
        else:
            return False

    def getScheduleStatus(self, schedule_name):
        """
        Checks schedule status active/suspended and returns it.
        :param schedule_name - Schedule name
        :type schedule_name: str
        :return: active/suspended
        """
        result = self.getSchedule(schedule_name)
        for r in result:
            if 'suspended' in r:
                return 'suspended'
            elif 'active' in r:
                return 'active'
        msg = "Couldn't find the schedule '%s' status" % schedule_name
        raise exceptions.SSHException(reason=msg)

    @staticmethod
    def convert_cli_output_to_wsapi_format(cli_output):
        """Convert CLI output into a response that looks the WS-API would.

        Use the first line as coma-separated headers.
        Build dictionaries for the remaining lines using the headers as keys.
        Return a dictionary with total and members (the dictionaries).

        If there isn't enough data for headers and data then
        total is 0 and members is an empty list.

        If you need more validity checking, you might want to do it before this
        generic routine.  It does minimal checking.

        :param cli_output: The result from the CLI (i.e. from ssh.run(cmd)).
                           The first row is headers. Following rows are data.
        :type cli_output: list

        .. code-block:: python

            # Example 1: Typical CLI output with header row and data rows.
            cli_output =
                [
                    'InstallTime,Id,Package,Version',
                    '2013-08-21 18:06:45 PDT,MU2,Complete,3.1.2.422',
                    '2013-10-10 15:20:05 PDT,MU3,Complete,3.1.2.484',
                    '2014-01-30 11:34:20 PST,DEVEL,Complete,3.1.3.170',
                    '2014-03-26 13:59:42 PDT,GA,Complete,3.1.3.202',
                    '2014-06-06 14:46:56 PDT,MU1,Complete,3.1.3.230'
                ]

            # Example 2: Example CLI output for an empty result.
            cli_output = ['No patch is applied to the system.']

        :returns: dict with total and members. members is list of dicts using
                  header for keys and data for values.
        :rtype: dict

        .. code-block:: python

            # Example 1: Converted to total and members list of dictionaries.
            ret = {
                'total': 5,
                'members': [
                    {
                        'Package': 'Complete',
                        'Version': '3.1.2.422',
                        'InstallTime': '2013-08-21 18:06:45 PDT',
                        'Id': 'MU2'
                    },
                    {
                        'Package': 'Complete',
                        'Version': '3.1.2.484',
                        'InstallTime': '2013-10-10 15:20:05 PDT',
                        'Id': 'MU3'
                    },
                    {
                        'Package': 'Complete',
                        'Version': '3.1.3.170',
                        'InstallTime': '2014-01-30 11:34:20 PST',
                        'Id': 'DEVEL'
                    },
                    {
                        'Package': 'Complete',
                        'Version': '3.1.3.202',
                        'InstallTime': '2014-03-26 13:59:42 PDT',
                        'Id': 'GA'
                    },
                    {
                        'Package': 'Complete',
                        'Version': '3.1.3.230',
                        'InstallTime': '2014-06-06 14:46:56 PDT',
                        'Id': 'MU1'
                    }
                ]
            }

            # Example 2: No data rows, so zero members.
            ret = {'total': 0, 'members': []}

        """

        members = []
        if cli_output and len(cli_output) >= 2:
            for index, line in enumerate(cli_output):
                if index == 0:
                    headers = line.split(',')
                else:
                    split = line.split(',')
                    member = {}
                    for i, header in enumerate(headers):
                        try:
                            member[header] = split[i]
                        except IndexError:
                            member[header] = None
                    members.append(member)

        return {'total': len(members), 'members': members}

    @staticmethod
    def _getSshClient(ip, login, password, port=22,
                      conn_timeout=None, privatekey=None,
                      **kwargs):
        ssh_client = ssh.HPE3PARSSHClient(ip, login, password, port,
                                          conn_timeout, privatekey,
                                          **kwargs)
        return ssh_client

    @staticmethod
    def getPortNumber(ip, login, password, port=22,
                      conn_timeout=None, privatekey=None,
                      **kwargs):
        """Get port number from showwsapi output

        :param 3PAR credentials
        :return: HTTPS_Port column value
        """
        try:
            ssh_client = HPE3ParClient._getSshClient(ip, login, password, port,
                                                     conn_timeout, privatekey,
                                                     **kwargs)
            if ssh_client is None:
                raise exceptions.SSHException("SSH is not initialized.\
 Initialize it by calling 'setSSHOptions'.")
            ssh_client.open()
            cli_output = ssh_client.run(['showwsapi'])
            wsapi_dict = HPE3ParClient.convert_cli_output_to_wsapi_format(
                cli_output)
            return wsapi_dict['members'][0]['HTTPS_Port']
        finally:
            if ssh_client:
                ssh_client.close()

    def tuneVolume(self, volName, tune_operation, optional=None):
        """Tune a volume.

        :param name: the name of the volume
        :type name: str
        :param name: tune_operation 1 for USR_CPG 2 for SNP_CPG
        :type name: int
        :param optional: dictionary of volume attributes to change
        :type optional: dict
        .. code-block:: python

            optional = {
             'action': 6,                  # For tuneVolume operation
             'userCPG': 'User CPG name',   # Required if tuneOperation is 1
             'snapCPG': 'Snap CPG name',   # Required if tuneOperation is 2
             'conversionOperation': 1,     # For TPVV 1, For FPVV 2, For TDVV
                                           # 3, for CONVERT_TO_DECO 4
             'compression': False,         # compression is not supported for
                                           # FPVV
            }

        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN_SAME_DOMAIN - Snap CPG is not in the same domain as
            the user CPG.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_VV_IS_FPVV - The volume is already fully provisioned.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_VV_IS_TDVV - The volume is already deduplicated.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_VV_IS_TPVV - The volume is already thinly provisioned.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_UNSUPPORTED_VV_TYPE - Invalid operation: Cannot
            grow this type of volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_MODIFY_USR_CPG_TDVV - Cannot change USR CPG of
            a TDVV to a different CPG..
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NON_BASE_VOLUME - The destination volume
            is not a base volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The volume is a system volume. This
            operation is not allowed on a system volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is
            in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Cannot modify an internal
            volume
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV
            conversion is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - Cannot modify a peer volume.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_TASK_CANCEL_IN_PROGRESS - Invalid operation:
            A task involving the volume is being canceled..
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Invalid operation: Volume
            promotion is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_TUNE_IN_PROGRESS - Invalid operation: Volume
            tuning is in progress.
        :raises: :class:`~hpe3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not Enough space is available
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - NODE_DOWN - The node is down.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hpe3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - volume doesn't exist
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NEEDS_TO_BE_CHECKED - The volume needs to be checked.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started.
        :raises: :class:`~hpe3parclient.exceptions.HTTPForbidden`
            - INV_INPUT_VV_IS_FPVV - A fully provisioned volume cannot be
            compressed.

        """
        info = {'action': self.TUNE_VOLUME, 'tuneOperation': tune_operation}
        if optional is not None and not self.compression_supported:
            if 'compression' in optional.keys() \
                    and optional.get('compression') is False:
                del optional['compression']
        if optional:
            if self.primera_supported:
                if optional.get('compression') is True:
                    if optional.get('conversionOperation') == self.TDVV:
                        optional['conversionOperation'] = self.CONVERT_TO_DECO
                        optional.pop('compression')
                    else:
                        raise exceptions.HTTPBadRequest("invalid input: On\
 primera array, with 'compression' set to true 'tdvv' must be true")
                else:
                    if optional.get('conversionOperation') == self.TDVV:
                        raise exceptions.HTTPBadRequest("invalid input: On\
 primera array, for compression and deduplicated volume 'tdvv' should be true\
 and 'compression' must be specified as true")
                    elif optional.get('conversionOperation') == self.TPVV:
                        if 'compression' in optional.keys():
                            optional.pop('compression')
                    elif optional.get('conversionOperation') ==\
                            self.CONVERT_TO_DECO:
                        if 'compression' in optional.keys():
                            optional.pop('compression')
                    elif optional.get('conversionOperation') == self.FPVV:
                        raise exceptions.HTTPBadRequest("invalid input:\
 On primera array 'fpvv' is not supported")
            info = self._mergeDict(info, optional)
        response, body = self.http.put(
            '/volumes/%s' % volName, body=info)
        return body

    def _cancelTask(self, taskId):
        info = {'action': 1}
        try:
            self.http.put('/tasks/%s' % taskId, body=info)
        except exceptions.HTTPBadRequest as ex:
            # it means task cannot be cancelled,
            # because it is 'done' or already 'cancelled'
            pass

    # =================
    # ENHANCED UTILITY FUNCTIONS MOVED FROM hpe_3par_common.py
    # =================

    @staticmethod
    def encode_name(name):
        """Encode a name using base64 and UUID for 3PAR compatibility.
        
        Converts names to a format that 3PAR accepts by:
        - Converting to UUID bytes
        - Base64 encoding
        - Replacing problematic characters (+, /, =)
        
        Args:
            name (str): The name to encode
            
        Returns:
            str: The encoded name suitable for 3PAR
        """
        # Import here to avoid circular imports
        import uuid
        import math
        import json
        import time
        from oslo_serialization import base64
        
        uuid_str = name.replace("-", "")
        vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
        vol_encoded = base64.encode_as_text(vol_uuid.bytes)

        # 3par doesn't allow +, nor /
        vol_encoded = vol_encoded.replace('+', '.')
        vol_encoded = vol_encoded.replace('/', '-')
        # strip off the == as 3par doesn't like those.
        vol_encoded = vol_encoded.replace('=', '')
        return vol_encoded

    @classmethod
    def get_3par_vol_name(cls, volume_id, temp_vol=False):
        """Get converted 3PAR volume name.

        Converts the openstack volume id from
        ecffc30f-98cb-4cf5-85ee-d7309cc17cd2
        to
        osv-7P.DD5jLTPWF7tcwnMF80g

        We convert the 128 bits of the uuid into a 24character long
        base64 encoded string to ensure we don't exceed the maximum
        allowed 31 character name limit on 3Par

        We strip the padding '=' and replace + with .
        and / with -

        volume_id is a polymorphic parameter and can be either a string or a
        volume (OVO or dict representation).
        
        Args:
            volume_id: Volume ID string or volume object
            temp_vol (bool): Whether this is a temporary volume
            
        Returns:
            str: Formatted 3PAR volume name
        """
        # Import here to avoid circular imports
        try:
            from cinder import objects
            # Accept OVOs (what we should only receive), dict (so we don't have to
            # change all our unit tests), and ORM (because we some methods still
            # pass it, such as terminate_connection).
            if isinstance(volume_id, (objects.Volume, objects.Volume.model, dict)):
                volume_id = volume_id.get('_name_id') or volume_id['id']
        except ImportError:
            # Handle case where cinder is not available
            if hasattr(volume_id, 'get'):
                volume_id = volume_id.get('_name_id') or volume_id.get('id', volume_id)
        
        volume_name = cls.encode_name(volume_id)
        if temp_vol:
            # is this a temporary volume
            # this is done during migration
            prefix = "tsv-%s"
        else:
            prefix = "osv-%s"
        return prefix % volume_name

    @classmethod
    def get_3par_snap_name(cls, snapshot_id, temp_snap=False):
        """Get converted 3PAR snapshot name.
        
        Args:
            snapshot_id (str): Snapshot ID
            temp_snap (bool): Whether this is a temporary snapshot
            
        Returns:
            str: Formatted 3PAR snapshot name
        """
        snapshot_name = cls.encode_name(snapshot_id)
        if temp_snap:
            # is this a temporary snapshot
            # this is done during cloning
            prefix = "tss-%s"
        else:
            prefix = "oss-%s"
        return prefix % snapshot_name

    @classmethod
    def get_3par_ums_name(cls, snapshot_id):
        """Get 3PAR unmanaged snapshot name.
        
        Args:
            snapshot_id (str): Snapshot ID
            
        Returns:
            str: Formatted 3PAR unmanaged snapshot name
        """
        ums_name = cls.encode_name(snapshot_id)
        return "ums-%s" % ums_name

    @classmethod
    def get_3par_vvs_name(cls, volume_id):
        """Get 3PAR volume set name.
        
        Args:
            volume_id (str): Volume ID
            
        Returns:
            str: Formatted 3PAR volume set name
        """
        vvs_name = cls.encode_name(volume_id)
        return "vvs-%s" % vvs_name

    @staticmethod
    def get_keys_by_volume_type(volume_type, hpe3par_valid_keys):
        """Extract HPE 3PAR keys from volume type extra specs.
        
        Args:
            volume_type (dict): Volume type with extra_specs
            hpe3par_valid_keys (list): List of valid HPE 3PAR keys
            
        Returns:
            dict: Filtered HPE 3PAR keys and values
        """
        hpe3par_keys = {}
        specs = volume_type.get('extra_specs')
        for key, value in specs.items():
            if ':' in key:
                fields = key.split(':')
                key = fields[1]
            if key in hpe3par_valid_keys:
                hpe3par_keys[key] = value
        return hpe3par_keys

    def get_model_update(self, volume_host, cpg, replication=False,
                        provider_location=None, hpe_tiramisu=None):
        """Get model_update dict for volume operations.
        
        Args:
            volume_host (str): Volume host string
            cpg (str): Actual CPG used
            replication (bool): Whether replication is enabled
            provider_location (str, optional): Provider location
            hpe_tiramisu (bool, optional): Tiramisu replication
            
        Returns:
            dict: Model update or None
        """
        # Import here to avoid circular imports
        from cinder.volume import volume_utils
        
        model_update = {}
        host = volume_utils.extract_host(volume_host, 'backend')
        host_and_pool = volume_utils.append_host(host, cpg)
        if volume_host != host_and_pool:
            # Since we selected a pool based on type, update the model.
            model_update['host'] = host_and_pool
        if replication:
            model_update['replication_status'] = 'enabled'
        if (replication or hpe_tiramisu) and provider_location:
            model_update['provider_location'] = provider_location
        if not model_update:
            model_update = None
        
        return model_update

    def get_existing_volume_ref_name(self, existing_ref, is_snapshot=False):
        """Extract volume/snapshot name from existing reference.
        
        Args:
            existing_ref (dict): Reference dictionary
            is_snapshot (bool): Whether this is for a snapshot
            
        Returns:
            str: Volume or snapshot name
            
        Raises:
            InvalidInput: If source-name is not provided
        """
        # Import here to avoid circular imports
        from cinder import exception
        from cinder.i18n import _
        
        if 'source-name' not in existing_ref:
            reason = _("Reference must contain source-name.")
            raise exception.InvalidInput(reason=reason)
        
        ref_name = existing_ref['source-name']
        
        # Additional validation for snapshots vs volumes could go here
        # For now, just return the name
        return ref_name

    def extend_volume_helper(self, volume, volume_name, growth_size_mib):
        """Helper method to extend a volume.
        
        This is a simplified version that just grows the volume.
        More complex logic with replication should be handled by the driver.
        
        Args:
            volume: Volume object (not used in this helper)
            volume_name (str): Name of the volume to extend
            growth_size_mib (int): Growth size in MiB
        """
        self.growVolume(volume_name, growth_size_mib)
        
    def wait_for_task_completion(self, task_id):
        """Wait for a 3PAR background task to complete or fail.

        This looks for a task to get out of the 'active' state.
        
        Args:
            task_id (str): Task ID to wait for
            
        Returns:
            dict: Task status information
        """
        from oslo_service import loopingcall
        
        # Wait for the physical copy task to complete
        def _wait_for_task(task_id):
            status = self.getTask(task_id)
            if status['status'] is not self.TASK_ACTIVE:
                self._task_status = status
                raise loopingcall.LoopingCallDone()

        self._task_status = None
        timer = loopingcall.FixedIntervalLoopingCall(
            _wait_for_task, task_id)
        timer.start(interval=1).wait()

        return self._task_status

    @classmethod
    def get_3par_unm_name(cls, volume_id):
        """Get 3PAR unmanaged volume name.
        
        Args:
            volume_id (str): Volume ID
            
        Returns:
            str: Formatted 3PAR unmanaged volume name
        """
        unm_name = cls.encode_name(volume_id)
        return "unm-%s" % unm_name

    @classmethod
    def get_3par_rcg_name(cls, volume_id):
        """Get 3PAR remote copy group name.
        
        Args:
            volume_id (str): Volume ID
            
        Returns:
            str: Formatted 3PAR RCG name (limited to 22 chars)
        """
        rcg_name = cls.encode_name(volume_id)
        rcg = "rcg-%s" % rcg_name
        return rcg[:22]

    @classmethod
    def get_3par_remote_rcg_name(cls, volume_id, provider_location):
        """Get 3PAR remote RCG name.
        
        Args:
            volume_id (str): Volume ID
            provider_location (str): Provider location
            
        Returns:
            str: Formatted 3PAR remote RCG name
        """
        return cls.get_3par_rcg_name(volume_id) + ".r" + str(provider_location)

    @staticmethod
    def capacity_from_size(vol_size):
        """Convert volume size to 3PAR capacity in MiB.
        
        Args:
            vol_size (int): Volume size in GB
            
        Returns:
            int: Capacity in MiB
        """
        # Import here to avoid circular imports
        import math
        try:
            from oslo_utils import units
            # because 3PAR volume sizes are in Mebibytes.
            if int(vol_size) == 0:
                capacity = units.Gi  # default: 1GiB
            else:
                capacity = vol_size * units.Gi
            capacity = int(math.ceil(capacity / units.Mi))
        except ImportError:
            # Fallback calculation without oslo_utils
            if int(vol_size) == 0:
                capacity = 1024  # default: 1GiB in MiB
            else:
                capacity = vol_size * 1024  # GB to MiB
        return capacity

    # =================
    # ENHANCED LICENSE CHECKING METHODS
    # =================

    def check_qos_license(self, valid_licenses):
        """Check if QoS (Priority Optimization) license is enabled.
        
        Args:
            valid_licenses (list): List of valid licenses
            
        Returns:
            bool: True if QoS license is enabled
        """
        return self._check_license_enabled(valid_licenses, PRIORITY_OPT_LIC, "QoS_support")

    def check_thin_provisioning_license(self, valid_licenses):
        """Check if Thin Provisioning license is enabled.
        
        Args:
            valid_licenses (list): List of valid licenses
            
        Returns:
            bool: True if Thin Provisioning license is enabled
        """
        return self._check_license_enabled(valid_licenses, THIN_PROV_LIC, "Thin_provisioning_support")

    def check_compression_license(self, valid_licenses):
        """Check if Compression license is enabled.
        
        Args:
            valid_licenses (list): List of valid licenses
            
        Returns:
            bool: True if Compression license is enabled
        """
        return self._check_license_enabled(valid_licenses, COMPRESSION_LIC, "Compression")

    def check_priority_optimization_license(self, valid_licenses):
        """Check if Priority Optimization license is enabled.
        
        Args:
            valid_licenses (list): List of valid licenses
            
        Returns:
            bool: True if Priority Optimization license is enabled
        """
        return self._check_license_enabled(valid_licenses, PRIORITY_OPT_LIC, "Priority_optimization")

    # =================
    # ENHANCED UTILITY FUNCTIONS
    # =================

    @staticmethod
    def get_qos_value(qos, key, default=None):
        """Get QoS value from dictionary with default.
        
        Args:
            qos (dict): QoS dictionary
            key (str): Key to lookup
            default: Default value if key not found
            
        Returns:
            Value from qos dict or default
        """
        if key in qos:
            return qos[key]
        else:
            return default

    @staticmethod
    def safe_hostname(connector, configuration):
        """Create safe hostname for 3PAR (max 31 characters).
        
        We have to use a safe hostname length for 3PAR host names.
        
        Args:
            connector (dict): Connector info with host
            configuration: Configuration object
            
        Returns:
            str: Safe hostname truncated to 31 characters
        """
        hostname = connector['host']
        unique_fqdn_network = getattr(configuration, 'unique_fqdn_network', False)
        
        if not unique_fqdn_network and connector.get('initiator'):
            iqn = connector.get('initiator')
            iqn = iqn.replace(":", "-")
            return iqn[::-1][:31]
        else:
            try:
                index = hostname.index('.')
            except ValueError:
                # couldn't find it
                index = len(hostname)

            # we'll just chop this off for now.
            if index > 31:
                index = 31

            return hostname[:index]

    def calculate_pool_stats(self, cpg_name, api_version, sr_support=True):
        """Calculate comprehensive pool statistics for a CPG.
        
        Args:
            cpg_name (str): CPG name
            api_version (int): API version
            sr_support (bool): System Reporter support
            
        Returns:
            dict: Pool statistics
        """
        # Constants for conversion
        const = 0.0009765625  # MiB to GB conversion
        
        # Get CPG information
        cpg = self.getCPG(cpg_name)
        
        # Get statistical capabilities if supported
        stat_capabilities = {
            THROUGHPUT: None,
            BANDWIDTH: None,
            LATENCY: None,
            IO_SIZE: None,
            QUEUE_LENGTH: None,
            AVG_BUSY_PERC: None
        }
        
        if api_version >= SRSTATLD_API_VERSION and sr_support:
            try:
                # Try to get statistical data if available
                stat_capabilities = self.getCPGStatData(cpg_name, 'daily', '7d')
            except Exception:
                # Return empty stats if not available
                pass
        
        # Calculate volume counts
        if 'numTDVVs' in cpg:
            total_volumes = int(
                cpg['numFPVVs'] + cpg['numTPVVs'] + cpg['numTDVVs']
            )
        else:
            total_volumes = int(
                cpg['numFPVVs'] + cpg['numTPVVs']
            )
        
        # Calculate capacity
        if 'limitMiB' not in cpg['SDGrowth']:
            # CPG usable free space for limitless CPG
            cpg_avail_space = self.getCPGAvailableSpace(cpg_name)
            total_capacity = int(
                (cpg['SDUsage']['usedMiB'] +
                 cpg['UsrUsage']['usedMiB'] +
                 cpg_avail_space['usableFreeMiB']) * const)
        else:
            total_capacity = int(cpg['SDGrowth']['limitMiB'] * const)

        provisioned_capacity = int((cpg['UsrUsage']['totalMiB'] +
                                   cpg['SAUsage']['totalMiB'] +
                                   cpg['SDUsage']['totalMiB']) * const)
        
        free_capacity = total_capacity - provisioned_capacity
        capacity_utilization = (
            (float(total_capacity - free_capacity) /
             float(total_capacity)) * 100) if total_capacity > 0 else 0

        return {
            'cpg_name': cpg_name,
            'total_capacity_gb': total_capacity,
            'free_capacity_gb': free_capacity,
            'provisioned_capacity_gb': provisioned_capacity,
            'total_volumes': total_volumes,
            'capacity_utilization': capacity_utilization,
            'statistical_capabilities': stat_capabilities,
            'cpg_info': cpg
        }

    # Additional utility methods needed by comprehensive driver
    def add_name_id_to_comment(self, comment, volume):
        """Add name_id to comment dictionary."""
        name_id = volume.get('_name_id')
        if name_id:
            comment['_name_id'] = name_id

    def get_updated_comment(self, vol_name, **values):
        """Get updated comment with new values."""
        import json
        vol = self.getVolume(vol_name)
        comment = json.loads(vol['comment']) if vol.get('comment') else {}
        comment.update(values)
        return comment

    def get_vlun(self, volume_name, hostname, lun_id=None, nsp=None):
        """Find a VLUN on a 3PAR host."""
        vluns = self.getHostVLUNs(hostname)
        
        found_vlun = None
        for vlun in vluns:
            if volume_name in vlun['volumeName']:
                if lun_id is not None:
                    if vlun['lun'] == lun_id:
                        found_vlun = vlun
                        break
                else:
                    found_vlun = vlun
                    break
        
        return found_vlun

    def get_persona_type(self, volume, hpe3par_keys=None):
        """Get persona type for volume."""
        # This is a simplified version - the real implementation
        # would need access to driver configuration
        default_persona = '2 - Generic-ALUA'
        if hpe3par_keys:
            persona_value = hpe3par_keys.get('persona', default_persona)
            return self.validate_persona(persona_value)
        return default_persona

    def _get_replication_mode_from_volume_type(self, volume_type):
        """Get replication mode from volume type."""
        # This is a placeholder - real implementation would analyze volume type
        return 'sync'

    # ===================
    # UTILITY FUNCTIONS FOR CODE REDUCTION
    # ===================
    
    @staticmethod
    def extract_cpg_from_volume_response(vol, allow_snap=False, fallback_pool=None):
        """Extract CPG from volume response.
        
        Args:
            vol: Volume response dictionary
            allow_snap: Whether to allow snapCPG fallback
            fallback_pool: Fallback pool name if no CPG found
            
        Returns:
            str: CPG name
        """
        if 'userCPG' in vol:
            return vol['userCPG']
        elif allow_snap and 'snapCPG' in vol:
            return vol['snapCPG']
        else:
            return fallback_pool
    
    @staticmethod
    def build_volume_copy_params(volume_name, temp_vol_name, cpg, tpvv, tdvv, compression=None, snap_cpg=None, online=True):
        """Build parameters for volume copy operation.
        
        Args:
            volume_name: Source volume name
            temp_vol_name: Destination volume name
            cpg: CPG name
            tpvv: Thin provisioned virtual volume flag
            tdvv: Thin deduplication virtual volume flag
            compression: Compression policy
            snap_cpg: Snapshot CPG
            online: Online copy flag
            
        Returns:
            dict: Parameters for copy operation
        """
        optional = {
            'online': online,
            'tpvv': tpvv, 
            'tdvv': tdvv
        }
        
        if snap_cpg:
            optional['snapCPG'] = snap_cpg
            
        if compression is not None:
            optional['compression'] = compression
            
        return {
            'source': volume_name,
            'destination': temp_vol_name,
            'cpg': cpg,
            'optional': optional
        }
    
    @staticmethod
    def validate_snapshot_dependencies(snap_list, volume_name):
        """Validate that volume has no dependent snapshots.
        
        Args:
            snap_list: List of snapshots
            volume_name: Volume name
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if snap_list:
            snap_str = ",".join(snap_list)
            error_msg = ("Volume %(name)s has dependent snapshots: %(snap)s."
                        " Either flatten or remove the dependent snapshots:"
                        " %(snap)s for the conversion of volume %(name)s to"
                        " succeed." % {'name': volume_name, 'snap': snap_str})
            return False, error_msg
        return True, None
    
    @staticmethod
    def generate_temp_volume_name(volume_name, prefix="omv-"):
        """Generate temporary volume name for migration.
        
        Args:
            volume_name: Original volume name
            prefix: Prefix for temp volume (default: omv-)
            
        Returns:
            str: Temporary volume name
        """
        return volume_name.replace("osv-", prefix)
    
    @staticmethod
    def process_task_completion_result(task_status, operation_name):
        """Process task completion and return status info.
        
        Args:
            task_status: Task status dictionary
            operation_name: Name of the operation
            
        Returns:
            dict: Status information
        """
        return {
            'task_done': task_status['status'] == HPE3ParClient.TASK_DONE,
            'operation': operation_name,
            'status': task_status.get('status'),
            'message': task_status.get('message', '')
        }
    
    @staticmethod
    def build_volume_set_creation_params(volume_id, cpg, qos_data=None, flash_cache_data=None):
        """Build parameters for volume set creation.
        
        Args:
            volume_id: Volume ID
            cpg: CPG name
            qos_data: QoS configuration data
            flash_cache_data: Flash cache configuration data
            
        Returns:
            dict: Volume set creation parameters
        """
        return {
            'volume_id': volume_id,
            'cpg': cpg,
            'qos': qos_data or {},
            'flash_cache': flash_cache_data,
            'has_qos': bool(qos_data),
            'has_flash_cache': bool(flash_cache_data)
        }
    
    @staticmethod
    def extract_qos_from_specs(kvs, hpe_qos_keys):
        """Extract QoS values from specifications.
        
        Args:
            kvs: Key-value specifications
            hpe_qos_keys: List of valid QoS keys
            
        Returns:
            dict: QoS specifications
        """
        qos = {}
        for key, value in kvs.items():
            if 'qos:' in key:
                fields = key.split(':')
                key = fields[1]
            if key in hpe_qos_keys:
                qos[key] = value
        return qos
    
    @staticmethod
    def build_volume_rename_params(new_name, comment=None):
        """Build parameters for volume rename operation.
        
        Args:
            new_name: New volume name
            comment: Optional comment
            
        Returns:
            dict: Rename parameters
        """
        params = {'newName': new_name}
        if comment:
            params['comment'] = comment
        return params
    
    @staticmethod
    def build_volume_modify_params(new_name=None, comment=None, snap_cpg=None):
        """Build parameters for volume modification.
        
        Args:
            new_name: New volume name
            comment: Volume comment
            snap_cpg: Snapshot CPG
            
        Returns:
            dict: Modification parameters
        """
        params = {}
        if new_name:
            params['newName'] = new_name
        if comment:
            params['comment'] = comment
        if snap_cpg:
            params['snapCPG'] = snap_cpg
        return params
    
    @staticmethod
    def validate_existing_volume_ref(existing_ref, is_snapshot=False):
        """Validate existing volume reference.
        
        Args:
            existing_ref: Reference dictionary
            is_snapshot: Whether this is for a snapshot
            
        Returns:
            str: Source name if valid
            
        Raises:
            ValueError: If reference is invalid
        """
        if 'source-name' in existing_ref:
            return existing_ref['source-name']
        
        entity_type = "snapshot" if is_snapshot else "volume"
        raise ValueError(f"Reference must be for an existing 3PAR {entity_type}.")
    
    @staticmethod
    def check_reserved_name_pattern(name):
        """Check if name matches reserved pattern.
        
        Args:
            name: Name to check
            
        Returns:
            bool: True if name is reserved
        """
        return bool(re.match('osv-*|oss-*|vvs-*|unm-*', name))
    
    @staticmethod
    def calculate_volume_size_mib(size_gb):
        """Calculate volume size in MiB from GB.
        
        Args:
            size_gb: Size in GB
            
        Returns:
            int: Size in MiB
        """
        import math
        return int(math.ceil(float(size_gb) * 1024))
    
    @staticmethod
    def build_snapshot_creation_params(snap_name, copy_of_name, extra=None, config=None):
        """Build parameters for snapshot creation.
        
        Args:
            snap_name: Snapshot name
            copy_of_name: Source volume name
            extra: Extra metadata
            config: Configuration settings
            
        Returns:
            dict: Snapshot creation parameters
        """
        import json
        
        optional = {'readOnly': False}
        
        if extra:
            optional['comment'] = json.dumps(extra)
            
        if config:
            if hasattr(config, 'hpe3par_snapshot_expiration') and config.hpe3par_snapshot_expiration:
                optional['expirationHours'] = int(config.hpe3par_snapshot_expiration)
                
            if hasattr(config, 'hpe3par_snapshot_retention') and config.hpe3par_snapshot_retention:
                optional['retentionHours'] = int(config.hpe3par_snapshot_retention)
        
        return {
            'snap_name': snap_name,
            'copy_of_name': copy_of_name,
            'optional': optional
        }

    @staticmethod
    def process_volume_set_addition(vvs_name, volume_name, volume_id, cpg, qos, flash_cache, hpe_qos_keys, qos_priority_level):
        """Process volume set addition logic.
        
        Args:
            vvs_name: Volume set name (None if auto-generated)
            volume_name: Volume name to add
            volume_id: Volume ID
            cpg: CPG name
            qos: QoS settings
            flash_cache: Flash cache settings
            hpe_qos_keys: Valid QoS keys
            qos_priority_level: QoS priority mapping
            
        Returns:
            dict: Volume set operation parameters
        """
        if vvs_name is not None:
            # Admin has set a volume set name to add the volume to
            return {
                'operation': 'add_to_existing',
                'vvs_name': vvs_name,
                'volume_name': volume_name
            }
        else:
            # Create new volume set
            auto_vvs_name = HPE3ParClient.get_3par_vvs_name(volume_id)
            return {
                'operation': 'create_new',
                'vvs_name': auto_vvs_name,
                'volume_name': volume_name,
                'cpg': cpg,
                'qos': qos,
                'flash_cache': flash_cache,
                'hpe_qos_keys': hpe_qos_keys,
                'qos_priority_level': qos_priority_level
            }
    
    @staticmethod
    def build_manage_existing_params(target_vol_name, volume, new_vol_name, volume_type=None):
        """Build parameters for managing existing volumes.
        
        Args:
            target_vol_name: Target volume name
            volume: Volume object
            new_vol_name: New volume name
            volume_type: Volume type object
            
        Returns:
            dict: Management parameters
        """
        import json
        
        new_comment = {}
        
        # Use display name from volume
        if volume.get('display_name'):
            new_comment['display_name'] = volume['display_name']
        
        # Generate volume information based on new ID
        name = 'volume-' + volume['id']
        new_comment['volume_id'] = volume['id']
        new_comment['name'] = name
        new_comment['type'] = 'OpenStack'
        
        # Add name_id if present
        name_id = volume.get('_name_id')
        if name_id:
            new_comment['_name_id'] = name_id
        
        modify_params = {
            'newName': new_vol_name,
            'comment': json.dumps(new_comment)
        }
        
        return {
            'target_vol_name': target_vol_name,
            'modify_params': modify_params,
            'new_comment': new_comment,
            'volume_type': volume_type
        }
    
    @staticmethod 
    def build_unmanage_params(volume, vol_name):
        """Build parameters for unmanaging volumes.
        
        Args:
            volume: Volume object
            vol_name: Current volume name
            
        Returns:
            dict: Unmanage parameters
        """
        # Use the user visible ID for easier location
        new_vol_name = HPE3ParClient.get_3par_unm_name(volume['id'])
        
        return {
            'current_name': vol_name,
            'new_name': new_vol_name,
            'display_name': volume.get('display_name', ''),
            'volume_id': volume['id']
        }
    
    @staticmethod
    def process_volume_size_calculation(vol_size_mib, unit_conversion_factor=1024):
        """Process volume size calculations.
        
        Args:
            vol_size_mib: Volume size in MiB
            unit_conversion_factor: Conversion factor (default: 1024 for MiB to GiB)
            
        Returns:
            int: Calculated size
        """
        import math
        return int(math.ceil(float(vol_size_mib) / unit_conversion_factor))
    
    @staticmethod
    def build_group_snapshot_params(group_snapshot, cg_id):
        """Build group snapshot parameters.
        
        Args:
            group_snapshot: Group snapshot object
            cg_id: Consistency group ID
            
        Returns:
            dict: Group snapshot parameters
        """
        snap_shot_name = HPE3ParClient.get_3par_snap_name(group_snapshot.id) + "-@count@"
        copy_of_name = HPE3ParClient.get_3par_vvs_name(cg_id)
        
        extra = {
            'group_snapshot_id': group_snapshot.id,
            'group_id': cg_id,
            'description': group_snapshot.description
        }
        
        return {
            'snap_shot_name': snap_shot_name,
            'copy_of_name': copy_of_name,
            'extra': extra
        }
    
    @staticmethod
    def process_manageable_volume_filter(volume, already_managed, cinder_cpg):
        """Process filtering for manageable volumes.
        
        Args:
            volume: Volume dictionary from 3PAR
            already_managed: Set of already managed volume names
            cinder_cpg: Cinder CPG name
            
        Returns:
            dict or None: Manageable volume info or None if not manageable
        """
        volume_name = volume.get('name', '')
        
        # Skip if already managed
        if volume_name in already_managed:
            return None
            
        # Skip if not in correct CPG
        if volume.get('userCPG') != cinder_cpg:
            return None
            
        # Skip temporary volumes
        if (volume_name.startswith('tsv-') or 
            volume_name.startswith('tss-') or
            volume_name.startswith('ums-')):
            return None
        
        # Build manageable volume info
        volume_info = {
            'reference': {'source-name': volume_name},
            'size': int(math.ceil(float(volume['sizeMiB']) / 1024)),
            'cinder_id': None,
            'extra_info': {
                'userCPG': volume.get('userCPG'),
                'snapCPG': volume.get('snapCPG'),
                'provisioningType': volume.get('provisioningType'),
                'comment': volume.get('comment', '')
            }
        }
        
        return volume_info
    
    @staticmethod
    def delete_vlun_utility(client_obj, volume_name, hostname, wwn=None, iqn=None, delete_3par_host_callback=None):
        """Delete VLUN and optionally clean up host resources.
        
        Args:
            client_obj: 3PAR client instance
            volume_name: Name of the volume on 3PAR
            hostname: Host name
            wwn: WWN list for cleanup
            iqn: IQN list for cleanup
            delete_3par_host_callback: Callback function to delete 3PAR host
            
        Returns:
            dict: Operation result with warnings if any
        """
        result = {'warnings': []}
        
        if hostname:
            vluns = client_obj.getHostVLUNs(hostname)
        else:
            # In case of 'force detach', hostname is None
            vluns = client_obj.getVLUNs()['members']

        # When deleting VLUNs, you simply need to remove the template VLUN
        # and any active VLUNs will be automatically removed.  The template
        # VLUN are marked as active: False

        modify_host = True
        volume_vluns = []

        for vlun in vluns:
            if volume_name in vlun['volumeName']:
                # template VLUNs are 'active' = False
                if not vlun['active']:
                    volume_vluns.append(vlun)

        if not volume_vluns:
            warning_msg = f"3PAR vlun for volume {volume_name} not found on host {hostname}"
            result['warnings'].append(warning_msg)
            return result

        # VLUN Type of MATCHED_SET 4 requires the port to be provided
        for vlun in volume_vluns:
            if hostname is None:
                hostname = vlun.get('hostname')
            if 'portPos' in vlun:
                client_obj.deleteVLUN(volume_name, vlun['lun'],
                                      hostname=hostname,
                                      port=vlun['portPos'])
            else:
                client_obj.deleteVLUN(volume_name, vlun['lun'],
                                      hostname=hostname)

        # Determine if there are other volumes attached to the host.
        # This will determine whether we should try removing host from host set
        # and deleting the host.
        vluns = []
        try:
            vluns = client_obj.getHostVLUNs(hostname)
        except Exception:
            # All VLUNs removed from host
            pass

        if wwn is not None and not isinstance(wwn, list):
            wwn = [wwn]
        if iqn is not None and not isinstance(iqn, list):
            iqn = [iqn]

        for vlun in vluns:
            if vlun.get('active'):
                if (wwn is not None and vlun.get('remoteName').lower() in wwn) or \
                   (iqn is not None and vlun.get('remoteName').lower() in iqn):
                    # vlun with wwn/iqn exists so do not modify host.
                    modify_host = False
                    break

        if len(vluns) == 0:
            # We deleted the last vlun, so try to delete the host too.
            # This check avoids the old unnecessary try/fail when vluns exist
            # but adds a minor race condition if a vlun is manually deleted
            # externally at precisely the wrong time. Worst case is leftover
            # host, so it is worth the unlikely risk.

            try:
                # Use callback to delete 3PAR host if provided
                if delete_3par_host_callback:
                    delete_3par_host_callback(hostname, client_obj)
            except Exception as ex:
                # Any exception down here is only logged.  The vlun is deleted.

                # If the host is in a host set, the delete host will fail and
                # the host will remain in the host set.  This is desired
                # because cinder was not responsible for the host set
                # assignment.  The host set could be used outside of cinder
                # for future needs (e.g. export volume to host set).

                # The log info explains why the host was left alone.
                warning_msg = (f"3PAR vlun for volume '{volume_name}' was deleted, "
                             f"but the host '{hostname}' was not deleted "
                             f"because: {getattr(ex, 'get_description', lambda: str(ex))()}")
                result['warnings'].append(warning_msg)
        elif modify_host:
            if wwn is not None:
                mod_request = {'pathOperation': client_obj.HOST_EDIT_REMOVE,
                               'FCWWNs': wwn}
            else:
                mod_request = {'pathOperation': client_obj.HOST_EDIT_REMOVE,
                               'iSCSINames': iqn}
            try:
                client_obj.modifyHost(hostname, mod_request)
            except Exception as ex:
                warning_msg = (f"3PAR vlun for volume '{volume_name}' was deleted, "
                             f"but the host '{hostname}' was not Modified "
                             f"because: {getattr(ex, 'get_description', lambda: str(ex))()}")
                result['warnings'].append(warning_msg)
        
        return result
    
    @staticmethod
    def convert_to_base_volume_utility(client_obj, volume_name, temp_vol_name, cpg, 
                                     tpvv, tdvv, compression, comment, 
                                     validate_callback=None, wait_callback=None, 
                                     process_task_callback=None, build_rename_callback=None):
        """Convert volume to base volume utility.
        
        Args:
            client_obj: 3PAR client instance
            volume_name: Original volume name
            temp_vol_name: Temporary volume name for conversion
            cpg: CPG name
            tpvv: Thin provisioning flag
            tdvv: Dedup flag  
            compression: Compression policy
            comment: Volume comment
            validate_callback: Callback to validate snapshot dependencies
            wait_callback: Callback to wait for task completion
            process_task_callback: Callback to process task completion result
            build_rename_callback: Callback to build rename parameters
            
        Returns:
            dict: Operation result with task_id and any errors
        """
        result = {'success': False, 'task_id': None, 'error': None}
        
        try:
            # If volume has snapshot, validate dependencies if callback provided
            if validate_callback:
                snap_list = client_obj.getVolumeSnapshots(volume_name)
                is_valid, error_msg = validate_callback(snap_list, volume_name)
                if not is_valid:
                    result['error'] = f"Volume is busy: {error_msg}"
                    return result

            # Create a physical copy of the volume
            task_id = client_obj.copy_volume(volume_name, temp_vol_name,
                                           cpg, cpg, tpvv, tdvv, compression)
            result['task_id'] = task_id

            # Wait for task completion if callback provided
            if wait_callback:
                task_status = wait_callback(task_id)
                
                # Process task completion if callback provided
                if process_task_callback:
                    completion_result = process_task_callback(task_status, 'convert_to_base_volume')
                    if not completion_result['task_done']:
                        result['error'] = f'Copy volume task failed: convert_to_base_volume: status={task_status}'
                        return result

            # Set comment if provided
            if comment:
                client_obj.modifyVolume(temp_vol_name, {'comment': comment})

            # Delete source volume after the copy is complete
            client_obj.deleteVolume(volume_name)

            # Rename the new volume to the original name
            if build_rename_callback:
                rename_params = build_rename_callback(volume_name)
                client_obj.modifyVolume(temp_vol_name, rename_params)

            result['success'] = True
            
        except Exception as ex:
            result['error'] = str(ex)
            
        return result
    
    @staticmethod
    def set_flash_cache_policy_in_vvs_utility(client_obj, flash_cache, vvs_name):
        """Set flash cache policy in volume set utility.
        
        Args:
            client_obj: 3PAR client instance
            flash_cache: Flash cache policy
            vvs_name: Volume set name
            
        Returns:
            dict: Operation result with success flag and any error
        """
        result = {'success': True, 'error': None}
        
        if flash_cache:
            try:
                client_obj.modifyVolumeSet(vvs_name, flashCachePolicy=flash_cache)
            except Exception as ex:
                result['success'] = False
                result['error'] = str(ex)
                
        return result
    
    # ================
    # NAME ENCODING UTILITIES
    # ================
    
    @staticmethod
    def encode_name(name):
        """Encode name for 3PAR compatibility.
        
        Args:
            name: Name to encode
            
        Returns:
            str: Encoded name
        """
        import uuid
        import base64
        
        uuid_str = name.replace("-", "")
        vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
        vol_encoded = base64.encode_as_text(vol_uuid.bytes)

        # 3par doesn't allow +, nor /
        vol_encoded = vol_encoded.replace('+', '.')
        vol_encoded = vol_encoded.replace('/', '-')
        # strip off the == as 3par doesn't like those.
        vol_encoded = vol_encoded.replace('=', '')
        return vol_encoded

    @classmethod
    def get_3par_vol_name(cls, volume_id, temp_vol=False):
        """Get converted 3PAR volume name.

        Converts the openstack volume id from
        ecffc30f-98cb-4cf5-85ee-d7309cc17cd2
        to
        osv-7P.DD5jLTPWF7tcwnMF80g

        We convert the 128 bits of the uuid into a 24character long
        base64 encoded string to ensure we don't exceed the maximum
        allowed 31 character name limit on 3Par

        We strip the padding '=' and replace + with .
        and / with -

        volume_id is a polymorphic parameter and can be either a string or a
        volume (OVO or dict representation).
        """
        # Accept OVOs (what we should only receive), dict (so we don't have to
        # change all our unit tests), and ORM (because we some methods still
        # pass it, such as terminate_connection).
        if hasattr(volume_id, 'get'):  # Duck typing for dict-like objects
            volume_id = volume_id.get('_name_id') or volume_id['id']
        elif hasattr(volume_id, 'id'):  # Handle OVO objects
            volume_id = getattr(volume_id, '_name_id', None) or volume_id.id
            
        volume_name = cls.encode_name(volume_id)
        if temp_vol:
            # is this a temporary volume
            # this is done during migration
            prefix = "tsv-%s"
        else:
            prefix = "osv-%s"
        return prefix % volume_name

    @classmethod
    def get_3par_snap_name(cls, snapshot_id, temp_snap=False):
        """Get 3PAR snapshot name."""
        snapshot_name = cls.encode_name(snapshot_id)
        if temp_snap:
            # is this a temporary snapshot
            # this is done during cloning
            prefix = "tss-%s"
        else:
            prefix = "oss-%s"
        return prefix % snapshot_name

    @classmethod
    def get_3par_ums_name(cls, snapshot_id):
        """Get 3PAR UMS name."""
        ums_name = cls.encode_name(snapshot_id)
        return "ums-%s" % ums_name

    @classmethod
    def get_3par_vvs_name(cls, volume_id):
        """Get 3PAR volume set name."""
        vvs_name = cls.encode_name(volume_id)
        return "vvs-%s" % vvs_name

    @classmethod
    def get_3par_unm_name(cls, volume_id):
        """Get 3PAR UNM name."""
        unm_name = cls.encode_name(volume_id)
        return "unm-%s" % unm_name
    
    # ================
    # MIGRATION UTILITIES
    # ================
    
    @staticmethod
    def rename_migrated_utility(client_obj, volume_id, dest_volume_id,
                               volume_name_id, get_3par_vol_name_callback,
                               get_updated_comment_callback, log_callback=None):
        """Rename migrated volume utility.
        
        Args:
            client_obj: 3PAR client instance
            volume_id: Source volume ID
            dest_volume_id: Destination volume ID
            volume_name_id: Volume name ID for rename
            get_3par_vol_name_callback: Callback to get 3PAR volume name
            get_updated_comment_callback: Callback to get updated comment
            log_callback: Optional logging callback
            
        Returns:
            dict: Operation result with success flag and any warnings
        """
        result = {'success': True, 'warnings': []}
        
        def log_error(vol_type, error, src, dest, rename_name=None, original_name=None):
            error_msg = (f"Changing the {vol_type} volume name from {src} to "
                        f"{dest} failed because {error}")
            result['warnings'].append(error_msg)
            if log_callback:
                log_callback(error_msg)
            
            if rename_name:
                original_name = original_name or dest
                warn_msg = (f"Migration will fail to delete the original volume. "
                           f"It must be manually renamed from {rename_name} to "
                           f"{original_name} in the backend, and then we "
                           f"have to tell cinder to delete volume {dest_volume_id}")
                result['warnings'].append(warn_msg)
                if log_callback:
                    log_callback(warn_msg)

        original_volume_renamed = False
        
        # Get volume names
        original_name = get_3par_vol_name_callback(volume_id)
        temp_name = get_3par_vol_name_callback(volume_id, temp_vol=True)
        current_name = get_3par_vol_name_callback(dest_volume_id)
        volume_id_name = get_3par_vol_name_callback(volume_name_id)

        # Try renaming original volume to temporary name
        try:
            volumeTempMods = {'newName': temp_name}
            client_obj.modifyVolume(original_name, volumeTempMods)
            original_volume_renamed = True
        except Exception as e:
            # HTTPNotFound is expected when original volume is on different backend
            if 'HTTPNotFound' not in str(type(e)):
                log_error('original', e, original_name, temp_name)
                result['success'] = False
                return result

        # Rename destination volume to source volume name
        try:
            new_comment = get_updated_comment_callback(current_name,
                                                     volume_id=volume_id,
                                                     _name_id=None)
            volumeMods = {'newName': volume_id_name, 'comment': new_comment}
            client_obj.modifyVolume(current_name, volumeMods)
        except Exception as e:
            if original_volume_renamed:
                _name = temp_name
            else:
                _name = original_name = None
            log_error('migrating', e, current_name, volume_id_name, _name, original_name)
            result['success'] = False
            return result

        # Rename original volume to destination volume name (swap names)
        if original_volume_renamed:
            try:
                old_comment = get_updated_comment_callback(
                    original_name,
                    volume_id=dest_volume_id,
                    _name_id=volume_name_id)
                volumeCurrentMods = {'newName': current_name,
                                   'comment': old_comment}
                client_obj.modifyVolume(temp_name, volumeCurrentMods)
            except Exception as e:
                log_error('original', e, temp_name, current_name, temp_name)
                # Don't fail the operation for this error
        
        return result

    @staticmethod
    def rename_migrated_vvset_utility(client_obj, src_volume_id, dest_volume_id,
                                    get_3par_vvs_name_callback, log_callback=None):
        """Rename migrated volume set utility.
        
        Args:
            client_obj: 3PAR client instance
            src_volume_id: Source volume ID
            dest_volume_id: Destination volume ID
            get_3par_vvs_name_callback: Callback to get 3PAR VVS name
            log_callback: Optional logging callback
            
        Returns:
            dict: Operation result with warnings if any
        """
        result = {'warnings': []}
        
        vvs_name_src = get_3par_vvs_name_callback(src_volume_id)
        vvs_name_dest = get_3par_vvs_name_callback(dest_volume_id)

        # Create unique temp name
        temp_vvs_name = 'tos-' + vvs_name_src[4:]

        # Rename destination to temp
        try:
            client_obj.modifyVolumeSet(vvs_name_dest, newName=temp_vvs_name)
        except Exception as ex:
            error_msg = f"Failed to rename vvset {vvs_name_dest} to {temp_vvs_name}: {ex}"
            result['warnings'].append(error_msg)
            if log_callback:
                log_callback(error_msg)

        # Rename source to destination
        try:
            client_obj.modifyVolumeSet(vvs_name_src, newName=vvs_name_dest)
        except Exception as ex:
            error_msg = f"Failed to rename vvset {vvs_name_src} to {vvs_name_dest}: {ex}"
            result['warnings'].append(error_msg)
            if log_callback:
                log_callback(error_msg)

        # Rename temp to source
        try:
            client_obj.modifyVolumeSet(temp_vvs_name, newName=vvs_name_src)
        except Exception as ex:
            error_msg = f"Failed to rename vvset {temp_vvs_name} to {vvs_name_src}: {ex}"
            result['warnings'].append(error_msg)
            if log_callback:
                log_callback(error_msg)
        
        return result
    
    # ================
    # REMOTE COPY UTILITIES
    # ================
    
    @staticmethod
    def get_3par_remote_rcg_name_utility(volume_rcg_name, provider_location):
        """Get 3PAR remote RCG name utility."""
        return volume_rcg_name + ".r" + str(provider_location)

    @staticmethod
    def get_3par_remote_rcg_name_of_group_utility(group_rcg_name, provider_location):
        """Get 3PAR remote RCG name of group utility."""
        return group_rcg_name + ".r" + str(provider_location)

    @staticmethod
    def get_hpe3par_tiramisu_value_utility(hpe3par_keys):
        """Get HPE 3PAR tiramisu value utility."""
        hpe3par_tiramisu = False
        if hpe3par_keys.get('group_replication'):
            hpe3par_tiramisu = (hpe3par_keys['group_replication'] == "<is> True")
        return hpe3par_tiramisu

    @staticmethod
    def stop_remote_copy_group_utility(client_obj, rcg_name, log_callback=None):
        """Stop remote copy group utility."""
        try:
            client_obj.stopRemoteCopy(rcg_name)
            return True
        except Exception as ex:
            if log_callback:
                log_callback(f"Stopping remote copy group {rcg_name} failed: {ex}")
            return False

    @staticmethod
    def start_remote_copy_group_utility(client_obj, rcg_name, log_callback=None):
        """Start remote copy group utility."""
        try:
            client_obj.startRemoteCopy(rcg_name)
            return True
        except Exception as ex:
            if log_callback:
                log_callback(f"Starting remote copy group {rcg_name} failed: {ex}")
            return False
    
    # ================
    # CLIENT MANAGEMENT UTILITIES
    # ================
    
    @staticmethod
    def create_replication_client_utility(remote_array, client_module, hpeexceptions_module):
        """Create replication client utility."""
        try:
            if client_module is not None:
                cl = client_module.HPE3ParClient(remote_array['hpe3par_api_url'])
            else:
                raise Exception("hpe3parclient not available")
            
            cl.login(remote_array['hpe3par_username'],
                     remote_array['hpe3par_password'])
        except Exception as ex:
            if 'HTTPUnauthorized' in str(type(ex)):
                msg = f"Failed to Login to 3PAR ({remote_array['hpe3par_api_url']}) because {ex}"
                raise Exception(msg)
            raise ex

        return cl

    @staticmethod
    def destroy_replication_client_utility(client_obj):
        """Destroy replication client utility."""
        if client_obj is not None:
            try:
                client_obj.logout()
            except Exception:
                pass  # Ignore logout errors
    
    # ================
    # VOLUME MANAGEMENT UTILITIES
    # ================
    
    @staticmethod
    def manage_existing_volume_utility(client_obj, volume, existing_ref, target_vol_name,
                                      get_volume_callback, get_volume_type_callback,
                                      retype_callback, log_callback=None):
        """Manage existing volume utility.
        
        Args:
            client_obj: 3PAR client instance
            volume: Volume object
            existing_ref: Existing reference
            target_vol_name: Target volume name
            get_volume_callback: Callback to get volume
            get_volume_type_callback: Callback to get volume type
            retype_callback: Callback to retype volume
            log_callback: Optional logging callback
            
        Returns:
            dict: Management result with updates and rollback info
        """
        import json
        result = {'success': False, 'updates': {}, 'rollback_info': {}}
        
        # Check for the existence of the virtual volume
        old_comment_str = ""
        try:
            vol = get_volume_callback(target_vol_name)
            if 'comment' in vol:
                old_comment_str = vol['comment']
        except Exception as ex:
            if 'HTTPNotFound' in str(type(ex)):
                result['error'] = f"Virtual volume '{target_vol_name}' doesn't exist on array."
                return result
            raise

        result['rollback_info']['old_comment'] = old_comment_str
        
        new_comment = {}

        # Use the display name from the existing volume if no new name was chosen by the user
        if volume['display_name']:
            display_name = volume['display_name']
            new_comment['display_name'] = volume['display_name']
        elif 'comment' in vol:
            display_name = client_obj._get_3par_vol_comment_value(vol['comment'], 'display_name')
            if display_name:
                new_comment['display_name'] = display_name
        else:
            display_name = None

        # Generate the new volume information based on the new ID
        from .client import HPE3ParClient
        new_vol_name = HPE3ParClient.get_3par_vol_name(volume['id'])
        name = 'volume-' + volume['id']

        new_comment['volume_id'] = volume['id']
        new_comment['name'] = name
        new_comment['type'] = 'OpenStack'
        client_obj.add_name_id_to_comment(new_comment, volume)

        volume_type = None
        if volume['volume_type_id']:
            try:
                volume_type = get_volume_type_callback(volume['volume_type_id'])
            except Exception:
                result['error'] = f"Volume type ID '{volume['volume_type_id']}' is invalid."
                return result

        new_vals = {'newName': new_vol_name, 'comment': json.dumps(new_comment)}

        # Ensure that snapCPG is set
        if 'snapCPG' not in vol:  # Simplified condition
            new_vals['snapCPG'] = vol['userCPG']
            if log_callback:
                log_callback(f"Virtual volume {display_name} '{new_vol_name}' snapCPG "
                           f"is empty so it will be set to: {new_vals['snapCPG']}")

        result['rollback_info']['target_vol_name'] = target_vol_name
        result['rollback_info']['new_vol_name'] = new_vol_name

        # Update the existing volume with the new name and comments
        try:
            client_obj.modifyVolume(target_vol_name, new_vals)
        except Exception as ex:
            result['error'] = f"Failed to modify volume: {ex}"
            return result

        if log_callback:
            log_callback(f"Virtual volume '{existing_ref['source-name']}' renamed to '{new_vol_name}'.")

        retyped = False
        model_update = None
        if volume_type:
            if log_callback:
                log_callback(f"Virtual volume {display_name} '{new_vol_name}' is being retyped.")

            try:
                retyped, model_update = retype_callback(volume, volume_type)
                if log_callback:
                    log_callback(f"Virtual volume {display_name} successfully retyped to "
                               f"{volume_type.get('name')}.")
            except Exception as ex:
                # Try to undo the rename and clear the new comment
                try:
                    client_obj.modifyVolume(new_vol_name, 
                                          {'newName': target_vol_name,
                                           'comment': old_comment_str})
                except Exception:
                    pass  # Ignore rollback errors
                result['error'] = f"Failed to retype volume: {ex}"
                return result

        updates = {'display_name': display_name}
        if retyped and model_update:
            updates.update(model_update)

        result['success'] = True
        result['updates'] = updates
        result['display_name'] = display_name
        result['new_vol_name'] = new_vol_name

        if log_callback:
            log_callback(f"Virtual volume {display_name} '{new_vol_name}' is now being managed.")

        return result

    @staticmethod
    def get_manageable_volumes_utility(client_obj, already_managed, cinder_cpg, 
                                     get_vlun_callback=None):
        """Get manageable volumes utility.
        
        Args:
            client_obj: 3PAR client instance
            already_managed: Dict of already managed volumes
            cinder_cpg: Cinder CPG name
            get_vlun_callback: Optional callback to get VLUN info
            
        Returns:
            list: List of manageable volumes
        """
        manageable_vols = []

        body = client_obj.getVolumes()
        all_volumes = body['members']
        
        for vol in all_volumes:
            cpg = vol.get('userCPG')
            if cpg == cinder_cpg:
                size_gb = int(vol['sizeMiB'] / 1024)
                vol_name = vol['name']
                
                if vol_name in already_managed:
                    is_safe = False
                    reason_not_safe = 'Volume already managed'
                    cinder_id = already_managed[vol_name]
                else:
                    is_safe = False
                    hostname = None
                    cinder_id = None
                    
                    # Check if the unmanaged volume is attached to any host
                    if get_vlun_callback:
                        try:
                            vlun = get_vlun_callback(vol_name)
                            hostname = vlun['hostname']
                        except Exception:
                            # not attached to any host
                            is_safe = True

                        if is_safe:
                            reason_not_safe = None
                        else:
                            reason_not_safe = f'Volume attached to host {hostname}'
                    else:
                        is_safe = True  # Default to safe if no callback provided
                        reason_not_safe = None

                manageable_vols.append({
                    'reference': {'name': vol_name},
                    'size': size_gb,
                    'safe_to_manage': is_safe,
                    'reason_not_safe': reason_not_safe,
                    'cinder_id': cinder_id,
                })

        return manageable_vols

    @staticmethod
    def get_manageable_snapshots_utility(client_obj, already_managed, cinder_cpg):
        """Get manageable snapshots utility.
        
        Args:
            client_obj: 3PAR client instance
            already_managed: Dict of already managed snapshots
            cinder_cpg: Cinder CPG name
            
        Returns:
            list: List of manageable snapshots
        """
        cpg_volumes = []

        body = client_obj.getVolumes()
        all_volumes = body['members']
        for vol in all_volumes:
            cpg = vol.get('userCPG')
            if cpg == cinder_cpg:
                cpg_volumes.append(vol)

        manageable_snaps = []

        for vol in cpg_volumes:
            size_gb = int(vol['sizeMiB'] / 1024)
            snapshots = client_obj.getSnapshotsOfVolume(cinder_cpg, vol['name'])
            
            for snap_name in snapshots:
                if snap_name in already_managed:
                    is_safe = False
                    reason_not_safe = 'Snapshot already managed'
                    cinder_snap_id = already_managed[snap_name]
                else:
                    is_safe = True
                    reason_not_safe = None
                    cinder_snap_id = None

                manageable_snaps.append({
                    'reference': {'name': snap_name},
                    'size': size_gb,
                    'safe_to_manage': is_safe,
                    'reason_not_safe': reason_not_safe,
                    'cinder_id': cinder_snap_id,
                    'source_reference': {'name': vol['name']},
                })

        return manageable_snaps

    @staticmethod
    def create_volume_utility(client_obj, volume, type_info, comments, vvs_name, qos, 
                            flash_cache, compression, consis_group_snap_type, cg_id, 
                            group, hpe_tiramisu, api_version, log_callback=None):
        """Create volume utility.
        
        Args:
            client_obj: 3PAR client instance
            volume: Volume object
            type_info: Volume type information
            comments: Volume comments
            vvs_name: Volume set name
            qos: QoS settings
            flash_cache: Flash cache policy
            compression: Compression policy
            consis_group_snap_type: Consistency group snapshot type flag
            cg_id: Consistency group ID
            group: Group object
            hpe_tiramisu: HPE Tiramisu flag
            api_version: API version
            log_callback: Optional logging callback
            
        Returns:
            dict: Creation result with success flag and model update info
        """
        import json
        result = {'success': False, 'replication_flag': False, 'hpe_tiramisu': hpe_tiramisu}
        
        try:
            # Extract type info
            cpg = type_info['cpg']
            snap_cpg = type_info['snap_cpg']
            tpvv = type_info['tpvv']
            tdvv = type_info['tdvv']
            volume_type = type_info['volume_type']

            if cg_id and consis_group_snap_type:
                from .client import HPE3ParClient
                vvs_name = HPE3ParClient.get_3par_vvs_name(cg_id)

            type_id = volume.get('volume_type_id', None)
            if type_id is not None:
                comments['volume_type_name'] = volume_type.get('name')
                comments['volume_type_id'] = type_id
                if vvs_name is not None:
                    comments['vvs'] = vvs_name
                else:
                    comments['qos'] = qos

            extras = {'comment': json.dumps(comments), 'tpvv': tpvv}

            if log_callback:
                log_callback(f"API_VERSION: {api_version}")

            # Version-specific settings
            if hasattr(client_obj, 'API_VERSION_2023') and api_version < client_obj.API_VERSION_2023:
                extras['snapCPG'] = snap_cpg

            # Only set the dedup option if the backend supports it
            if hasattr(client_obj, 'DEDUP_API_VERSION') and api_version >= client_obj.DEDUP_API_VERSION:
                extras['tdvv'] = tdvv

            from .client import HPE3ParClient
            volume_name = HPE3ParClient.get_3par_vol_name(volume['id'])
            capacity = client_obj.capacity_from_size(volume['size'])

            if compression is not None:
                extras['compression'] = compression

            # Create the volume
            client_obj.createVolume(volume_name, cpg, capacity, extras)

            result['volume_name'] = volume_name
            result['cpg'] = cpg
            result['success'] = True

        except Exception as ex:
            if 'HTTPConflict' in str(type(ex)):
                result['error'] = f"Volume ({volume_name}) already exists on array"
                result['error_type'] = 'Duplicate'
            elif 'HTTPBadRequest' in str(type(ex)):
                result['error'] = f"Bad request: {getattr(ex, 'get_description', lambda: str(ex))()}"
                result['error_type'] = 'Invalid'
                result['error_type'] = 'CinderException'

        return result

    def delete_volume_utility(self, client, volume, get_3par_vol_name_callback, 
                             is_online_physical_copy_callback, log_callback):
        """Complete utility for volume deletion with comprehensive error handling.
        
        Args:
            client: 3PAR client instance
            volume: Volume to delete
            get_3par_vol_name_callback: Callback to get 3PAR volume name
            is_online_physical_copy_callback: Callback to check online copy
            log_callback: Logging callback
            
        Returns:
            dict: Result with success status and volume name
        """
        from oslo_utils import excutils
        from cinder import exception
        from cinder.i18n import _
        
        result = {'success': False, 'volume_name': None}
        
        try:
            vol_id = volume.id
            name_id = volume.get('_name_id')
            log_callback(f"DELETE volume vol_id: {vol_id}, name_id: {name_id}")

            # Get volume name with special handling for migration status
            if (client.volume_of_replicated_type(volume, hpe_tiramisu_check=True)
               and volume.get('migration_status') == 'deleting'):
                # Use volume id instead of name_id for replication migration
                volume_name = client.encode_name(volume.id)
                volume_name = "osv-" + volume_name
            else:
                volume_name = get_3par_vol_name_callback(volume)
            
            result['volume_name'] = volume_name
            log_callback(f"volume_name: {volume_name}")

            # Check for replication handling
            if client.volume_of_replicated_type(volume, hpe_tiramisu_check=True):
                log_callback("volume is of replicated_type")
                replication_status = volume.get('replication_status', None)
                log_callback(f"replication_status: {replication_status}")
                if replication_status:
                    result['success'] = True
                    result['requires_replication_cleanup'] = True
                    result['replication_status'] = replication_status
                    return result

            # Try to delete the volume with comprehensive error handling
            try:
                client.deleteVolume(volume_name)
                result['success'] = True
            except Exception as ex:
                error_code = getattr(ex, 'get_code', lambda: None)()
                
                if 'HTTPBadRequest' in str(type(ex)) and error_code == 29:
                    if is_online_physical_copy_callback(volume_name):
                        log_callback(f"Found an online copy for {volume_name}")
                        client.stopOnlinePhysicalCopy(volume_name)
                        result['success'] = True
                    else:
                        result['error'] = str(ex)
                elif 'HTTPConflict' in str(type(ex)):
                    if error_code == 34:
                        # Volume is part of a volume set - requires special handling
                        result['requires_vvset_cleanup'] = True
                        result['success'] = True
                    elif error_code == 151:
                        if is_online_physical_copy_callback(volume_name):
                            log_callback(f"Found an online copy for {volume_name}")
                            client.stopOnlinePhysicalCopy(volume_name)
                            result['success'] = True
                        else:
                            # Volume is busy - requires retry logic
                            result['requires_retry'] = True
                            result['error'] = "Volume is currently busy and cannot be deleted"
                    elif error_code == 32:
                        # Volume has children - requires temp snapshot cleanup
                        result['has_children'] = True
                        try:
                            snaps = client.getVolumeSnapshots(volume_name)
                            temp_snaps = [snap for snap in snaps if snap.startswith('tss-')]
                            if temp_snaps:
                                result['temp_snapshots'] = temp_snaps
                                result['success'] = True
                            else:
                                result['error'] = "Volume has children and cannot be deleted"
                        except Exception:
                            result['error'] = "Volume has children and cannot be deleted"
                    else:
                        result['error'] = getattr(ex, 'get_description', lambda: str(ex))()
                elif 'HTTPNotFound' in str(type(ex)):
                    # Volume not found - treat as success for cleanup
                    log_callback(f"Delete volume id not found. Removing from cinder: {volume['id']} Ex: {ex}")
                    result['success'] = True
                elif 'HTTPForbidden' in str(type(ex)):
                    result['error'] = getattr(ex, 'get_description', lambda: str(ex))()
                    result['error_type'] = 'NotAuthorized'
                else:
                    result['error'] = str(ex)
                    
        except Exception as ex:
            result['error'] = str(ex)

        return result

    def create_cloned_volume_utility(self, client, volume, src_vref, 
                                   get_3par_vol_name_callback, get_volume_settings_callback,
                                   create_volume_callback, get_model_update_callback,
                                   log_callback):
        """Complete utility for cloned volume creation.
        
        Args:
            client: 3PAR client instance
            volume: New volume to create
            src_vref: Source volume reference
            get_3par_vol_name_callback: Callback to get 3PAR volume name
            get_volume_settings_callback: Callback to get volume type settings
            create_volume_callback: Callback to create volume
            get_model_update_callback: Callback to get model update
            log_callback: Logging callback
            
        Returns:
            dict: Result with success status and model update
        """
        from oslo_utils import units
        from cinder import exception
        from cinder.i18n import _
        import json
        
        result = {'success': False, 'model_update': None}
        
        try:
            vol_name = get_3par_vol_name_callback(volume)
            src_vol_name = get_3par_vol_name_callback(src_vref)
            back_up_process = False
            vol_chap_enabled = False
            hpe_tiramisu = False

            # Check for CHAP enabled volume
            if hasattr(client, '_client_conf') and client._client_conf.get('hpe3par_iscsi_chap_enabled'):
                try:
                    vol_chap_enabled = client.getVolumeMetaData(
                        src_vol_name, 'HPQ-cinder-CHAP-name')['value']
                except:
                    log_callback(f"CHAP is not enabled on volume {src_vref['id']}")
                    vol_chap_enabled = False

            # Check for backup process
            if str(src_vref['status']) == 'backing-up':
                back_up_process = True

            # Determine if we can use online copy
            can_use_online_copy = (
                volume['size'] == src_vref['size'] and 
                not (back_up_process and vol_chap_enabled) and 
                not client.volume_of_replicated_type(volume, hpe_tiramisu_check=True)
            )

            if can_use_online_copy:
                log_callback("Creating a clone of volume, using online copy.")
                
                type_info = get_volume_settings_callback(volume)
                snapshot = client.create_temp_snapshot(src_vref)
                cpg = type_info['cpg']
                qos = type_info['qos']
                vvs_name = type_info['vvs_name']
                flash_cache = client.get_flash_cache_policy(type_info['hpe3par_keys'])
                compression_val = client.get_compression_policy(type_info['hpe3par_keys'])

                # Prepare comment if supported
                comment_line = None
                api_version = getattr(client, 'API_VERSION', 0)
                if api_version >= 40600000:
                    comments = {
                        'volume_id': volume['id'],
                        'name': volume['name'],
                        'type': 'OpenStack'
                    }
                    
                    volume_type = type_info.get('volume_type')
                    type_id = volume.get('volume_type_id')
                    if type_id and volume_type:
                        comments['volume_type_name'] = volume_type.get('name')
                        comments['volume_type_id'] = type_id
                        if vvs_name:
                            comments['vvs'] = vvs_name
                        else:
                            comments['qos'] = qos

                    display_name = volume.get('display_name')
                    if display_name:
                        comments['display_name'] = display_name

                    comment_line = json.dumps(comments)

                # Perform online copy
                client.copy_volume(
                    snapshot['name'], vol_name, cpg=cpg,
                    snap_cpg=type_info['snap_cpg'],
                    tpvv=type_info['tpvv'],
                    tdvv=type_info['tdvv'],
                    compression=compression_val,
                    comment=comment_line
                )

                # Add to volume set if needed
                if qos or vvs_name or flash_cache is not None:
                    try:
                        # This would need to be handled by the calling code
                        result['requires_volume_set_addition'] = True
                        result['volume_set_params'] = {
                            'volume': volume,
                            'vol_name': vol_name,
                            'cpg': cpg,
                            'vvs_name': vvs_name,
                            'qos': qos,
                            'flash_cache': flash_cache
                        }
                    except Exception as ex:
                        # Clean up on failure
                        try:
                            client.deleteVolume(vol_name)
                        except:
                            pass
                        result['error'] = f"Failed to add volume '{vol_name}' to vvset '{vvs_name}' because '{str(ex)}'"
                        return result

                if client.volume_of_hpe_tiramisu_type(volume):
                    hpe_tiramisu = True

                result['model_update'] = get_model_update_callback(
                    volume['host'], cpg, replication=False,
                    provider_location=client.id, hpe_tiramisu=hpe_tiramisu
                )
                result['success'] = True
                
            else:
                # Non-online copy - create volume first then copy
                log_callback("Creating a clone of volume, using non-online copy.")
                
                model_update = create_volume_callback(volume, perform_replica=False)
                
                optional = {'priority': 1}
                body = client.copyVolume(src_vol_name, vol_name, None, optional=optional)
                task_id = body['taskid']

                task_status = client.wait_for_task_completion(task_id)
                if task_status['status'] is not client.TASK_DONE:
                    result['error'] = f'Copy volume task failed: create_cloned_volume id={volume["id"]}, status={task_status}'
                    return result
                else:
                    log_callback(f'Copy volume completed: create_cloned_volume: id={volume["id"]}.')

                # Handle replication if needed
                replication_flag = False
                if (client.volume_of_replicated_type(volume, hpe_tiramisu_check=True)):
                    # Replication setup would be handled by calling code
                    result['requires_replication_setup'] = True
                    replication_flag = True
                    type_info = get_volume_settings_callback(volume)
                    cpg = type_info['cpg']
                    model_update = get_model_update_callback(
                        volume['host'], cpg, replication=True,
                        provider_location=client.id, hpe_tiramisu=hpe_tiramisu
                    )

                result['model_update'] = model_update
                result['success'] = True

        except Exception as ex:
            error_type = str(type(ex))
            if 'HTTPForbidden' in error_type:
                result['error_type'] = 'NotAuthorized'
            elif 'HTTPNotFound' in error_type:
                result['error_type'] = 'NotFound'
            else:
                result['error_type'] = 'CinderException'
            result['error'] = str(ex)

        return result

    def create_volume_from_snapshot_utility(self, client, volume, snapshot, 
                                          get_3par_vol_name_callback, get_type_info_callback,
                                          log_callback, snap_name=None, vvs_name=None):
        """Complete utility for creating volume from snapshot.
        
        Args:
            client: 3PAR client instance
            volume: Volume to create
            snapshot: Source snapshot
            get_3par_vol_name_callback: Callback to get 3PAR volume name
            get_type_info_callback: Callback to get type info
            log_callback: Logging callback
            snap_name: Optional snapshot name
            vvs_name: Optional volume set name
            
        Returns:
            dict: Result with success status and model update
        """
        from oslo_utils import units
        from cinder import exception
        from cinder.i18n import _
        import json
        import pprint
        
        result = {'success': False, 'model_update': {}}
        
        try:
            log_callback(f"Create Volume from Snapshot\n{pprint.pformat(volume['display_name'])}\n{pprint.pformat(snapshot['display_name'])}")

            if not snap_name:
                snap_name = client.get_3par_snap_name(snapshot['id'])
            volume_name = get_3par_vol_name_callback(volume)

            extra = {
                'volume_id': volume['id'],
                'snapshot_id': snapshot['id']
            }
            client.add_name_id_to_comment(extra, volume)

            type_id = volume.get('volume_type_id')
            hpe3par_keys, qos, _volume_type, vvs = get_type_info_callback(type_id)
            if vvs:
                vvs_name = vvs

            name = volume.get('display_name')
            if name:
                extra['display_name'] = name

            description = volume.get('display_description')
            if description:
                extra['description'] = description

            optional = {
                'comment': json.dumps(extra),
                'readOnly': False
            }

            client.createSnapshot(volume_name, snap_name, optional)

            # Handle convert_to_base
            convert_to_base = client._get_boolean_key_value(hpe3par_keys, 'convert_to_base')
            log_callback(f"convert_to_base: {convert_to_base}")

            growth_size = volume['size'] - snapshot['volume_size']
            log_callback(f"growth_size: {growth_size}")
            
            if growth_size > 0 or convert_to_base:
                log_callback(f'Converting to base volume type: {volume["id"]}.')
                result['requires_convert_to_base'] = True
            else:
                log_callback("volume is created as child of snapshot")

            if growth_size > 0:
                try:
                    growth_size_mib = growth_size * units.Gi / units.Mi
                    log_callback(f'Growing volume: {volume["id"]} by {growth_size} GiB.')
                    client.growVolume(volume_name, growth_size_mib)
                except Exception as ex:
                    log_callback(f"Error extending volume {volume['id']}. Ex: {ex}")
                    # Clean up on failure
                    try:
                        client.deleteVolume(volume_name)
                    except:
                        pass
                    result['error'] = str(ex)
                    return result

            # Handle volume set addition
            flash_cache = client.get_flash_cache_policy(hpe3par_keys)
            if qos or vvs_name or flash_cache is not None:
                cpg_names = client._get_key_value(hpe3par_keys, 'cpg', [])
                if cpg_names:
                    result['requires_volume_set_addition'] = True
                    result['volume_set_params'] = {
                        'volume': volume,
                        'volume_name': volume_name,
                        'cpg': cpg_names[0],
                        'vvs_name': vvs_name,
                        'qos': qos,
                        'flash_cache': flash_cache
                    }

            # Handle special volume types
            if client.volume_of_hpe_tiramisu_type(volume):
                result['model_update']['provider_location'] = client.id

            # Handle replication
            if (client.volume_of_replicated_type(volume, hpe_tiramisu_check=True)):
                result['requires_replication_setup'] = True
                result['model_update']['replication_status'] = 'enabled'
                result['model_update']['provider_location'] = client.id

            result['success'] = True

        except Exception as ex:
            error_type = str(type(ex))
            if 'HTTPForbidden' in error_type:
                result['error_type'] = 'NotAuthorized'
            elif 'HTTPNotFound' in error_type:
                result['error_type'] = 'NotFound'
            else:
                result['error_type'] = 'CinderException'
            result['error'] = str(ex)

        return result

    def create_snapshot_utility(self, client, snapshot, get_3par_vol_name_callback, 
                               config, log_callback):
        """Complete utility for snapshot creation.
        
        Args:
            client: 3PAR client instance
            snapshot: Snapshot to create
            get_3par_vol_name_callback: Callback to get 3PAR volume name
            config: Configuration object
            log_callback: Logging callback
            
        Returns:
            dict: Result with success status
        """
        from cinder import exception
        from cinder.i18n import _
        import json
        import pprint
        
        result = {'success': False}
        
        try:
            log_callback(f"Create Snapshot\n{pprint.pformat(snapshot)}")

            snap_name = client.get_3par_snap_name(snapshot['id'])
            vol_name = get_3par_vol_name_callback(snapshot['volume'])

            extra = {
                'volume_name': snapshot['volume_name'],
                'volume_id': snapshot.get('volume_id')
            }
            client.add_name_id_to_comment(extra, snapshot['volume'])

            try:
                extra['display_name'] = snapshot['display_name']
            except (AttributeError, KeyError):
                pass

            try:
                extra['description'] = snapshot['display_description']
            except (AttributeError, KeyError):
                pass

            optional = {
                'comment': json.dumps(extra),
                'readOnly': True
            }
            
            if hasattr(config, 'hpe3par_snapshot_expiration') and config.hpe3par_snapshot_expiration:
                optional['expirationHours'] = int(config.hpe3par_snapshot_expiration)

            if hasattr(config, 'hpe3par_snapshot_retention') and config.hpe3par_snapshot_retention:
                optional['retentionHours'] = int(config.hpe3par_snapshot_retention)

            client.createSnapshot(snap_name, vol_name, optional)
            result['success'] = True

        except Exception as ex:
            error_type = str(type(ex))
            if 'HTTPForbidden' in error_type:
                result['error_type'] = 'NotAuthorized'
            elif 'HTTPNotFound' in error_type:
                result['error_type'] = 'NotFound'
            else:
                result['error_type'] = 'CinderException'
            result['error'] = str(ex)

        return result

    def delete_snapshot_utility(self, client, snapshot, log_callback):
        '''Complete utility for snapshot deletion with error handling.
        
        Args:
            client: 3PAR client instance
            snapshot: Snapshot to delete
            log_callback: Logging callback
            
        Returns:
            dict: Result with success status
        '''
        from cinder import exception
        from cinder.i18n import _
        import pprint
        
        result = {'success': False}
        
        try:
            log_callback(f'Delete Snapshot id {snapshot["id"]} {pprint.pformat(snapshot)}')

            snap_name = client.get_3par_snap_name(snapshot['id'])
            
            try:
                client.deleteVolume(snap_name)
                result['success'] = True
            except Exception as ex:
                error_type = str(type(ex))
                
                if 'HTTPForbidden' in error_type:
                    result['error_type'] = 'NotAuthorized'
                    result['error'] = str(ex)
                elif 'HTTPNotFound' in error_type:
                    # Treat as success for cleanup
                    log_callback(f'Delete Snapshot id not found. Removing from cinder: {snapshot["id"]} Ex: {ex}')
                    result['success'] = True
                elif 'HTTPConflict' in error_type:
                    error_code = getattr(ex, 'get_code', lambda: None)()
                    if error_code == 32:
                        # Snapshot has children - handle temp snapshots and volumes
                        result['has_children'] = True
                        try:
                            snaps = client.getVolumeSnapshots(snap_name)
                            temp_snaps = [snap for snap in snaps if snap.startswith('tss-')]
                            child_volumes = [snap for snap in snaps if snap.startswith('osv-')]
                            
                            if temp_snaps:
                                result['temp_snapshots'] = temp_snaps
                            if child_volumes:
                                result['child_volumes'] = child_volumes
                                result['snap_name'] = snap_name
                            
                            result['success'] = True
                        except Exception:
                            result['error'] = 'Snapshot has children and cannot be deleted'
                    else:
                        result['error'] = getattr(ex, 'get_description', lambda: str(ex))()
                        result['error_type'] = 'SnapshotIsBusy'
                else:
                    result['error'] = str(ex)
                    
        except Exception as ex:
            result['error'] = str(ex)

        return result
