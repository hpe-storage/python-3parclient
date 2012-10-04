# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Hewlett Packard Development Company, L.P.
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
HP3Par REST Client

.. module: HP3ParClient
.. moduleauthor: Walter A. Boring IV

:Author: Walter A. Boring IV
:Description: This is the 3PAR Client that talks to 3PAR's REST WSAPI Service.  It provides the ability to provision 3PAR volumes, VLUNs, CPGs.

"""

import logging
import os
import urlparse
import httplib2
import time
import pprint

from hp3parclient import http,exceptions


class HP3ParClient:
    """
    The 3PAR REST API Client

    :param api_url: The url to the WSAPI service on 3PAR ie. http://<3par server>:8008/api/v1
    :type api_url: str

    """

    def __init__(self, api_url):
	self.http = http.HTTPJSONRESTClient(api_url)

    def debug_rest(self,flag):
        """
        This is useful for debugging requests to 3PAR

        :param flag: set to True to enable debugging
        :type flag: bool

        """
	self.http.set_debug_flag(flag)

    def login(self, username, password):
        """
        This authenticates against the 3Par wsapi server and creates a session.

        :param username: The username
        :type username: str
        :param password: The Password
        :type password: str

        :returns: None

        """
	self.http.authenticate(username, password)

    def logout(self):
        """
        This destroys the session and logs out from the 3PAR server

        :returns: None

        """
        self.http.unauthenticate()


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
        volumes = self.getVolumes()
        if volumes:
            for volume in volumes['members']:
                if volume['name'] == name:
                    return volume

        raise exceptions.HTTPNotFound({'code':'NON_EXISTENT_VOL', 'desc': "Volume '%s' was not found" % name})

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
                'copyRO' : True, # Read Only?
                'expirationHours' : 36 # time from now to expire
                'retentionHours' : 12 # time from now to expire 
            }

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VOL - The volume does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        """
        parameters = {'name' : name}
        if optional:
            parameters = self._mergeDict(parameters, optional)

        info = {'action' : 'createSnapshot',
                'parameters' : parameters}

        response, body = self.http.post('/volumes/%s' % copyOfName, body=info)
	return body




    ##CPG methods
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
        cpgs = self.getCPGs()
        if cpgs:
            for cpg in cpgs['members']:
                if cpg['name'] == name:
                    return cpg 

        raise exceptions.HTTPNotFound({'code':'NON_EXISTENT_CPG', 'desc': "CPG '%s' was not found" % name})

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

        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT Invalid URI Syntax 
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NON_EXISTENT_DOMAIN - Domain doesn't exist
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - NO_SPACE - Not Enough space is available.
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - BAD_CPG_PATTERN  A Pattern in a CPG specifies illegal values
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
    ## logical unit number (LUN), expressed as either a VLUN template or an active
    ## VLUN

    ## A VLUN template sets up an association between a virtual volume and a
    ## LUN-host, LUN-port, or LUN-host-port combination by establishing the export
    ## rule, or the manner in which the Volume is exported. 


    def getVLUNs(self):
	""" 
        Get VLUNs
        
        :returns: Array of VLUNs
        """
	reponse, body = self.http.get('/vluns')
	return body

    def getVLUN(self, name):
        """ 
        Get information about a VLUN

        :param name: The name of the VLUN to find
        :type name: str

        :returns: VLUN

        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` -  NON_EXISTENT_VLUN - VLUN doesn't exist

        """
        vluns = self.getVLUNs()
        if vluns:
            for vlun in vluns['members']:
                if vlun['name'] == name:
                    return vlun

        raise exceptions.HTTPNotFound({'code':'NON_EXISTENT_VLUN', 'desc': "VLUN '%s' was not found" % name})

    def createVLUN(self, volumeName, lun, hostname=None, portPos=None, noVcn=None,
                   overrideLowerPriority=None):
	""" 
        Create a new VLUN

        When creating a VLUN, the volumeName and lun members are required.
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
	info = {'volumeName': volumeName, 'lun': lun}

        if hostname:
            info['hostname'] = hostname

        if portPos:
            info['portPos'] = portPos

        if noVcn:
            info['noVcn'] = noVcn

        if overrideLowerPriority:
            info['overrideLowerPriority'] = overrideLowerPriority

	response, body = self.http.post('/vluns', body=info)
        if response:
            location = response['headers']['location'].replace('/api/v1/vluns/', '')
	    return location
        else:
            return None
        
    def deleteVLUN(self, name, lunID, hostname=None, port=None):
	""" 
        Delete a VLUN
        
        :param name: the name of the VLUN
        :type name: str
        :param lunID: The LUN ID 
        :type lunID: int
        :param hostname: Name of the host which the volume is exported. For VLUN of port type,the value is empty
        :type hostname: str
        :param port: Specifies the system port of the VLUN export.  It includes the system node number, PCI bus slot number, and card port number on the FC card in the format <node>:<slot>:<port>
        :type port: str


        
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_MISSING_REQUIRED - Incomplete VLUN info. Missing volumeName or lun, or both hostname and port. 
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_PORT_SELECTION - Specified port is invalid. 
        :raises: :class:`~hp3parclient.exceptions.HTTPBadRequest` - INV_INPUT_EXCEEDS_RANGE - The LUN specified exceeds expected range.
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_HOST - The host does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_VLUN - The VLUN does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPNotFound` - NON_EXISTENT_PORT - The port does not exist
        :raises: :class:`~hp3parclient.exceptions.HTTPForbidden` - PERM_DENIED - Permission denied
        """

        vlun = ("%s,%s" % name, lunID)

        if hostname:
            vlun += ",%s" % hostname

        if port:
            vlun += ",%s" % port

	response, body = self.http.delete('/vluns/%s' % vlun)



    def _mergeDict(selft, dict1, dict2):
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

