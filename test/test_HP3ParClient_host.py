
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

DOMAIN = 'UNIT_TEST_DOMAIN'
HOST_NAME1 = 'HOST1_UNIT_TEST'
HOST_NAME2 = 'HOST2_UNIT_TEST'

class HP3ParClientHostTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):
    
    def setUp(self):
        super(HP3ParClientHostTestCase, self).setUp()
        
    def tearDown(self):
        try :
            self.cl.deleteHost(HOST_NAME1)
        except :
            pass
        try :
            self.cl.deleteHost(HOST_NAME2)
        except :
            pass        
        
        # very last, tear down base class
        super(HP3ParClientHostTestCase, self).tearDown()

    def test_1_create_host_badParams(self):
        self.printHeader('create_host_badParams')        
        
        name = 'UnitTestHostBadParams'
        optional = {'iSCSIPaths': 'foo bar'}
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          name,
                          None, 
                          None, 
                          optional)
        
        self.printFooter('create_host_badParams')
 

    def test_1_create_host_no_name(self):
        self.printHeader('create_host_no_name')
        
        optional = {'domain' : 'default'}
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          None,
                          None, 
                          None, 
                          optional)
        
        self.printFooter('create_host_no_name') 

    def test_1_create_host_exceed_length(self):
        self.printHeader('create_host_exceed_length')
        
        optional = {'domain': 'ThisDomainNameIsWayTooLongToMakeAnySense'}
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          None, 
                          optional)        
        
        self.printFooter('create_host_exceed_length')
        
 
    def test_1_create_host_empty_domain(self):
        self.printHeader('create_host_empty_domain')
        
        optional={'domain': ''}
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          None, 
                          optional)                
        
        self.printFooter('create_host_empty_domain')        

    def test_1_create_host_illegal_string(self):
        self.printHeader('create_host_illegal_string')
        
        optional = {'domain' : 'doma&n'}
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          None, 
                          optional)     
        
        self.printFooter('create_host_illegal_string')     

    def test_1_create_host_param_conflict(self):
        self.printHeader('create_host_param_conflict')
        
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        iscsi = ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000']
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          iscsi, 
                          fc, 
                          optional)   
        
        self.printFooter('create_host_param_conflict')
        
    def test_1_create_host_wrong_type(self):
        self.printHeader('create_host_wrong_type')
        
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00']
        self.assertRaises(exceptions.HTTPBadRequest, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          fc, 
                          optional)       
        self.printFooter('create_host_wrong_type')            
        
    def test_1_create_host_existent_path(self):
        self.printHeader('create_host_existent_path')
        
        optional = {'domain':DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        self.assertRaises(exceptions.HTTPConflict, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          fc, 
                          optional)   
        
        self.printFooter('create_host_existent_path')        

    def test_1_create_host_duplicate(self):
        self.printHeader('create_host_duplicate')
        
        optional = {'domain' : DOMAIN}
        self.cl.createHost(HOST_NAME1, None, None, optional)
        self.assertRaises(exceptions.HTTPConflict, 
                          self.cl.createHost, 
                          HOST_NAME1,
                          None, 
                          None, 
                          optional)  
        
        self.printFooter('create_host_duplicate')

    def test_1_create_host(self):
        self.printHeader('create_host')  
 
        #add one
            
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        #check 
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertIsNotNone(host1)
        name1 = host1['name']
        self.assertEqual(HOST_NAME1, name1)
        #add another            
        iscsi = ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000']
        self.cl.createHost(HOST_NAME2, iscsi, None, optional)
        #check
        host2 = self.cl.getHost(HOST_NAME2)
        self.assertIsNotNone(host2)
        name3 = host2['name']
        self.assertEqual(HOST_NAME2, name3)

        self.printFooter('create_host')

    def test_2_delete_host_nonExist(self):
        self.printHeader("delete_host_non_exist")
        
        self.assertRaises(exceptions.HTTPNotFound, 
                          self.cl.deleteHost, 
                          "UnitTestNonExistHost")  
        
        self.printFooter("delete_host_non_exist")

    def test_2_delete_host(self):
        self.printHeader("delete_host")
        
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        
        #check 
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertIsNotNone(host1)
        

        hosts = self.cl.getHosts()
        if hosts and hosts['total'] > 0:
            for host in hosts['members']:
                if 'name' in host and host['name'] == HOST_NAME1:
                    self.cl.deleteHost(host['name'])                

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)  
        
        self.printFooter("delete_host")                    


    def test_3_get_host_bad(self):
        self.printHeader("get_host_bad")
        
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, "BadHostName")
        
        self.printFooter("get_host_bad")

    def test_3_get_host_illegal(self):
        self.printHeader("get_host_illegal")
        
        self.assertRaises(exceptions.HTTPBadRequest, self.cl.getHost, "B&dHostName")
        
        self.printFooter("get_host_illegal")
 
    def test_3_get_host(self):
        self.printHeader("get_host")
        
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)
        
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertEquals(host1['name'], HOST_NAME1)        

        self.printFooter('get_host')

    def test_4_modify_host(self):
        self.printHeader('modify_host')
        
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME2)
        
        optional = {'domain': DOMAIN}
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        
        # validate host was created
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertEquals(host1['name'], HOST_NAME1)
        
        # change host name
        mod_request = {'newName' : HOST_NAME2}
        self.cl.modifyHost(HOST_NAME1, mod_request)
        
        # validate host name was changed
        host2 = self.cl.getHost(HOST_NAME2)
        self.assertEquals(host2['name'], HOST_NAME2)
        
        # host 1 name should be history
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)
        
        self.printFooter('modfiy_host')
        