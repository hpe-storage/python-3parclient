# (c) Copyright 2012-2014 Hewlett Packard Development Company, L.P.
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
"""
HP3PAR REST Client

.. module: HP3ParClient
.. moduleauthor: Walter A. Boring IV
.. moduleauthor: Kurt Martin

:Author: Walter A. Boring IV
:Author: Kurt Martin
:Description: This is the 3PAR Client that talks to 3PAR's REST WSAPI Service
and to the CLIQ SSH interface.
It provides the ability to provision 3PAR volumes, VLUNs, CPGs.

This client requires and works with 3PAR InForm 3.1.3 firmware

"""
import re
import urllib2
from hp3parclient import exceptions, http, ssh


class HP3ParClient:
    """
    The 3PAR REST API Client

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080/api/v1
    :type api_url: str

    """

    PORT_MODE_TARGET = 2
    PORT_MODE_INITIATOR = 3
    PORT_MODE_PEER = 4

    PORT_TYPE_HOST = 1
    PORT_TYPE_DISK = 2
    PORT_TYPE_FREE = 3
    PORT_TYPE_RCIP = 6
    PORT_TYPE_ISCSI = 7

    PORT_PROTO_FC = 1
    PORT_PROTO_ISCSI = 2
    PORT_PROTO_IP = 4

    PORT_STATE_READY = 4
    PORT_STATE_SYNC = 5
    PORT_STATE_OFFLINE = 10

    HOST_EDIT_ADD = 1
    HOST_EDIT_REMOVE = 2

    SET_MEM_ADD = 1
    SET_MEM_REMOVE = 2

    STOP_PHYSICAL_COPY = 1
    RESYNC_PHYSICAL_COPY = 2
    GROW_VOLUME = 3

    TARGET_TYPE_VVSET = 1
    TARGET_TYPE_SYS = 2

    PRIORITY_LOW = 1
    PRIORITY_NORMAL = 2
    PRIORITY_HIGH = 3

    # build contains major minor mj=3 min=01 main=03 build=168
    HP3PAR_WS_MIN_BUILD_VERSION = 30103168

    def __init__(self, api_url):
        self.api_url = api_url
        self.http = http.HTTPJSONRESTClient(self.api_url)
        api_version = None
        self.ssh = None
        try:
            api_version = self.getWsApiVersion()
        except Exception:
            msg = ('Either, the 3PAR WS is not running or the'
                   ' version of the WS is invalid.')
            raise exceptions.UnsupportedVersion(msg)

        # Note the build contains major, minor, maintenance and build
        # e.g. 30102422 is 3 01 02 422
        # therefore all we need to compare is the build
        if (api_version is None or
            api_version['build'] < self.HP3PAR_WS_MIN_BUILD_VERSION):
            raise exceptions.UnsupportedVersion('Invalid 3PAR WS API, requires'
                                                ' version, 3.1.3')

    def setSSHOptions(self, ip, login, password, port=22,
                      conn_timeout=30, privatekey=None):
        """This is used to set the SSH credentials for calls
        that use SSH instead of REST HTTP."""
        self.ssh = ssh.HP3PARSSHClient(ip, login, password, port,
                                       conn_timeout, privatekey)

    def getWsApiVersion(self):
        """
        Get the 3PAR WS API version

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
        """
        This is useful for debugging requests to 3PAR

        :param flag: set to True to enable debugging
        :type flag: bool

        """
        self.http.set_debug_flag(flag)
        if self.ssh:
            self.ssh.set_debug_flag(flag)

    def login(self, username, password, optional=None):
        """
        This authenticates against the 3PAR wsapi server and creates a session.

        :param username: The username
        :type username: str
        :param password: The Password
        :type password: str

        :returns: None

        """
        self.http.authenticate(username, password, optional)

    def logout(self):
        """
        This destroys the session and logs out from the 3PAR server

        :returns: None
        """
        self.http.unauthenticate()

    def setHighConnections(self):
        """
        Set the number of REST Sessions to max.
        """
        self.ssh.run(['setwsapi', '-sru', 'high'])

    def getStorageSystemInfo(self):
        """
        Get the Storage System Information

        :returns: Dictionary of Storage System Info
        """
        response, body = self.http.get('/system')
        return body

    def getWSAPIConfigurationInfo(self):
        """
        Get the WSAPI Configuration Information

        :returns: Dictionary of WSAPI configurations
        """
        response, body = self.http.get('/wsapiconfiguration')
        return body

    ##Volume methods
    def getVolumes(self):
        """
        Get the list of Volumes

        :returns: list of Volumes
        """
        response, body = self.http.get('/volumes')
        return body

    def getVolume(self, name):
        """
        Get information about a volume

        :param name: The name of the volume to find
        :type name: str

        :returns: volume
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - volume doesn't exist
        """
        response, body = self.http.get('/volumes/%s' % name)
        return body

    def createVolume(self, name, cpgName, sizeMiB, optional=None):
        """ Create a new volume

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
             'id': 12,
             'comment': 'some comment',
             'snapCPG' :'CPG name',
             'ssSpcAllocWarningPct' : 12,
             'ssSpcAllocLimitPct': 22,
             'tpvv' : True,
             'usrSpcAllocWarningPct': 22,
             'usrSpcAllocLimitPct': 22,
             'expirationHours': 256,
             'retentionHours': 256
            }

        :returns: List of Volumes

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT - Invalid Parameter
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - TOO_LARGE - Volume size above limit
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NO_SPACE - Not Enough space is available
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_SV - Volume Exists already
        """
        info = {'name': name, 'cpg': cpgName, 'sizeMiB': sizeMiB}
        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/volumes', body=info)
        return body

    def deleteVolume(self, name):
        """
        Delete a volume

        :param name: the name of the volume
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - RETAINED - Volume retention time has not expired
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - HAS_RO_CHILD - Volume has read-only child
        """
        response, body = self.http.delete('/volumes/%s' % name)
        return body

    def growVolume(self, name, amount):
        """
        Grow an existing volume by 'amount' Mebibytes.

        :param name: the name of the volume
        :type name: str
        :param amount: the additional size in MiB to add, rounded up to the next chunklet size (e.g. 256 or 1000 MiB)
        :type amount: int

        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_UNSUPPORTED_VV_TYPE - Invalid operation: Cannot grow this type of volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_TUNE_IN_PROGRESS - Invalid operation: Volume tuning is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_LENGTH - Invalid input: String length exceeds limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_VV_GROW_SIZE - Invalid grow size.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NEW_SIZE_EXCEEDS_CPG_LIMIT - New volume size exceeds CPG limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_INTERNAL_VOLUME - This operation is not allowed on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS - Invalid operation: VV conversion is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_VOLUME_COPY_IN_PROGRESS - Invalid operation: online copy is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Internal volume cleanup is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_SIZE_CANNOT_REDUCE - New volume size is smaller than the current size.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NEW_SIZE_EXCEEDS_LIMITS - New volume size exceeds the limit.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_SA_SD_SPACE_REMOVED - Invalid operation: Volume SA/SD space is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_IS_BUSY - Invalid operation: Volume is currently busy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NOT_STARTED - Volume is not started.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_IS_PCOPY - Invalid operation: Volume is a physical copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - Volume state is not normal.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_PROMOTE_IN_PROGRESS - Invalid operation: Volume promotion is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_PARENT_OF_PCOPY - Invalid operation: Volume is the parent of physical copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NO_SPACE - Insufficent space for requested operation.
        """
        info = {'action': self.GROW_VOLUME,
                'sizeMiB': amount}

        response, body = self.http.put('/volumes/%s' % name, body=info)
        return body

    def copyVolume(self, src_name, dest_name, optional=None):
        """
        Copy/Clone a volume.

        :param src_name: the source volume name
        :type src_name: str
        :param dest_name: the destination volume name
        :type dest_name: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'destCPG': "OpenStack_CPG", # CPG for the destination volume
                'online': False, # should physical copy be performed online?
                'tpvv': False, # use thin provisioned space for destination?  (online copy only)
                'snapCPG' : "OpenStack_SnapCPG, # snapshot CPG for the destination (online copy only)
                'saveSnapshot': False, # save the snapshot of the source volume after the copy id complete?
                'priority' : 1 # taskPriorityEnum (does not apply to online copy)
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid range(1-3).
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a base volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved in a remote copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the same as the parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a read-only snapshot.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the base volume of a parent volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a conversion operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must allow snapshots.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the target of an online copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume for the volume is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the normal state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has a physical copy in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the destination volume has failed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent volume is larger than the size of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VVCOPY - Physical copy not found.
        """
        # Virtual volume sets are not supported with the -online option
        parameters = {'destVolume': dest_name}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action': 'createPhysicalCopy',
                'parameters': parameters}

        response, body = self.http.post('/volumes/%s' % src_name, body=info)
        return body

    def stopPhysicalCopy(self, name):
        """
        Stopping a physical copy operation.

        :param name: the name of the volume
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Invalid VV name or CPG name.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_CPG - The CPG does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - CPG_NOT_IN SAME_DOMAIN - The CPG is not in the current domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_NOT_IN_SAME_DOMAIN - The volume is not in the same domain.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BAD_ENUM_VALUE - The priority value in not in the valid range(1-3).
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_VOLUME - The volume already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_NON_BASE_VOLUME - The destination volume is not a base volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_IN_REMOTE_COPY - The destination volume is involved in a remote copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_EXPORTED - The volume is exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_COPY_TO_SELF - The destination volume is the same as the parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_READONLY_SNAPSHOT - The parent volume is a read-only snapshot.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_COPY_TO_BASE - The destination volume is the base volume of a parent volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_VOLUME_CONV_IN_PROGRESS  - The volume is in a conversion operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NO_SNAPSHOT_ALLOWED - The parent volume must allow snapshots.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_ONLINE_COPY_IN_PROGRESS  - The volume is the target of an online copy.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_CLEANUP_IN_PROGRESS - Cleanup of internal volume for the volume is in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_CIRCULAR_COPY - The parent volume is a copy of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_PEER_VOLUME - The operation is not allowed on a peer volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NOT_IN_NORMAL_STATE - The volume is not in the normal state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_INCONSISTENT_STATE - The volume has an internal consistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_PCOPY_IN_PROGRESS  - The destination volume has a physical copy in progress.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_FAILED_ONLINE_COPY  - Online copying of the destination volume has failed.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - INV_OPERATION_VV_COPY_PARENT_TOO_BIG - The size of the parent volume is larger than the size of the destination volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_NO_PARENT - The volume has no physical parent.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - IN_USE - The resynchronization snapshot is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_STALE_STATE - The volume is in a stale state.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VVCOPY - Physical copy not found.
        """
        info = {'action': self.STOP_PHYSICAL_COPY}

        response, body = self.http.put('/volumes/%s' % name, body=info)
        return body

    def createSnapshot(self, name, copyOfName, optional=None):
        """
        Create a snapshot of an existing Volume

        :param name: Name of the Snapshot
        :type name: str
        :param copyOfName: The volume you want to snapshot
        :type copyOfName: str
        :param optional: Dictionary of optional params
        :type optional: dict

        .. code-block:: python

            optional = {
                'id' : 12, # Specifies the ID of the volume, next by default
                'comment' : "some comment",
                'readOnly' : True, # Read Only
                'expirationHours' : 36, # time from now to expire
                'retentionHours' : 12 # time from now to expire
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        """
        parameters = {'name': name}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action': 'createSnapshot',
                'parameters': parameters}

        response, body = self.http.post('/volumes/%s' % copyOfName, body=info)
        return body

    ##Host methods
    def getHosts(self):
        """
        Get information about every Host on the 3Par array

        :returns: list of Hosts
        """
        response, body = self.http.get('/hosts')
        return body

    def getHost(self, name):
        """
        Get information about a Host

        :param name: The name of the Host to find
        :type name: str

        :returns: host dict
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - HOST doesn't exist
        """
        response, body = self.http.get('/hosts/%s' % name)
        return body

    def createHost(self, name, iscsiNames=None, FCWwns=None, optional=None):
        """
        Create a new Host entry
        TODO: get the list of thrown exceptions

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
                'domain' : 'myDomain', # Create the host in the specified domain, or default domain if unspecified.
                'forceTearDown' : False, # If True, force to tear down low-priority VLUN exports.
                'iSCSINames' : True, # Read Only
                'descriptors' : {'location' : 'earth', 'IPAddr' : '10.10.10.10', 'os': 'linux',
                              'model' : 'ex', 'contact': 'Smith', 'comment' : 'Joe's box}
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_MISSING_REQUIRED - Name not specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_PARAM_CONFLICT - FCWWNs and iSCSINames are both specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_LENGTH - Host name, domain name, or iSCSI name is too long.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EMPTY_STR - Input string (for domain name, iSCSI name, etc.) is empty.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Any error from host-name or domain-name parsing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI names are specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_WRONG_TYPE - The length of WWN is not 16. WWN specification contains non-hexadecimal digit.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_PATH - host WWN/iSCSI name already used by another host
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_HOST - host name is already used.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NO_SPACE - No space to create host.
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
        """
        Modify an existing Host entry

        :param name: The name of the host
        :type name: str
        :param mod_request: Objects for Host Modification Request
        :type mod_request: dict

        .. code-block:: python

            mod_request = {
                'newName' : 'myNewName', # New name of the host
                'pathOperation' : 1, # If adding, adds the WWN or iSCSI name to the existing host.
                'FCWWNs' : [], # One or more WWN to set for the host.
                'iSCSINames' : [], # One or more iSCSI names to set for the host.
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT - Missing host name.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_PARAM_CONFLICT - Both iSCSINames & FCWWNs are specified. (lot of other possibilities)
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ONE_REQUIRED - iSCSINames or FCWwns missing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ONE_REQUIRED - No path operation specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BAD_ENUM_VALUE - Invalid enum value.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_MISSING_REQUIRED - Required fields missing.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_LENGTH - Host descriptor argument length, new host name, or iSCSI name is too long.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Error parsing host or iSCSI name.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_HOST - New host name is already used.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - Host to be modified does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_TOO_MANY_WWN_OR_iSCSI - More than 1024 WWNs or iSCSI names are specified.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_WRONG_TYPE - Input value is of the wrong type.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_PATH - WWN or iSCSI name is already claimed by other host.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BAD_LENGTH - CHAP hex secret length is not 16 bytes, or chap ASCII secret length is not 12 to 16 characters.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NO_INITIATOR_CHAP - Setting target CHAP without initiator CHAP.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_CHAP - Remove non-existing CHAP.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - NON_UNIQUE_CHAP_SECRET - CHAP secret is not unique.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXPORTED_VLUN - Setting persona with active export; remove a host path on an active export.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NON_EXISTENT_PATH - Remove a non-existing path.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - LUN_HOSTPERSONA_CONFLICT - LUN number and persona capability conflict.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_DUP_PATH - Duplicate path specified.
        """
        response, body = self.http.put('/hosts/%s' % name, body=mod_request)
        return body

    def deleteHost(self, name):
        """
        Delete a Host

        :param name: Host Name
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` -  IN_USE - The HOST Cannot be removed because it's in use.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        """
        reponse, body = self.http.delete('/hosts/%s' % name)

    def findHost(self, iqn=None, wwn=None):
        """
        Find a host from an iSCSI initiator or FC WWN

        :param iqn: lookup based on iSCSI initiator
        :type iqn: str
        :param wwn: lookup based on WWN
        :type wwn: str
        """
        # for now there is no search in the REST API
        # so we can do a create looking for a specific
        # error.  If we don't get that error, we nuke the
        # fake host.

        cmd = ['createhost']
        #create a random hostname
        hostname = 'zxy-delete-vxz'
        if iqn:
            cmd.append('-iscsi')

        cmd.append(hostname)

        if iqn:
            cmd.append(iqn)
        else:
            cmd.append(wwn)

        result = self.ssh.run(cmd)
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

    def queryHost(self, iqn=None, wwn=None):
        """
        Find a host from an iSCSI initiator or FC WWN

        :param iqn: lookup based on iSCSI initiator
        :type iqn: str
        :param wwn: lookup based on WWN
        :type wwn: str

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT - Invalid URI syntax.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - HOST Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPInternalServerError` - INTERNAL_SERVER_ERR - Internal server error.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Host name contains invalid character.
        """
        query = ''
        if iqn:
            query = 'iSCSIPaths[name==%s]' % iqn
        if wwn:
            query = 'FCPaths[wwn==%s]' % wwn

        query = '"%s"' % query

        response, body = self.http.get('/hosts?query=%s' % urllib2.quote(query.encode("utf8")))
        return body

    def getHostVLUNs(self, hostName):
        """
        Get all of the VLUNs on a specific Host

        :param hostName: Host name
        :type hostNane: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - HOST Not Found
        """
        # calling getHost to see if the host exists and raise not found
        # exception if it's not found.
        self.getHost(hostName)

        allVLUNs = self.getVLUNs()

        vluns = []

        if allVLUNs:
            for vlun in allVLUNs['members']:
                if vlun['hostname'] == hostName:
                    vluns.append(vlun)

        if len(vluns) < 1:
            raise exceptions.HTTPNotFound({'code': 'NON_EXISTENT_HOST',
                                           'desc': 'HOST Not Found'})

        return vluns

    ## PORT Methods
    def getPorts(self):
        """
        Get the list of ports on the 3Par

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
        """
        Get a list of Fibre Channel Ports

        :returns: list of Fibre Channel Ports
        """
        return self._getProtocolPorts(1, state)

    def getiSCSIPorts(self, state=None):
        """
        Get a list of iSCSI Ports

        :returns: list of iSCSI Ports
        """
        return self._getProtocolPorts(2, state)

    def getIPPorts(self, state=None):
        """
        Get a list of IP Ports

        :returns: list of IP Ports
        """
        return self._getProtocolPorts(4, state)

    ## CPG methods
    def getCPGs(self):
        """
        Get entire list of CPGs

        :returns: list of cpgs
        """
        response, body = self.http.get('/cpgs')
        return body

    def getCPG(self, name):
        """
        Get information about a CPG

        :param name: The name of the CPG to find
        :type name: str

        :returns: cpg dict
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` -  NON_EXISTENT_CPG - CPG doesn't exist
        """
        response, body = self.http.get('/cpgs/%s' % name)
        return body

    def createCPG(self, name, optional=None):
        """
        Create a CPG

        :param name: CPG Name
        :type name: str
        :param optional: Optional parameters
        :type optional: dict

        .. code-block:: python

            optional = {
                'growthIncrementMiB' : 100,
                'growthLimitMiB' : 1024,
                'usedLDWarningAlertMiB' : 200,
                'domain' : 'MyDomain',
                'LDLayout' : {'RAIDType' : 1, 'setSize' : 100, 'HA': 0,
                              'chunkletPosPref' : 2, 'diskPatterns': []}
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT Invalid URI Syntax.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` -
        NON_EXISTENT_DOMAIN - Domain doesn't exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NO_SPACE - Not Enough space is available.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - BAD_CPG_PATTERN  A Pattern in a CPG specifies illegal values.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXISTENT_CPG - CPG Exists already

        """
        info = {'name': name}
        if optional:
            info = self._mergeDict(info, optional)

        reponse, body = self.http.post('/cpgs', body=info)
        return body

    def deleteCPG(self, name):
        """
        Delete a CPG

        :param name: CPG Name
        :type name: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_CPG - CPG Not Found
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` -  IN_USE - The CPG Cannot be removed because it's in use.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied

        """
        reponse, body = self.http.delete('/cpgs/%s' % name)

    ## VLUN methods
    ## Virtual-LUN, or VLUN, is a pairing between a virtual volume and a
    ## logical unit number (LUN), expressed as either a VLUN template or
    ## an active
    ## VLUN
    ## A VLUN template sets up an association between a virtual volume and a
    ## LUN-host, LUN-port, or LUN-host-port combination by establishing the
    ## export rule or the manner in which the Volume is exported.
    def getVLUNs(self):
        """
        Get VLUNs

        :returns: Array of VLUNs
        """
        reponse, body = self.http.get('/vluns')
        return body

    def getVLUN(self, volumeName):
        """
        Get information about a VLUN

        :param volumeName: The volume name of the VLUN to find
        :type name: str

        :returns: VLUN

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` -  NON_EXISTENT_VLUN - VLUN doesn't exist

        """
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
        """
        Create a new VLUN

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
        :param portPos: 'portPos' (dict) - System port of VLUN exported to. It includes node number, slot number, and card port number
        :type portPos: dict
        :param noVcn: A VLUN change notification (VCN) not be issued after export (-novcn). Default: False.
        :type noVcn: bool
        :param overrideLowerPriority: Existing lower priority VLUNs will
                be overridden (-ovrd). Use only if hostname member exists. Default:
                False.
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
        """
        Delete a VLUN

        :param volumeName: the volume name of the VLUN
        :type name: str
        :param lunID: The LUN ID
        :type lunID: int
        :param hostname: Name of the host which the volume is exported. For VLUN of port type,the value is empty
        :type hostname: str
        :param port: Specifies the system port of the VLUN export.  It includes
        the system node number, PCI bus slot number, and card port number on
        the FC card in the format <node>:<slot>:<cardPort>
        :type port: dict

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_MISSING_REQUIRED - Incomplete VLUN info. Missing volumeName or lun, or both hostname and port.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_PORT_SELECTION - Specified port is invalid.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_RANGE - The LUN specified exceeds expected range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - The host does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VLUN - The VLUN does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_PORT - The port does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        """

        vlun = "%s,%s" % (volumeName, lunID)

        if hostname:
            vlun += ",%s" % hostname

        if port:
            vlun += ",%s:%s:%s" % (port['node'],
                                   port['slot'],
                                   port['cardPort'])

        response, body = self.http.delete('/vluns/%s' % vlun)

    ## VolumeSet methods
    def findVolumeSet(self, name):
        """
        Find the Volume Set name for a volume.

        :param name: the volume name
        :type name: str
        """
        cmd = ['showvvset', '-vv', name]
        out = self.ssh.run(cmd)
        vvset_name = None
        if out and len(out) > 1:
            info = out[1].split(",")
            vvset_name = info[1]

        return vvset_name

    def getVolumeSets(self):
        """
        Get Volume Sets

        :returns: Array of Volume Sets
        """
        reponse, body = self.http.get('/volumesets')
        return body

    def getVolumeSet(self, name):
        """
        Get information about a Volume Set

        :param name: The name of the Volume Set to find
        :type name: str

        :returns: Volume Set

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_SET - The set doesn't exist
        """
        reponse, body = self.http.get('/volumesets/%s' % name)
        return body

    def createVolumeSet(self, name, comment=None, domain=None,
                        setmembers=None):
        """
        This creates a new volume set

        :param name: the volume set to create
        :type set_name: str
        :param comment: the comment for on the vv set
        :type comment: str
        :param domain: the domain where the set lives
        :type domain: str
        :param setmembers: the vv to add to the set, the existence of the vv
        will not be checked
        :type setmembers: array

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_INCONSISTENT_STATE - The volume has an internal inconsistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - The host does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        """
        info = {'name': name}

        if comment:
            info['comment'] = comment

        if domain:
            info['domain'] = domain

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

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - EXPORTED_VLUN - The host set has exported VLUNs. The VV set was exported.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - VVSET_QOS_TARGET - The object is already part of the set.
        """
        response, body = self.http.delete('/volumesets/%s' % name)

    def modifyVolumeSet(self, name, action=None, newName=None, comment=None, setmembers=None):
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
        :param setmembers: the vv to add to the set, the existence of the vv will not be checked
        :type setmembers: array

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - EXISTENT_SET - The set already exits.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_SET - The set does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_IN_DOMAINSET - The host is in a domain set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_IN_SET - The object is already part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - MEMBER_NOT_IN_SET - The object is not part of the set.
        :raises: :class:`~hp3parclient.exceptions.HTTPConflict` - MEMBER_NOT_IN_SAME_DOMAIN - Objects must be in the same domain to perform this operation.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IN_INCONSISTENT_STATE - The volume has an internal inconsistency error.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - VV_IS_BEING_REMOVED - The volume is being removed.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOLUME - The volume does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_SYS_VOLUME - The operation is not allowed on a system volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - INV_OPERATION_VV_INTERNAL_VOLUME - The operation is not allowed on an internal volume.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_DUP_NAME - Invalid input (duplicate name).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_PARAM_CONFLICT - Invalid input (parameters cannot be present at the same time).
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Invalid contains one or more illegal characters.
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

        response, body = self.http.put('/volumesets/%s' % name, body=info)

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
        result = self.ssh.run(cmd)

        if result:
            msg = result[0]
        else:
            msg = None

        if msg:
            if 'no matching QoS target found' in msg:
                raise exceptions.HTTPNotFound(error={'desc': msg})
            else:
                raise exceptions.SetQOSRuleException(message=msg)

    def createQoSRules(self, name, target_type, optional=None):
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

        :param name: the name of the target object on which the QoS
                     rule will be created.
        :type name: str
        :param target_name: Type of QoS target, either enum
                            TARGET_TYPE_VVS or TARGET_TYPE_SYS.
        :type target_type: enum
        :param optional: Optional parameters
        :type optional: dict

        .. code-block:: python

            optional = {
                'priority': 2,         # priority enum
                'bwMinGoalKB': 1024,   # bandwidth rate minimum goal in kilobytes per second
                'bwMaxLimitKB': 1024,  # bandwidth rate maximum limit in kilobytes per second
                'ioMinGoal': 10000,    # I/O-per-second minimum goal
                'ioMaxLimit': 2000000, # I/0-per-second maximum limit
                'enable': True,        # QoS rule for target enabled?
                'bwMinGoalOP': 1,      # zero none operation enum, when set to 1, bandwidth minimum goal is 0
                                       # when set to 2, the bandwidth mimumum goal is none (NoLimit)
                'bwMaxLimitOP': 1,     # zero none operation enum, when set to 1, bandwidth maximum limit is 0
                                       # when set to 2, the bandwidth maximum limit is none (NoLimit)
                'ioMinGoalOP': 1,      # zero none operation enum, when set to 1, I/O minimum goal is 0
                                       # when set to 2, the I/O minimum goal is none (NoLimit)
                'ioMaxLimitOP': 1,     # zero none operation enum, when set to 1, I/O maximum limit is 0
                                       # when set to 2, the I/O maximum limit is none (NoLimit)
                'latencyGoal': 5000,   # Latency goal in milliseconds
                'defaultLatency': False # Use latencyGoal or defaultLatency?
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit should be greater than the mimimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BELOW_RANGE - I/O-per-second limit is below range. Bandwidth limit is below range.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - UNLICENSED_FEATURE - The system is not licensed for QoS.
        """
        info = {'name': name,
                'type': target_type}

        if optional:
            info = self._mergeDict(info, optional)

        reponse, body = self.http.post('/qos', body=info)
        return body

    def modifyQoSRules(self, name, target_type, optional=None):
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

        :param name: the name of the target object on which the QoS
                     rule will be created.
        :type name: str
        :param target_name: Type of QoS target, either enum
                            TARGET_TYPE_VVS or TARGET_TYPE_SYS.
        :type target_type: enum
        :param optional: Optional parameters
        :type optional: dict

        .. code-block:: python

            optional = {
                'priority': 2,         # priority enum
                'bwMinGoalKB': 1024,   # bandwidth rate minimum goal in kilobytes per second
                'bwMaxLimitKB': 1024,  # bandwidth rate maximum limit in kilobytes per second
                'ioMinGoal': 10000,    # I/O-per-second minimum goal.
                'ioMaxLimit': 2000000, # I/0-per-second maximum limit
                'enable': True,        # QoS rule for target enabled?
                'bwMinGoalOP': 1,      # zero none operation enum, when set to 1, bandwidth minimum goal is 0
                                       # when set to 2, the bandwidth minimum goal is none (NoLimit)
                'bwMaxLimitOP': 1,     # zero none operation enum, when set to 1, bandwidth maximum limit is 0
                                       # when set to 2, the bandwidth maximum limit is none (NoLimit)
                'ioMinGoalOP': 1,      # zero none operation enum, when set to 1, I/O minimum goal minimum goal is 0
                                       # when set to 2, the I/O minimum goal is none (NoLimit)
                'ioMaxLimitOP': 1,     # zero none operation enum, when set to 1, I/O maximum limit is 0
                                       # when set to 2, the I/O maximum limit is none (NoLimit)
                'latencyGoal': 5000,   # Latency goal in milliseconds
                'defaultLatency': False # Use latencyGoal or defaultLatency?
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_RANGE - Invalid input: number exceeds expected range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_QOS_RULE - QoS rule does not exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - EXISTENT_QOS_RULE - QoS rule already exists.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_IO_MIN_GOAL_GRT_MAX_LIMIT - I/O-per-second maximum limit should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BW_MIN_GOAL_GRT_MAX_LIMIT - Bandwidth maximum limit should be greater than the minimum goal.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_BELOW_RANGE - I/O-per-second limit is below range. Bandwidth limit is below range.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - UNLICENSED_FEATURE - The system is not licensed for QoS.
        """
        info = {'name': name,
                'type': target_type}

        if optional:
            info = self._mergeDict(info, optional)

        reponse, body = self.http.put('/qos', body=info)
        return body

    def deleteQoSRules(self, targetType, targetName):
        """
        Clear and Delete QoS rules

        :param targetType: target type is vvset or sys
        :type targetType: str
        :param targetName: the name of the target. When targetType is sys,
                           target name must be sys:all_others.
        :type targetName: str

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_QOS_RULE - QoS rule does not exist.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_ILLEGAL_CHAR - Illegal character in the input.
        """
        response, body = self.http.delete('/qos/%(targ_type)s:%(targ_name)s' %
                                          {'targ_type': targetType,
                                           'targ_name': targetName})

    def setVolumeMetaData(self, name, key, value):
        """
        This is used to set a key/value pair metadata into a volume.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str
        :param value: the metadata value
        :type value: str
        """
        cmd = ['setvv', '-setkv', key + '=' + value, name]
        result = self.ssh.run(cmd)
        if result and len(result) == 1:
            if 'does not exist' in result[0]:
                raise exceptions.HTTPNotFound(error={'desc': result[0]})

    def removeVolumeMetaData(self, name, key):
        """
        This is used to remove a metadata key/value pair from a volume.

        :param name: the volume name
        :type name: str
        :param key: the metadata key name
        :type key: str
        """
        cmd = ['setvv', '-clrkey', key, name]
        result = self.ssh.run(cmd)
        if result and len(result) == 1:
            if 'does not exist' in result[0]:
                raise exceptions.HTTPNotFound(error={'desc': result[0]})

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
