
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
            name = 'UnitTestHostBadParams'
            optional = {'iSCSIPaths': {'modelBad': 'UNIT_TEST'}}
            self.cl.createHost(name, None, None, optional)             
        except exceptions.HTTPBadRequest:
            print "Expected exception"  
            self.printFooter('create_host_badParams')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.fail("No exception occurred")

    def test_1_create_host_badParams2(self):
        self.printHeader('create_host_badParams2')
        try:
            name = 'UnitTestHostBadParams2'
            optional = {'domainBad': 'hp'}
            self.cl.createHost(name, None, None, optional) 
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            self.printFooter('create_host_badParams2')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.fail("No exception occurred")       

    def test_1_create_host_perm_denied(self):
        self.printHeader('create_host_perm_denied')
        try:
            name = 'PermissionDeniedHost'
            optional = {'domain' : 'default'}
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPForbidden:
            print 'Expected exception'
            self.printFooter('create_host_perm_denied')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_no_name(self):
        self.printHeader('create_host_no_name')
        try:
            optional = {'domain' : 'default'}
            self.cl.createHost(None, None, None, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_no_name')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_exceed_length(self):
        self.printHeader('create_host_exceed_length')
        try:
            optional = {'domain': 'ThisDomainNameIsWayTooLongToMakeAnySense'}
            name = 'LongDomainHost'
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_exceed_length')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_empty_domain(self):
        self.printHeader('create_host_empty_domain')
        try:
            optional={'domain': ''}
            name = 'EmptyDomainHost'
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_empty_domain')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_illegal_string(self):
        self.printHeader('create_host_illegal_string')
        try:
            optional = {'domain' : 'doma&n'}
            name = 'IllegalDomainHost'
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_illegal_string')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_param_conflict(self):
        self.printHeader('create_host_param_conflict')
        try:
            optional = {'domain' : 'default'}
            FCWwns = {'fcpath1':'path1'}
            iSCSINames = {'vendor' : 'hp'}
            name = 'DualPathHost'
            self.cl.createHost(name, iSCSINames, FCWwns, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_param_conflict')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_long_params(self):
        self.printHeader('create_host_long_params')
        try:
            optional = {'domain' : 'default'}
            name = 'LongParamsHost'
            fc = {'length' : '1024'}
            self.cl.createHost(name, None, fc, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_long_params')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_wrong_type(self):
        self.printHeader('create_host_wrong_type')
        try:
            optional = {'domain' :'default'}
            fc = {'length' : 'LessThan16'}
            name = 'WrongTypeHost'
            self.cl.createHost(name, None, fc, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_wrong_type')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_existent_path(self):
        self.printHeader('create_host_existent_path')
        try:
            optional = {'domain':'default'}
            fc = {'path' : 'ExistentPath'}
            name = 'ExistentPathHost'
            self.cl.createHost(name, None, fc, optional)
        except exceptions.HTTPConflict:
            print 'Expected exception'
            self.printFooter('create_host_existent_path')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_duplicate(self):
        self.printHeader('create_host_duplicate')
        try:
            optional = {'domain' : 'default'}
            name = 'ExistentHost'
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPConflict:
            print 'Expected exception'
            self.printFooter('create_host_duplicate')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_1_create_host_no_space(self):
        self.printHeader('create_host_no_space')
        try:
            optional = {'domain' : 'NoSpace'}
            name = 'NoSpaceHost'
            self.cl.createHost(name, None, None, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_host_no_space')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

    def test_1_create_host(self):
        self.printHeader('create_host')  
        try:
            #add one
            name = 'UnitTestHost'
            optional = {'domain': 'UNIT_TEST'}
            fc = {'fcpath':'path1'}
            self.cl.createHost(name, None, fc, optional)
            #check 
            host1 = self.cl.getHost(name)
            self.assertIsNotNone(host1)
            name1 = host1['name']
            self.assertEqual(name, name1)
            #add another
            name2 = 'UnitTestHost2'
            iSCSINames = {'ipAddr': '10.10.221.58'}
            self.cl.createHost(name2, iSCSINames, None, optional)
            #check
            host2 = self.cl.getHost(name2)
            self.assertIsNotNone(host2)
            name3 = host2['name']
            self.assertEqual(name2, name3)
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.printFooter('create_host')

    def test_2_delete_host_nonExist(self):
        self.printHeader("delete_host_non_exist")
        try:
            self.cl.deleteHost("UnitTestNonExistHost")
        except exceptions.HTTPNotFound:
            print "Expected exception"
            self.printFooter("delete_host_non_exist")
            return
        except Exception as ex:
            print ex
            self.fail("Unexpected Exception")
        self.fail("No error occurred")

    def test_2_delete_host_in_use(self):
        self.printHeader("delete_host_in_use")
        try:
            self.cl.deleteHost("UnitTestInUseHost")
        except exceptions.HTTPForbidden:
            print "Expected exception"
            self.printFooter("delete_host_in_use")
            return
        except Exception as ex:
            print ex
            self.fail("Unexpected Exception")
        self.fail("No error occurred")

    def test_2_delete_host(self):
        self.printHeader("delete_host")
        try:
            hosts = self.cl.getHosts()
            if hosts and hosts['total'] > 0:
                for host in hosts['members']:
                    if host['name'].startswith('UnitTestHost'):
                        self.cl.deleteHost(host['name'])
            #check
            try:
                name = 'UnitTestHost'
                host = self.cl.getHost(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail("Failed with unexpected exception")

            try:
                name = 'UnitTestHost2'
                host = self.cl.getHost(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail ("Failed with unexpected exception")
        except Exception as ex:
            print ex
            self.fail ("Failed with unexpected exception")

    def test_3_get_host_bad(self):
        self.printHeader("get_host_bad")
        try:
            self.cl.getHost("BadHostName")
        except exceptions.HTTPNotFound:
            print "Expected exception"
            self.printFooter("get_host_bad")
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.fail("No exception occurred")

    def test_3_get_host_illegal(self):
        self.printHeader("get_host_illegal")
        try:
            self.cl.getHost('B&dHostName')
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter("get_host_illegal")
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_3_get_host_invalid_URI(self):
        self.printHeader('get_host_invalid_URI')
        try:
            self.cl.getHost('InvalidURI')
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('get_host_invalid_URI')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')
        self.fail('No exception occurred.')

    def test_3_get_host(self):
        self.printHeader("get_host")
        try:
            hosts = self.cl.getHosts()
            host1 = self.cl.getHost("UnitTestHost")
            host2 = self.cl.getHost("UnitTestHost2")
            self.assertIn(host1, hosts['members'])
            self.assertIn(host2, hosts['members'])
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.printFooter('get_host')

    def test_4_modify_host(self):
        self.printHeader('modify_host')
        try:
            name = 'ModifyHost'
            mod_request = {'newName' : 'ModifiedHost'}
            self.cl.modifyHost(name, mod_request)
            self.printFooter('modfiy_host')
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception.')
        