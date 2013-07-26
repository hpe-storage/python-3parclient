
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

"""Test class of 3Par Client handling Host"""

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

class HP3ParClientHostTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def test_1_create_host_badParams(self):
        self.printHeader('create_host_badParams')
        
        try:
            name='UnitTestHostBadParams'
            optional={'iSCSIPaths': {'modelBad': 'UNIT_TEST'}}
            self.cl.createHost(name, None, None, optional)
            
            self.printFooter('create_host_badParams')
            
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
    
    def test_1_create_host_badParams2(self):
        self.printHeader('create_host_badParams2')
        
        try:
            name='UnitTestHostBadParams2'
            optional={}
            self.cl.createHost(name, None, None, optional)
            
            self.printFooter('create_host_badParams2')
            
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")    
            
    def test_1_create_host(self):
        self.printHeader('create_host')
         
        try:
            #add one
            name='UnitTestHost'
            optional = {'domain' : 'UNIT_TEST'}
            self.cl.createHost(name, None, None, optional)

            #check 
            host1 = self.cl.getHost(name)
            self.assertIsNotNone(host1)
            name1 = host1['name']
            self.assertEqual(name, name1)

            #add another
            name2 = 'UnitTestHost2'
            optional2 = optional.copy()
            more_optional = {'iSCSIPaths':{'ipAddr': '10.10.221.58'}}
            optional2.update(more_optional)
            self.cl.createHost(name2, None, None, optional2)

            #check
            host2 = self.cl.getHost(name2)
            self.assertIsNotNone(host2)
            name3 = host2['name']
            self.assertEqual(name2, name3)

            self.printFooter('create_host')

        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

