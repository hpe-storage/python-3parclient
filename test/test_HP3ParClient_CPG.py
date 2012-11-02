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

"""Test class of 3Par Client handling CPG"""

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

class HP3ParClientCPGTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def test_1_create_CPG(self):
        self.printHeader('create_CPG')

        try:
            #add one
            optional = {'domain': 'UNIT_TEST'}
            name = 'UnitTestCPG'
            self.cl.createCPG(name, optional)
            
            #assert
            cpg1 = self.cl.getCPG(name)
            self.assertIsNotNone(cpg1)
            cpgName = cpg1['name']
            self.assertEqual(name, cpgName)

            #add another
	    name = 'UnitTestCPG2'
            optional2 = optional.copy()
            more_optional = {'LDLayout':{'RAIDType':1}}
            optional2.update(more_optional)
            self.cl.createCPG(name, optional2)

            #assert
            cpg2 = self.cl.getCPG(name)
            self.assertIsNotNone(cpg2)
            cpgName = cpg2['name']
            self.assertEqual(name, cpgName)
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_CPG')
    
    def test_1_create_CPG_badDomain(self):
        self.printHeader('create_CPG_badDomain')

        #add one
        try:
            optional = {'domain': 'BAD_DOMAIN'}
            name = 'UnitTestCPG'
            self.cl.createCPG(name, optional)
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_CPG_badDomain')
   
    def test_1_create_CPG_badDupCPG(self):
        self.printHeader('create_CPG_badDupCPG')

        #add one
        try:
            optional = {'domain': 'UNIT_TEST'}
            name = 'UnitTestCPG3'
            self.cl.createCPG(name, optional)
        except exceptions.HTTPConflict:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_CPG_badDupCPG')
    
    def test_1_create_CPG_badParams(self):
        self.printHeader('create_CPG_badParams')

        #add one
        try:
            optional = {'domain': 'UNIT_TEST'}
            more_optional = {'LDLayout':{'RAIDBadType':1}}
            optional.update(more_optional)
            name = 'UnitTestCPGbad'
            self.cl.createCPG(name, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_CPG_badParams')
    
    def test_2_get_CPG_Bad(self):
        self.printHeader('get_CPG_Bad')

        try:
            cpg = self.cl.getCPG('BadName')
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_CPG_Bad')
   
    def test_2_get_CPGs(self):
        self.printHeader('get_CPGs')

        try:
            cpgs = self.cl.getCPGs()

            #assert
            name = 'UnitTestCPG'
            cpg1 = self.cl.getCPG(name)
	    name = 'UnitTestCPG2'
            cpg2 = self.cl.getCPG(name)
            self.assertIn(cpg1, cpgs['members'])
            self.assertIn(cpg2, cpgs['members'])
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_CPGs')
    
    def test_3_delete_CPG_NonExist(self):
        self.printHeader('delete_CPG_NonExist')

        try:
            self.cl.deleteCPG('NonExistCPG')
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('delete_CPG_NonExist')
    
    def test_3_delete_CPGs(self):
        self.printHeader('delete_CPGs')

        try:
            cpgs = self.cl.getCPGs()
            if cpgs and cpgs['total'] > 0:
                for cpg in cpgs['members']:
                    if cpg['name'].startswith('UnitTestCPG'):
                        #pprint.pprint("Deleting CPG %s " % cpg['name'])
                        self.cl.deleteCPG(cpg['name'])
            #assert
            try:
                name = 'UnitTestCPG'
                cpg = self.cl.getCPG(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail("Failed with unexpected exception")

            try:
                name = 'UnitTestCPG2'
                cpg = self.cl.getCPG(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail ("Failed with unexpected exception")

        except Exception as ex:
            print ex
            self.fail ("Failed with unexpected exception")

        self.printFooter('delete_CPGs')
   
#testing
suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientCPGTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
