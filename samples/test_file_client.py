# (c) Copyright 2015 Hewlett Packard Development Company, L.P.
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
""" HP3PAR sample client program for File Persona arrays.

:Description: This simple sample shows how to call the File Persona API
and print the results.

"""

import os, sys, pprint

from hp3parclient import file_client

cmd_folder = os.path.realpath(os.path.abspath("..") )
if cmd_folder not in sys.path:
     sys.path.insert(0, cmd_folder)

username = 'your-3PAR-user-name'
password = 'your-3PAR-password'
ip = 'your-3PAR-ip-address'

cl = file_client.HP3ParFilePersonaClient("https://%s:8080/api/v1" % ip)
cl.setSSHOptions(ip, username, password, port=22, conn_timeout=None)

cl.login(username, password)

# Test commands and pretty-print their output...
print "GETFS:"
pprint.pprint(cl.getfs())
print "GETVFS:"
pprint.pprint(cl.getvfs())
print "GETFPG:"
pprint.pprint(cl.getfpg())

cl.logout()
