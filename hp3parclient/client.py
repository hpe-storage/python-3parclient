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

    def createVolume(self, name, cpgName, sizeMB, extra=None):
	""" Create a new volume
	:Parameters:
	    'name' - (str) - the name of the volume
	    'cpgName' - (str) - the name of the destination CPG 
	    'sizeMB' - (int) - size in MegaBytes for the volume
            'extra' - (dict) - dict of other optional items
                               {'comment': 'some comment', 'snapCPG' :'CPG name'}
	:Returns:
	    List of Volumes
	"""
        info = {'name': name, 'cpg': cpgName, 'sizeMB': sizeMB}
        if extra:
            if type(extra) is dict:
	        for key in extra.keys():
                    info[key] = extra[key]
            else:
                raise Exception("extra must be a dictionary")

        response, body = self.http.post('/volumes', body=info)
	return body

    def deleteVolume(self, name):
	""" Delete a volume
	:Parameters:
	    'name' - (str) - the name of the volume
	:Returns:
	    None
	"""
	info = {'name': name}
	response, body = self.http.delete('/volumes', body=info)
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

    def createCPG(self, name):
	""" Create a CPG
	:Parameters
            'name' (str) - cpg name    
	:Returns
	"""
	info = {'name': name}
	reponse, body = self.http.post('/cpgs', body=info)
	return body
    
    def deleteCPG(self, name):
	""" Delete a CPG
        :Parameters:
            'name' (str) - cpg name    
        :Returns:
            None
        """
	info = {'name': name}
	reponse, body = self.http.delete('/cpgs', body=info)
	return body



    ##VLUN methods
    def getVLUNs(self):
	""" Get VLUNs
        :Parameters:
            None          
        :Returns:
            All vluns
        """
	reponse, body = self.http.get('/vluns')
	return body

    def createVLUN(self, name):
	""" Create a new VLUN
	:Parameters:
	:Returns
	"""
	info = {'name': name}
	response, body = self.http.post('/vluns', body=info)
	return body
        
    def deleteVLUN(self, name):
	""" Delete a VLUN
        :Parameters:
            'name' (str) - vlun name    
        :Returns:
            None
        """
	info = {'name': name}
	response, body = self.http.delete('/vluns', body=info)
	return body

    


