# (c) Copyright 2012-2015 Hewlett Packard Development Company, L.P.
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
""" HP3PAR REST Client.

.. module: client
.. moduleauthor: Walter A. Boring IV
.. moduleauthor: Kurt Martin

:Author: Walter A. Boring IV
:Description: This is the 3PAR Client that talks to 3PAR's REST WSAPI Service.
It provides the ability to provision 3PAR volumes, VLUNs, CPGs.  This version
also supports running actions on the 3PAR that use SSH.

This client requires and works with 3PAR InForm 3.1.3 MU1 firmware

"""
import re
import time
import uuid

try:
    # For Python 3.0 and later
    from urllib.parse import quote
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import quote

from hp3parclient import exceptions, http, ssh


class HP3ParClient(object):

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
    HP3PAR_WS_MIN_BUILD_VERSION = 30103230
    HP3PAR_WS_MIN_BUILD_VERSION_DESC = '3.1.3 MU1'

    # Minimum build version needed for VLUN query support.
    HP3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY = 30201292
    HP3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY_DESC = '3.2.1 MU2'

    VLUN_TYPE_EMPTY = 1
    VLUN_TYPE_PORT = 2
    VLUN_TYPE_HOST = 3
    VLUN_TYPE_MATCHED_SET = 4
    VLUN_TYPE_HOST_SET = 5

    VLUN_MULTIPATH_UNKNOWN = 1
    VLUN_MULTIPATH_ROUND_ROBIN = 2
    VLUN_MULTIPATH_FAILOVER = 3

    CPG_RAID_R0 = 1     # RAID 0
    CPG_RAID_R1 = 2     # RAID 1
    CPG_RAID_R5 = 3     # RAID 5
    CPG_RAID_R6 = 4     # RAID 6

    CPG_HA_PORT = 1     # Support failure of a port.
    CPG_HA_CAGE = 2     # Support failure of a drive cage.
    CPG_HA_MAG = 3      # Support failure of a drive magazine.

    # Lowest numbered available chunklets, where transfer rate is the fastest.
    CPG_CHUNKLET_POS_PREF_FIRST = 1
    # Highest numbered available chunklets, where transfer rate is the slowest.
    CPG_CHUNKLET_POS_PREF_LAST = 2

    CPG_DISK_TYPE_FC = 1        # Fibre Channel
    CPG_DISK_TYPE_NL = 2        # Near Line
    CPG_DISK_TYPE_SSD = 3       # SSD

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

    def __init__(self, api_url, debug=False, secure=False):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(self.api_url, secure=secure)
        api_version = None
        self.ssh = None
        self.vlun_query_supported = False

        self.debug_rest(debug)

        try:
            api_version = self.getWsApiVersion()
        except Exception as ex:
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
           api_version['build'] < self.HP3PAR_WS_MIN_BUILD_VERSION):
            raise exceptions.UnsupportedVersion(
                'Invalid 3PAR WS API, requires version, %s' %
                self.HP3PAR_WS_MIN_BUILD_VERSION_DESC)

        # Check for VLUN query support.
        if (api_version['build'] >=
           self.HP3PAR_WS_MIN_BUILD_VERSION_VLUN_QUERY):
            self.vlun_query_supported = True

    def setSSHOptions(self, ip, login, password, port=22,
                      conn_timeout=None, privatekey=None,
                      **kwargs):
        """Set SSH Options for ssh calls.

        This is used to set the SSH credentials for calls
        that use SSH instead of REST HTTP.

        """
        self.ssh = ssh.HP3PARSSHClient(ip, login, password, port,
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
        self.http.authenticate(username, password, optional)

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
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - volume doesn't exist

        """
        response, body = self.http.get('/volumes/%s' % name)
        return body

    def createVolume(self, name, cpgName, sizeMiB, optional=None):
        """Create a new volume.

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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Invalid Parameter
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - TOO_LARGE - Volume size above limit
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not Enough space is available
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_SV - Volume Exists already

        """
        info = {'name': name, 'cpg': cpgName, 'sizeMiB': sizeMiB}
        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/volumes', body=info)
        return body

    def deleteVolume(self, name):
        """Delete a volume.

        :param name: the name of the volume
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - RETAINED - Volume retention time has not expired
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - HAS_RO_CHILD - Volume has read-only child
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - HAS_CHILD - The volume has a child volume
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - IN_USE - The volume is in use by VV set, VLUN, etc

        """
        response, body = self.http.delete('/volumes/%s' % name)
        return body

    def modifyVolume(self, name, volumeMods):
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WARN_GT_LIMIT - Allocation warning level is higher than
            the limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_USR_ALRT_NON_TPVV - User space allocation alerts are
            valid only with a TPVV.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_RETAIN_GT_EXPIRE - Retention time is greater than
            expiration time.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_VV_POLICY - Invalid policy specification (for example,
            caching or system is set to true).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: string length exceeds
            limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TIME - Invalid time specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_MODIFY_USR_CPG_TPVV - usr_cpg cannot be modified
            on a TPVV.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - UNLICENSED_FEATURE - Retention time cannot be modified on a
            system without the Virtual Lock license.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN_SAME_DOMAIN - Snap CPG is not in the same domain as
            the user CPG.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - Cannot modify a peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPInternalServerError`
            - INT_SERV_ERR - Metadata of the VV is corrupted.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - Cannot modify retention time on a
            system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Cannot modify an internal
            volume
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_NOT_DEFINED_ALL_NODES - Cannot modify a
            volume until the volume is defined on all volumes.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_ONLINE_COPY_IN_PROGRESS - Cannot modify a
            volume when an online copy for that volume is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Cannot modify a
            volume in the middle of a conversion operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INVALID_OPERATION_VV_SNAPSPACE_NOT_MOVED_TO_CPG - Snapshot space
            of a volume needs to be moved to a CPG before the user space.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_ACCOUNTING_IN_PROGRESS - The volume
            cannot be renamed until snapshot accounting has finished.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_ZERO_DETECT_TPVV - The zero_detect policy can be
            used only on TPVVs.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_CPG_ON_SNAPSHOT - CPG cannot be assigned to a
            snapshot.

        """
        response = self.http.put('/volumes/%s' % name, body=volumeMods)
        return response

    def growVolume(self, name, amount):
        """Grow an existing volume by 'amount' Mebibytes.

        :param name: the name of the volume
        :type name: str
        :param amount: the additional size in MiB to add, rounded up to the
                       next chunklet size (e.g. 256 or 1000 MiB)
        :type amount: int

        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_UNSUPPORTED_VV_TYPE - Invalid operation: Cannot
            grow this type of volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_TUNE_IN_PROGRESS - Invalid operation: Volume
            tuning is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: String length exceeds
            limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_VV_GROW_SIZE - Invalid grow size.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NEW_SIZE_EXCEEDS_CPG_LIMIT - New volume size exceeds CPG limit
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - This operation is not allowed
            on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV
            conversion is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_COPY_IN_PROGRESS - Invalid operation:
            online copy is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is
            in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_SIZE_CANNOT_REDUCE - New volume size is smaller than the
            current size.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NEW_SIZE_EXCEEDS_LIMITS - New volume size exceeds the limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_SA_SD_SPACE_REMOVED - Invalid operation: Volume
            SA/SD space is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_IS_BUSY - Invalid operation: Volume is currently
            busy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_IS_PCOPY - Invalid operation: Volume is a
            physical copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Invalid operation: Volume
            promotion is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PARENT_OF_PCOPY - Invalid operation: Volume is
            the parent of physical copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Insufficent space for requested operation.

        """
        info = {'action': self.GROW_VOLUME,
                'sizeMiB': amount}

        response, body = self.http.put('/volumes/%s' % name, body=info)
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid
            range(1-3).
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a
            base volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved
            in a remote copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the
            same as the parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a
            read-only snapshot.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the
            base volume of a parent volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a
            conversion operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must
            allow snapshots.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume
            for the volume is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of
            the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a
            peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the
            normal state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has
            a physical copy in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the
            destination volume has failed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent
            volume is larger than the size of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VVCOPY - Physical copy not found.

        """
        # Virtual volume sets are not supported with the -online option
        parameters = {'destVolume': dest_name,
                      'destCPG': dest_cpg}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action': 'createPhysicalCopy',
                'parameters': parameters}

        response, body = self.http.post('/volumes/%s' % src_name, body=info)
        return body

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
            msg = "Couldn't find the copy task for '%s'" % name
            raise exceptions.HTTPNotFound(error={'desc': msg})
        else:
            task_id = task[0]

        # now stop the copy
        if task_id is not None:
            cmd = ['canceltask', '-f', task_id]
            self._run(cmd)
        else:
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
            snap1 = self.getVolume(vol['copyOf'])
            snap2 = self.getVolume(snap1['copyOf'])
            self.deleteVolume(name)
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BELOW_RANGE - Bad Request Task ID must be a positive
            value.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - Bad Request Task ID is too large.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_TASK - Task with the specified task ID does not
            exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - Task ID is not an integer.

        """
        response, body = self.http.get('/tasks/%s' % taskId)
        return body

    def _findTask(self, name, active=True):
        cmd = ['showtask']
        if active:
            cmd.append('-active')
        cmd.append(name)
        result = self._run(cmd)
        if result and len(result) == 1:
            if 'No tasks' in result[0]:
                return None
        elif len(result) == 2:
            return result[1].split(',')
        return result

    def _convert_cli_output_to_collection_like_wsapi(self, cli_output):
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid
            range(1-3).
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a
            base volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved
            in a remote copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the
            same as the parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a
            read-only snapshot.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the
            base volume of a parent volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a
            conversion operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must
            allow snapshots.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume
            for the volume is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of
            the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a
            peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the
            normal state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency
            error.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has
            a physical copy in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the
            destination volume has failed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent
            volume is larger than the size of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
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
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain
            to perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - MEMBER_NOT_IN_SET - The object is not part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain
            to perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Invalid input (parameters cannot be
            present at the same time).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Name not specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - FCWWNs and iSCSINames are both
            specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Host name, domain name, or iSCSI name
            is too long.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EMPTY_STR - Input string (for domain name, iSCSI name,
            etc.) is empty.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Any error from host-name or domain-name
            parsing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI
            names are specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - The length of WWN is not 16. WWN
            specification contains non-hexadecimal digit.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_PATH - host WWN/iSCSI name already used by another host
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_HOST - host name is already used.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Missing host name.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Both iSCSINames & FCWWNs are
            specified. (lot of other possibilities)
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ONE_REQUIRED - iSCSINames or FCWwns missing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ONE_REQUIRED - No path operation specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_ENUM_VALUE - Invalid enum value.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Required fields missing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Host descriptor argument length, new
            host name, or iSCSI name is too long.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Error parsing host or iSCSI name.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_HOST - New host name is already used.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - Host to be modified does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI
            names are specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_WRONG_TYPE - Input value is of the wrong type.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_PATH - WWN or iSCSI name is already claimed by other
            host.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_BAD_LENGTH - CHAP hex secret length is not 16 bytes, or
            chap ASCII secret length is not 12 to 16 characters.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NO_INITIATOR_CHAP - Setting target CHAP without initiator CHAP.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CHAP - Remove non-existing CHAP.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - NON_UNIQUE_CHAP_SECRET - CHAP secret is not unique.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXPORTED_VLUN - Setting persona with active export; remove a host
            path on an active export.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - NON_EXISTENT_PATH - Remove a non-existing path.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - LUN_HOSTPERSONA_CONFLICT - LUN number and persona capability
            conflict.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_PATH - Duplicate path specified.

        """
        response = self.http.put('/hosts/%s' % name, body=mod_request)
        return response

    def deleteHost(self, name):
        """Delete a Host.

        :param name: Host Name
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            -  IN_USE - The HOST Cannot be removed because it's in use.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT - Invalid URI syntax.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPInternalServerError`
            - INTERNAL_SERVER_ERR - Internal server error.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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
    def getPorts(self):
        """Get the list of ports on the 3PAR.

        :returns: list of Ports

        """
        response, body = self.http.get('/ports')
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
        response, body = self.http.get('/cpgs')
        return body

    def getCPG(self, name):
        """Get information about a CPG.

        :param name: The name of the CPG to find
        :type name: str

        :returns: cpg dict
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            -  NON_EXISTENT_CPG - CPG doesn't exist

        """
        response, body = self.http.get('/cpgs/%s' % name)
        return body

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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT Invalid URI Syntax.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - NON_EXISTENT_DOMAIN - Domain doesn't exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - NO_SPACE - Not Enough space is available.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - BAD_CPG_PATTERN  A Pattern in a CPG specifies illegal values.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_CPG - CPG Exists already

        """
        info = {'name': name}
        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/cpgs', body=info)
        return body

    def deleteCPG(self, name):
        """Delete a CPG.

        :param name: CPG Name
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_CPG - CPG Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            -  IN_USE - The CPG Cannot be removed because it's in use.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        if lun:
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Incomplete VLUN info. Missing
            volumeName or lun, or both hostname and port.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PORT_SELECTION - Specified port is invalid.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_RANGE - The LUN specified exceeds expected
            range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VLUN - The VLUN does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_PORT - The port does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - PERM_DENIED - Permission denied
        """

        vlun = "%s,%s" % (volumeName, lunID)

        if hostname:
            vlun += ",%s" % hostname

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

        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - Internal inconsistency error in vol
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - Illegal op on system vol
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to
            perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal
            inconsistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_HOST - The host does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXPORTED_VLUN - The host set has exported VLUNs. The VV set was
            exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - MEMBER_NOT_IN_SET - The object is not part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to
            perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - The volume has an internal
            inconsistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a
            system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed
            on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_PARAM_CONFLICT - Invalid input (parameters cannot be
            present at the same time).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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
                     "VV Name Patterns" in the HP 3PAR Command Line Interface
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INVALID_INPUT_VV_PATTERN - Invalid volume pattern specified
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_SET - The set does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - EMPTY_SET - The set is empty
        :raises: :class:`~hp3parclient.exceptions.HTTPServiceUnavailable`
            - VV_LIMIT_REACHED - Maximum number of volumes reached
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The storage volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IS_BEING_REMOVED - The volume is being removed
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_READONLY_TO_READONLY_SNAP - Creating a
            read-only copy from a read-only volume is not permitted
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - NO_SNAP_CPG - No snapshot CPG has been configured for the volume
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_SNAP_PARENT_SAME_BASE - Two parent
            snapshots share thesame base volume
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS - Invalid
            operation. Online copyis in progress
        :raises: :class:`~hp3parclient.exceptions.HTTPServiceUnavailable`
            - VV_ID_LIMIT_REACHED - Max number of volumeIDs has been reached
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOLUME - The volume does not exists
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_NOT_STARTED - Volume is not started
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_UNAVAILABLE - The volume is not accessible
        :raises: :class:`~hp3parclient.exceptions.HTTPServiceUnavailable`
            - SNAPSHOT_LIMIT_REACHED - Max number of snapshots has been reached
        :raises: :class:`~hp3parclient.exceptions.HTTPServiceUnavailable`
            - CPG_ALLOCATION_WARNING_REACHED - The CPG has reached the
            allocation warning
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV
            conversion is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is
            in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_PEER_VOLUME - Cannot modify a peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the
            target of an online copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_INTERNAL_VOLUME - Illegal op on internal vol
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict`
            - EXISTENT_ID - An ID exists
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
            - VV_IN_INCONSISTENT_STATE - Internal inconsistency error in vol
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_RETAIN_GT_EXPIRE - Retention time is greater than
            expiration time.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_TIME - Invalid time specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
           - NON_EXISTENT_QOS_RULE - QoS rule does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected
          range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
          - NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit
          should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit
          should be greater than the mimimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
          - INV_INPUT_BELOW_RANGE - I/O-per-second limit is below range.
          Bandwidth limit is below range.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected
            range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_IO_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit
            should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit
            should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            INV_INPUT_BELOW_RANGE - I/O-per-second limit is below
            range. Bandwidth limit is below range.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` -
                        NON_EXISTENT_QOS_RULE - QoS rule does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` -
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


        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_EXCEEDS_LENGTH - Invalid input: string length exceeds
            limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_MISSING_REQUIRED - Required fields missing
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_UNREC_NAME - Unrecognized name
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest`
            - INV_INPUT_ILLEGAL_CHAR - Illegal character in input
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
            - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound`
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

        :raises: :class:`~hp3parclient.exceptions.SrstatldException`
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
                                               + "short")
        elif len(output[-1].split(',')) < 16:
            raise exceptions.SrstatldException("srstatld output last line "
                                               + "invalid")
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
