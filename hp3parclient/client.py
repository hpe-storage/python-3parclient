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
	self.http = http.HTTPRESTClient(api_url)

    def debug_rest(self,flag):
	self.http.set_debug_flag(flag)

    def login(self, username, password):
	self.http.authenticate(username, password)

    def logout(self):
        self.http.unauthenticate()		
