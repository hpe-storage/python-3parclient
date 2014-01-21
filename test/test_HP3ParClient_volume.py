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
            optional = {'comment': 'test volume', 'tpvv': True}
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
            self.assertEqual(VOLUME_NAME1, volName)

        except Exception as ex:
            print ex
            self.fail('Failed to get volume')
            return

        try:
            #add another
            optional = {'comment': 'test volume2', 'tpvv': True}
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
            comment = vol2['comment']
            self.assertEqual(VOLUME_NAME2, volName)
            self.assertEqual("test volume2", comment)
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
            optional = {'comment': 'test volume', 'tpvv': True}
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
            optional = {'id': 10000, 'comment': 'first volume'}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')

        try:
            optional2 = {'id': 10000, 'comment': 'volume with duplicate ID'}
            self.cl.createVolume(VOLUME_NAME2, CPG_NAME2, 1024, optional2)
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

    def test_3_delete_volume_nonExist(self):
        self.printHeader('delete_volume_nonExist')
        try:
            self.cl.deleteVolume(VOLUME_NAME1)
        except exceptions.HTTPNotFound:
            print "Expected exception"
            self.printFooter('delete_volume_nonExist')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail('No exception occurred.')

    def test_3_delete_volumes(self):
        self.printHeader('delete_volumes')

        try:
            optional = {'comment': 'Made by flask.'}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
            self.cl.getVolume(VOLUME_NAME1)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')

        try:
            optional = {'comment': 'Made by flask.'}
            self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, 1024, optional)
            self.cl.getVolume(VOLUME_NAME2)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')

        try:
            self.cl.deleteVolume(VOLUME_NAME1)
        except Exception as ex:
            print ex
            self.fail('Failed to delete %s' % (VOLUME_NAME1))

        try:
            self.cl.getVolume(VOLUME_NAME1)
        except exceptions.HTTPNotFound:
            print 'Expected exception'
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

        try:
            self.cl.deleteVolume(VOLUME_NAME2)
        except Exception as ex:
            print ex
            self.fail('Failed to delete %s' % (VOLUME_NAME2))

        try:
            self.cl.getVolume(VOLUME_NAME2)
        except exceptions.HTTPNotFound:
            print 'Expected exception'
            self.printFooter('delete_volumes')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

    def test_4_create_snapshot(self):
        self.printHeader('create_snapshot')

        try:
            optional = {'snapCPG': CPG_NAME1}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
            #add one
            optional = {'expirationHours': 300}
            self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1, optional)
            #no API to get and check
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.cl.deleteVolume(SNAP_NAME1)
        self.printFooter('create_snapshot')

    def test_4_create_snapshot_badParams(self):
        self.printHeader('create_snapshot_badParams')
        #add one
        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        try:
            optional = {'Bad': True, 'expirationHours': 300}
            self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1, optional)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            self.printFooter('create_snapshot_badParams')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail("No exception occurred.")

    def test_4_create_snapshot_nonExistVolume(self):
        self.printHeader('create_snapshot_nonExistVolume')

        #add one
        try:
            name = 'UnitTestSnapshot'
            volName = 'NonExistVolume'
            optional = {'id': 1, 'comment': 'test snapshot',
                        'readOnly': True, 'expirationHours': 300}
            self.cl.createSnapshot(name, volName, optional)
        except exceptions.HTTPNotFound:
            print "Expected exception"
            self.printFooter('create_snapshot_nonExistVolume')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail("No exception occurred.")

    def test_5_grow_volume(self):
        self.printHeader('grow_volume')
        try:
            #add one
            optional = {'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')
            return

        try:
            #grow it
            result = self.cl.growVolume(VOLUME_NAME1, 1)
        except Exception as ex:
            print ex
            self.fail('Failed to grow volume')
            return

        try:
            result = self.cl.getVolume(VOLUME_NAME1)
            size_after = result['sizeMiB']
            self.assertGreater(size_after, 1024)
        except Exception as ex:
            print ex
            self.fail('Failed to get volume after growth')
            return

        self.printFooter('grow_volume')

    def test_5_grow_volume_bad(self):
        self.printHeader('grow_volume_bad')

        try:
            #add one
            optional = {'comment': 'test volume', 'tpvv': True}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')
            return

        try:
            #shrink it
            self.cl.growVolume(VOLUME_NAME1, -1)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
            self.printFooter('grow_volume_bad')
            return
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.fail("No exception occurred.")

    def test_6_copy_volume(self):
        self.printHeader('copy_volume')

        try:
            #add one
            optional = {'comment': 'test volume', 'tpvv': True,
                        'snapCPG': CPG_NAME1}
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to create volume')
            return

        try:
            #copy it
            optional = {'online': True, 'destCPG': CPG_NAME1}
            self.cl.copyVolume(VOLUME_NAME1, VOLUME_NAME2, optional)
        except Exception as ex:
            print ex
            self.fail('Failed to copy volume')
            return

        try:
            result = self.cl.getVolume(VOLUME_NAME2)
        except Exception as ex:
            print ex
            self.fail('Failed to get cloned volume')
            return

        self.printFooter('copy_volume')

#testing
#suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientVolumeTestCase)
#unittest.TextTestRunner(verbosity=2).run(suite)
