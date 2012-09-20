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
"""

import logging
import os
import urlparse
import httplib2
import time
import pprint

from hp3parclient import http


class HP3ParClient:

    def __init__(self, api_url):
	self.http = http.HTTPJSONRESTClient(api_url)

    def debug_rest(self,flag):
	self.http.set_debug_flag(flag)

    def login(self, username, password):
	self.http.authenticate(username, password)

    def logout(self):
        self.http.unauthenticate()


    ##Volume methods
    def getVolumes(self):
	""" Get the list of Volumes
	:Parameters:
	    None
	:Returns:
	    List of Volumes
	"""
	response, body = self.http.get('/volumes')
        return body

    def createVolume(self, name, cpgName, sizeMB, optional=None):
	""" Create a new volume
	:Parameters:
	    'name' - (str) - the name of the volume
	    'cpgName' - (str) - the name of the destination CPG 
	    'sizeMB' - (int) - size in MegaBytes for the volume
            'optional' - (dict) - dict of other optional items
                               {'comment': 'some comment', 'snapCPG' :'CPG name'}
	:Returns:
	    List of Volumes
	"""
        info = {'name': name, 'cpg': cpgName, 'sizeMB': sizeMB}
        if optional:
            info = self._mergeDict(info, optional)

        response, body = self.http.post('/volumes', body=info)
	return body

    def deleteVolume(self, name):
	""" Delete a volume
	:Parameters:
	    'name' - (str) - the name of the volume
	:Returns:
	    None
	"""
	response, body = self.http.delete('/volumes/%s' % name)
	return body


    def createSnapshot(self, name, copyOfName): 
        info = {'name': name, 'copyOfName': copyOfName, 'isCopy': True}
        response, body = self.http.post('/volumes', body=info)
	return body




    ##CPG methods
    def getCPGs(self):
	""" Get CPGs
        :Parameters:
            None          
        :Returns:
            All cpgs
        """
	response, body = self.http.get('/cpgs')
	return body

    def createCPG(self, name, optional=None):
	""" Create a CPG
	:Parameters
            'name' (str) - cpg name    
            'optional' (dict) - optional parameters

                List of optional keys

                'growthIncrementMB' (int) - Specifies the growth increment, the
                    amount of logical disk storage created on each auto-grow operation.
                'growthLimitMB' (int) - Specifies that the auto-grow operation
                    is limited to the specified storage amount that sets the growth limit.
                'usedLDWarningAlertMB' (int) - Specifies that the threshold of
                    used logical disk space, when exceeded results in a warning alert.
                'domain' (str) - Specifies the name of the domain in which the
                    object will reside.
                'LDLayout' (obj) - Specifies Logical Disk types to be used for
                    this CPG.

                example optional dict:

                {'growthIncrementMB' : 100,
                 'growthLimitMB' : 1024,
                 'usedLDWarningAlertMB' : 200,
                 'domain' : 'MyDomain',
                 'LDLayout' : {'RAIDType' : 1, 'setSize' : 100, 'HA': 0,
                               'chunkletPosPref' : 2, 'diskPatterns': []}
                 }
	:Returns
            returns HTTP 200 response with no body on success
	"""
	info = {'name': name}
        if optional:
            info = self._mergeDict(info, optional)

	reponse, body = self.http.post('/cpgs', body=info)
	return body
    
    def deleteCPG(self, name):
	""" Delete a CPG
        :Parameters:
            'name' (str) - cpg name    
        :Returns:
            None
        """
	reponse, body = self.http.delete('/cpgs/%s' % name)
	return body



    ## VLUN methods

    ## Virtual-LUN, or VLUN, is a pairing between a virtual volume and a
    ## logical unit number (LUN), expressed as either a VLUN template or an active
    ## VLUN

    ## A VLUN template sets up an association between a virtual volume and a
    ## LUN-host, LUN-port, or LUN-host-port combination by establishing the export
    ## rule, or the manner in which the Volume is exported. 


    def getVLUNs(self):
	""" Get VLUNs
        :Parameters:
            None          
        :Returns:
            Array of VLUNs
        """
	reponse, body = self.http.get('/vluns')
	return body

    def createVLUN(self, volumeName, lun, hostname, portPos=None, noVcn=None,
                   overrideLowerPriority=None):
	""" Create a new VLUN
            When creating a VLUN, the volumeName and lun members are required.
            Either hostname or portPos (or both in the case of matched sets) is
            also required.  The noVcn and overrideLowerPriority members are
            optional.
	:Parameters:
            'volumeName' (str) - Name of the volume to be exported
            'lun' (int) - LUN id

            'hostname' (str) - Name of the host which the volume is to be
                exported.

            'portPos' (dict) - System port of VLUN exported to. It includes
                node number, slot number, and card port number
                example:
                    {'node': 1, 'slot': 2, 'cardPort': 3}

            'noVcn' (bool) - A VLUN change notification (VCN) not be issued
                after export (-novcn). Default: False.

            'verrideLowerPriority' (bool) - Existing lower priority VLUNs will
                be overridden (-ovrd). Use only if hostname member exists. Default:
                False.

	:Returns
            HTTP 200 on success with no body
	"""
	info = {'volumeName': volumeName, 'lun': lun, 'hostname':hostname}

        if portPos:
            info['portPos'] = portPos

        if noVcn:
            info['noVcn'] = noVcn

        if overrideLowerPriority:
            info['overrideLowerPriority'] = overrideLowerPriority

	response, body = self.http.post('/vluns', body=info)
	return body
        
    def deleteVLUN(self, name):
	""" Delete a VLUN
        :Parameters:
            'name' (str) - vlun name    
        :Returns:
            None
        """
	response, body = self.http.delete('/vluns/%s' % name)
	return body



    def _mergeDict(selft, dict1, dict2):
        """Safely merge 2 dictionaries together
        :Parameters:
            'dict1' (dict)
            'dict2' (dict)
        :Returns:
            dict
        """
        if type(dict1) is not dict:
            raise Exception("dict1 is not a dictionary")
        if type(dict2) is not dict:
            raise Exception("dict2 is not a dictionary")
        
        dict3 = dict1.copy()
        dict3.update(dict2)
        return dict3


