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

"""Test class of 3Par Client handling volume & snapshot """

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

CPG_NAME1 = 'CPG1_UNIT_TEST'
CPG_NAME2 = 'CPG2_UNIT_TEST'
VOLUME_NAME1 = 'VOLUME1_UNIT_TEST'
VOLUME_NAME2 = 'VOLUME2_UNIT_TEST'
SNAP_NAME1 = 'SNAP_UNIT_TEST'

class HP3ParClientVolumeTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):
    
    def setUp(self):
        super(HP3ParClientVolumeTestCase, self).setUp()
        
        try :
            self.cl.createCPG(CPG_NAME1)
        except :
            pass
        try :
            self.cl.createCPG(CPG_NAME2)
        except :
            pass
        
        
    def tearDown(self):

        try :
            self.cl.deleteVolume(VOLUME_NAME1)
        except :
            pass
        try :
            self.cl.deleteVolume(VOLUME_NAME2)
        except :
            pass   
        try :
            self.cl.deleteCPG(CPG_NAME1)
        except :
            pass
        try :
            self.cl.deleteCPG(CPG_NAME2)
        except :
            pass              

        super(HP3ParClientVolumeTestCase, self).tearDown()    

    def test_1_create_volume(self):
        self.printHeader('create_volume')

        try:
            #add one
            optional = {'id': 1, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')
            return

        try:
            #check
            vol1 = self.cl.getVolume(VOLUME_NAME1)
            self.assertIsNotNone(vol1)
            volName = vol1['name']
            volId = vol1['id']
            self.assertEqual(VOLUME_NAME1, volName)
            self.assertEqual(1, volId)

        except Exception as ex:
            print ex
            self.fail('Failed to get volume')
            return

        try:
            #add another
            optional = {'id': 2, 'comment': 'test volume2', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME2, CPG_NAME2, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')
            return

        try:
            #check
            vol2 = self.cl.getVolume(VOLUME_NAME2)
            self.assertIsNotNone(vol2)
            volName = vol2['name']
            volId = vol2['id']
            self.assertEqual(VOLUME_NAME2, volName)
            self.assertEqual(2, volId)
        except Exception as ex:
            print ex
            self.fail("Failed to get volume")

        self.printFooter('create_volume')

    def test_1_create_volume_badParams(self):
        self.printHeader('create_volume_badParams')
        try:
            name = VOLUME_NAME1
            cpgName = CPG_NAME1
            optional = {'id': 4, 'comment': 'test volume', 'badPram': True}
            self.cl.createVolume(name, cpgName, 1024, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            self.printFooter('create_volume_badParams')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail('No exception occurred.')

    def test_1_create_volume_duplicate_name(self):
        self.printHeader('create_volume_duplicate_name')

        #add one and check
        try:
            optional = {'id': 4, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail("Failed to create volume")

        try:
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME2, 1024, optional)
        except exceptions.HTTPConflict:
            print "Expected exception"
            self.printFooter('create_volume_duplicate_name')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")
        self.fail('No exception occurred.')
 
    def test_1_create_volume_tooLarge(self):
        self.printHeader('create_volume_tooLarge')
        try:
            optional = {'id': 3, 'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 16777218, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            self.printFooter('create_volume_tooLarge')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail('No exception occurred')

    def test_1_create_volume_duplicate_ID(self):
        self.printHeader('create_volume_duplicate_ID')
        try:
            optional = {'id': 1, 'comment': 'first volume'}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')

        try:
            optional2 = {'id': 1, 'comment': 'volume with duplicate ID'}
            self.cl.createVolume(VOLUME_NAME2, CPG_NAME2, 1024, optional)
        except exceptions.HTTPConflict:
            print 'Expected exception'
            self.printFooter('create_volume_duplicate_ID')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

        self.fail('No exception occurred')
 
    def test_1_create_volume_longName(self):
        self.printHeader('create_volume_longName')
        try:
            optional = {'id': 5}
            LongName = 'ThisVolumeNameIsWayTooLongToMakeAnySenseAndIsDeliberatelySo'
            self.cl.createVolume(LongName, CPG_NAME1, 1024, optional)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('create_volume_longName')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

        self.fail('No exception occurred.')

    def test_2_get_volume_bad(self):
        self.printHeader('get_volume_bad')
 
        try:
            self.cl.getVolume('NoSuchVolume')
        except exceptions.HTTPNotFound:
            print "Expected exception"
            self.printFooter('get_volume_bad')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail("No exception occurred")

    def test_2_get_volumes(self):
        self.printHeader('get_volumes')
 
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024)
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, 1024)

        vol1 = self.cl.getVolume(VOLUME_NAME1)            
        vol2 = self.cl.getVolume(VOLUME_NAME2)   

        vols = self.cl.getVolumes() 

        self.assertTrue(self.findInDict(vols['members'], 'name', vol1['name']))
        self.assertTrue(self.findInDict(vols['members'], 'name', vol2['name']))          
 
        self.printFooter('get_volumes')

#     def test_3_delete_volume_nonExist(self):
#         self.printHeader('delete_volume_nonExist')
# 
#         try:
#             self.cl.deleteVolume('NonExistVolume')
#         except exceptions.HTTPNotFound:
#             print "Expected exception"
#         except Exception as ex:
#             print ex
#             self.fail("Failed with unexpected exception")
# 
#         self.printFooter('delete_volume_nonExist')
#     
#     def test_3_delete_volumes(self):
#         self.printHeader('delete_volumes')
# 
#         try:
#             volumes = self.cl.getVolumes()
#             if volumes and volumes['total'] > 0:
#                 for vol in volumes['members']:
#                     if vol['name'].startswith('UnitTestVolume'):
#                         self.cl.deleteVolume(vol['name'])
#             #check
#             try:
#                 name = 'UnitTestVolume'
#                 vol = self.cl.getVolume(name)
#             except exceptions.HTTPNotFound:
#                 print "Expected exception"
#             except Exception as ex:
#                 print ex
#                 self.fail("Failed with unexpected exception")
# 
#             try:
#                 name = 'UnitTestVolume2'
#                 vol = self.cl.getVolume(name)
#             except exceptions.HTTPNotFound:
#                 print "Expected exception"
#             except Exception as ex:
#                 print ex
#                 self.fail ("Failed with unexpected exception")
# 
#         except Exception as ex:
#             print ex
#             self.fail ("Failed with unexpected exception")
# 
#         self.printFooter('delete_volumes')
# 
#     def test_4_create_snapshot(self):
#         self.printHeader('create_snapshot')
# 
#         try:
#             optional = {'snapCPG': CPG_NAME1}
#             self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
#             
#             
#             #add one
#             self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1)
#             #no API to get and check 
#         except Exception as ex:
#             print ex
#             self.fail("Failed with unexpected exception")
# 
#         self.cl.deleteVolume(SNAP_NAME1)
#         self.printFooter('create_snapshot')
#    
#     def test_4_create_snapshot_badParams(self):
#         self.printHeader('create_snapshot_badParams')
# 
#         #add one
#         try:
#             name = 'UnitTestSnapshot'
#             volName = 'UnitTestVolume'
#             optional = {'id': 1, 'comment': 'test snapshot', 
#                         'Bad': True, 'expirationHours': 300}
#             self.cl.createSnapshot(name, volName, optional)
#         except exceptions.HTTPBadRequest:
#             print "Expected exception"
#         except Exception as ex:
#             print ex
#             self.fail("Failed with unexpected exception")
# 
#         self.printFooter('create_snapshot_badParams')
# 
#     def test_4_create_snapshot_nonExistVolume(self):
#         self.printHeader('create_snapshot_nonExistVolume')
# 
#         #add one
#         try:
#             name = 'UnitTestSnapshot'
#             volName = 'NonExistVolume'
#             optional = {'id': 1, 'comment': 'test snapshot', 
#                         'readOnly': True, 'expirationHours': 300}
#             self.cl.createSnapshot(name, volName, optional)
#         except exceptions.HTTPNotFound:
#             print "Expected exception"
#         except Exception as ex:
#             print ex
#             self.fail("Failed with unexpected exception")
# 
#         self.printFooter('create_snapshot_nonExistVolume')
#testing
#suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientVolumeTestCase)
#unittest.TextTestRunner(verbosity=2).run(suite)
