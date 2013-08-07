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
import argparse
import unittest
import subprocess
import time
import pprint
import inspect
from testconfig import config

# pip install nose-testconfig


class HP3ParClientBaseTestCase(unittest.TestCase):     
  
    #if have debug as second argument for the test
    #for example, pythong test_HP3ParClient_CPG.py debug
    #need to manaully start test_HP3ParMockServer_flask.py before run 
    #test
    user = config['3PAR']['user']
    password = config['3PAR']['pass']
    debug = config['3PAR']['debug']
    unitTest = config['3PAR']['unit']
    flask_url = config['3PAR']['flask_url']
    url_3par = config['3PAR']['3par_url']
        
    def setUp(self):
            
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            
        if self.unitTest :
            self.cl = client.HP3ParClient(self.flask_url)
            script = 'test_HP3ParMockServer_flask.py'
            path = "%s/%s" % (cwd, script)
            self.mockServer = subprocess.Popen([sys.executable, 
                                               path], 
                                               stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE, 
                                               stdin=subprocess.PIPE)
            time.sleep(1) 
        else :
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

