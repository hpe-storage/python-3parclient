# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2009-2012 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test base class of 3Par Client"""

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import subprocess
import time
import pprint
import inspect
from testconfig import config
from urlparse import urlparse

# pip install nose-testconfig

# e.g.
# nosetests test_HP3ParClient_host.py -v --tc-file config.ini


class HP3ParClientBaseTestCase(unittest.TestCase):     
  
    #if have debug as second argument for the test
    #for example, pythong test_HP3ParClient_CPG.py debug
    #need to manaully start test_HP3ParMockServer_flask.py before run 
    #test
    user = config['3PAR']['user']
    password = config['3PAR']['pass']
    flask_url = config['3PAR']['flask_url']
    url_3par = config['3PAR']['3par_url']
    debug = config['3PAR']['debug'].lower() == 'true'
    unitTest = config['3PAR']['unit'].lower() == 'true'
        
    def setUp(self):
            
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            
        if self.unitTest :
            self.printHeader('Using flask ' + self.flask_url)
            self.cl = client.HP3ParClient(self.flask_url)
            parsed_url = urlparse(self.flask_url)
            userArg = '-user=%s' % self.user
            passwordArg = '-password=%s' % self.password
            portArg = '-port=%s' % parsed_url.port
            args = '-user %s -password %s -port %s' % (self.user, 
                                                       self.password, 
                                                       parsed_url.port)
            script = 'test_HP3ParMockServer_flask.py'
            path = "%s/%s" % (cwd, script)
            try :
                self.mockServer = subprocess.Popen([sys.executable, 
                                                    path, 
                                                    userArg,
                                                    passwordArg,
                                                    portArg], 
                                               stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE, 
                                               stdin=subprocess.PIPE
                                               )
            except Exception as e:
                pass
            time.sleep(1) 
        else :
            self.printHeader('Using 3PAR ' + self.url_3par)
            self.cl = client.HP3ParClient(self.url_3par)
            
        if self.debug :
            self.cl.debug_rest(True)
         
        self.cl.login(self.user, self.password)

    def tearDown(self):
        self.cl.logout()
        if self.unitTest :
            #TODO: it seems to kill all the process except the last one...
            #don't know why 
            self.mockServer.kill()

    def printHeader(self, name):
        print "\n##Start testing '%s'" % name

    def printFooter(self, name):
        print "##Compeleted testing '%s\n" % name
        
    def findInDict(self, dic, key, value):
        for i in dic :
            if key in i and i[key] == value :
                return True

