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

"""Test class of 3Par Client handling volume"""

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

class HP3ParClientVolumeTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def test_1_create_volume(self):
        self.printHeader('create_volume')

        try:
            #add one
            name = 'UnitTestVolume'
            cpgName = 'UnitTestCPG'
            optional = {'id': 1, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(name, cpgName, 1024, optional)
            
            #assert
            vol1 = self.cl.getVolume(name)
            self.assertIsNotNone(vol1)
            volName = vol1['name']
            volId = vol1['id']
            self.assertEqual(name, volName)
            self.assertEqual(1, volId)

            #add another
	    name = 'UnitTestVolume2'
            optional = {'id': 2, 'comment': 'test volume2', 'tpvv': True}
            self.cl.createVolume(name, cpgName, 1024, optional)

            #assert
            vol2 = self.cl.getVolume(name)
            self.assertIsNotNone(vol2)
            volName = vol2['name']
            volId = vol2['id']
            self.assertEqual(name, volName)
            self.assertEqual(2, volId)
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_volume')

    
    def test_1_create_volume_toolarge(self):
        self.printHeader('create_volume_badTooLarge')

        #add one
        try:
            name = 'UnitTestVolume3'
            cpgName = 'UnitTestCPG'
            optional = {'id': 3, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(name, cpgName, 10241024, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_volume_badTooLarge')
  
    def test_1_create_volume_dup(self):
        self.printHeader('create_volume_badDup')

        #add one
        try:
            name = 'UnitTestExistingVolume'
            cpgName = 'UnitTestCPG'
            optional = {'id': 4, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(name, cpgName, 1024, optional)
        except exceptions.HTTPConflict:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_volume_badDup')
    
    def test_1_create_volume_badParams(self):
        self.printHeader('create_volume_badParams')

        #add one
        try:
            name = 'UnitTestBadVolume'
            cpgName = 'UnitTestCPG'
            optional = {'id': 4, 'comment': 'test volume', 'badPram': True}
            self.cl.createVolume(name, cpgName, 1024, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_volume_badParams')
    
    def test_2_get_volume_bad(self):
        self.printHeader('get_volume_bad')

        try:
            cpg = self.cl.getVolume('BadName')
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_volume_bad')
   
    def test_2_get_volumes(self):
        self.printHeader('get_volumes')

        try:
            vols = self.cl.getVolumes()

            #assert
            name = 'UnitTestVolume'
            vol1 = self.cl.getVolume(name)
	    name = 'UnitTestVolume2'
            vol2 = self.cl.getVolume(name)
            self.assertIn(vol1, vols['members'])
            self.assertIn(vol2, vols['members'])
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_volumes')
    
    def test_3_delete_volume_nonExist(self):
        self.printHeader('delete_volume_nonExist')

        try:
            self.cl.deleteVolume('NonExistVolume')
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('delete_volume_nonExist')
    
    def test_3_delete_volumes(self):
        self.printHeader('delete_volumes')

        try:
            volumes = self.cl.getVolumes()
            if volumes and volumes['total'] > 0:
                for vol in volumes['members']:
                    if vol['name'].startswith('UnitTestVolume'):
                        self.cl.deleteVolume(vol['name'])
            #assert
            try:
                name = 'UnitTestVolume'
                vol = self.cl.getVolume(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail("Failed with unexpected exception")

            try:
                name = 'UnitTestVolume2'
                vol = self.cl.getVolume(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail ("Failed with unexpected exception")

        except Exception as ex:
            print ex
            self.fail ("Failed with unexpected exception")

        self.printFooter('delete_volumes')
   
#testing
suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientVolumeTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
