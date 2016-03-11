# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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

"""Test class of 3PAR Client handling volume & snapshot."""

import time
import unittest
from testconfig import config

from test import HPE3ParClient_base as hpe3parbase

from hpe3parclient import exceptions

CPG_NAME1 = 'CPG1_UNIT_TEST' + hpe3parbase.TIME
CPG_NAME2 = 'CPG2_UNIT_TEST' + hpe3parbase.TIME
VOLUME_NAME1 = 'VOLUME1_UNIT_TEST' + hpe3parbase.TIME
VOLUME_NAME2 = 'VOLUME2_UNIT_TEST' + hpe3parbase.TIME
VOLUME_NAME3 = 'VOLUME3_UNIT_TEST' + hpe3parbase.TIME
SNAP_NAME1 = 'SNAP_UNIT_TEST1' + hpe3parbase.TIME
SNAP_NAME2 = 'SNAP_UNIT_TEST2' + hpe3parbase.TIME
DOMAIN = 'UNIT_TEST_DOMAIN'
VOLUME_SET_NAME1 = 'VOLUME_SET1_UNIT_TEST' + hpe3parbase.TIME
VOLUME_SET_NAME2 = 'VOLUME_SET2_UNIT_TEST' + hpe3parbase.TIME
VOLUME_SET_NAME3 = 'VOLUME_SET3_UNIT_TEST' + hpe3parbase.TIME
SIZE = 512
REMOTE_COPY_GROUP_NAME1 = 'RCG1_UNIT_TEST' + hpe3parbase.TIME
REMOTE_COPY_GROUP_NAME2 = 'RCG2_UNIT_TEST' + hpe3parbase.TIME
REMOTE_COPY_TARGETS = [{"targetName": "testTarget",
                        "mode": 2,
                        "roleReversed": False,
                        "groupLastSyncTime": None}]
RC_VOLUME_NAME = 'RC_VOLUME1_UNIT_TEST' + hpe3parbase.TIME
SKIP_RCOPY_MESSAGE = ("Only works with flask server.")
SKIP_FLASK_RCOPY_MESSAGE = ("Remote copy is not configured to be tested "
                            "on live arrays.")
RCOPY_STARTED = 3
RCOPY_STOPPED = 5
FAILOVER_GROUP = 7
RESTORE_GROUP = 10


def is_live_test():
    return config['TEST']['unit'].lower() == 'false'


def no_remote_copy():
    unit_test = config['TEST']['unit'].lower() == 'false'
    remote_copy = config['TEST']['run_remote_copy'].lower() == 'true'
    run_remote_copy = not remote_copy or not unit_test
    return run_remote_copy


class HPE3ParClientVolumeTestCase(hpe3parbase.HPE3ParClientBaseTestCase):

    def setUp(self):
        super(HPE3ParClientVolumeTestCase, self).setUp(withSSH=True)

        optional = self.CPG_OPTIONS
        try:
            self.cl.createCPG(CPG_NAME1, optional)
        except Exception:
            pass
        try:
            self.cl.createCPG(CPG_NAME2, optional)
        except Exception:
            pass
        try:
            self.secondary_cl.createCPG(CPG_NAME1, optional)
        except Exception:
            pass
        try:
            self.secondary_cl.createCPG(CPG_NAME2, optional)
        except Exception:
            pass

    def tearDown(self):

        try:
            self.cl.deleteVolume(SNAP_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteVolume(SNAP_NAME2)
        except Exception:
            pass
        try:
            self.cl.deleteVolumeSet(VOLUME_SET_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteVolumeSet(VOLUME_SET_NAME2)
        except Exception:
            pass
        try:
            self.cl.deleteVolumeSet(VOLUME_SET_NAME3)
        except Exception:
            pass
        try:
            self.cl.deleteVolume(VOLUME_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteVolume(VOLUME_NAME2)
        except Exception:
            pass
        try:
            self.cl.deleteVolume(VOLUME_NAME3)
        except Exception:
            pass
        try:
            self.cl.deleteCPG(CPG_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteCPG(CPG_NAME2)
        except Exception:
            pass
        try:
            self.cl.stopRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        except Exception:
            pass
        try:
            self.cl.removeVolumeFromRemoteCopyGroup(
                REMOTE_COPY_GROUP_NAME1, RC_VOLUME_NAME, removeFromTarget=True)
        except Exception:
            pass
        try:
            self.cl.removeRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteVolume(RC_VOLUME_NAME)
        except Exception:
            pass
        try:
            self.secondary_cl.deleteVolume(RC_VOLUME_NAME)
        except Exception:
            pass
        try:
            self.secondary_cl.deleteCPG(CPG_NAME1)
        except Exception:
            pass
        try:
            self.secondary_cl.deleteCPG(CPG_NAME2)
        except Exception:
            pass

        super(HPE3ParClientVolumeTestCase, self).tearDown()

    def test_1_create_volume(self):
        self.printHeader('create_volume')

        # add one
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # check
        vol1 = self.cl.getVolume(VOLUME_NAME1)
        self.assertIsNotNone(vol1)
        volName = vol1['name']
        self.assertEqual(VOLUME_NAME1, volName)

        # add another
        optional = {'comment': 'test volume2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME2, SIZE, optional)

        # check
        vol2 = self.cl.getVolume(VOLUME_NAME2)
        self.assertIsNotNone(vol2)
        volName = vol2['name']
        comment = vol2['comment']
        self.assertEqual(VOLUME_NAME2, volName)
        self.assertEqual("test volume2", comment)

        self.printFooter('create_volume')

    def test_1_create_volume_badParams(self):
        self.printHeader('create_volume_badParams')

        name = VOLUME_NAME1
        cpgName = CPG_NAME1
        optional = {'id': 4, 'comment': 'test volume', 'badPram': True}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.createVolume,
            name,
            cpgName,
            SIZE,
            optional)

        self.printFooter('create_volume_badParams')

    def test_1_create_volume_duplicate_name(self):
        self.printHeader('create_volume_duplicate_name')

        # add one and check
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.createVolume,
            VOLUME_NAME1,
            CPG_NAME2,
            SIZE,
            optional
        )

        self.printFooter('create_volume_duplicate_name')

    def test_1_create_volume_tooLarge(self):
        self.printHeader('create_volume_tooLarge')

        optional = {'id': 3, 'comment': 'test volume', 'tpvv': True}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.createVolume,
            VOLUME_NAME1,
            CPG_NAME1,
            16777218,
            optional
        )

        self.printFooter('create_volume_tooLarge')

    def test_1_create_volume_duplicate_ID(self):
        self.printHeader('create_volume_duplicate_ID')

        optional = {'id': 10000, 'comment': 'first volume'}
        optional2 = {'id': 10000, 'comment': 'volume with duplicate ID'}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.createVolume,
            VOLUME_NAME2,
            CPG_NAME2,
            SIZE,
            optional2
        )

        self.printFooter('create_volume_duplicate_ID')

    def test_1_create_volume_longName(self):
        self.printHeader('create_volume_longName')

        optional = {'id': 5}
        LongName = ('ThisVolumeNameIsWayTooLongToMakeAnySenseAndIs'
                    'DeliberatelySo')
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.createVolume,
            LongName,
            CPG_NAME1,
            SIZE,
            optional
        )

        self.printFooter('create_volume_longName')

    def test_2_get_volume_bad(self):
        self.printHeader('get_volume_bad')

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getVolume,
            'NoSuchVolume'
        )

        self.printFooter('get_volume_bad')

    def test_2_get_volumes(self):
        self.printHeader('get_volumes')

        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE)
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE)

        vol1 = self.cl.getVolume(VOLUME_NAME1)
        vol2 = self.cl.getVolume(VOLUME_NAME2)

        vols = self.cl.getVolumes()

        self.assertTrue(self.findInDict(vols['members'], 'name', vol1['name']))
        self.assertTrue(self.findInDict(vols['members'], 'name', vol2['name']))

        self.printFooter('get_volumes')

    def test_3_delete_volume_nonExist(self):
        self.printHeader('delete_volume_nonExist')

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.deleteVolume,
            VOLUME_NAME1
        )

        self.printFooter('delete_volume_nonExist')

    def test_3_delete_volumes(self):
        self.printHeader('delete_volumes')

        optional = {'comment': 'Made by flask.'}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        self.cl.getVolume(VOLUME_NAME1)

        optional = {'comment': 'Made by flask.'}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)
        self.cl.getVolume(VOLUME_NAME2)

        self.cl.deleteVolume(VOLUME_NAME1)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getVolume,
            VOLUME_NAME1
        )

        self.cl.deleteVolume(VOLUME_NAME2)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getVolume,
            VOLUME_NAME2
        )

        self.printFooter('delete_volumes')

    def test_4_create_snapshot_no_optional(self):
        self.printHeader('create_snapshot_no_optional')

        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        # add one
        self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1)
        # no API to get and check

        self.cl.deleteVolume(SNAP_NAME1)

        self.printFooter('create_snapshot_no_optional')

    def test_4_create_snapshot(self):
        self.printHeader('create_snapshot')

        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        # add one
        optional = {'expirationHours': 300}
        self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1, optional)
        # no API to get and check

        self.cl.deleteVolume(SNAP_NAME1)

        self.printFooter('create_snapshot')

    def test_4_create_snapshot_badParams(self):
        self.printHeader('create_snapshot_badParams')

        # add one
        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        optional = {'Bad': True, 'expirationHours': 300}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.createSnapshot,
            SNAP_NAME1,
            VOLUME_NAME1,
            optional
        )

        self.printFooter('create_snapshot_badParams')

    def test_4_create_snapshot_nonExistVolume(self):
        self.printHeader('create_snapshot_nonExistVolume')

        # add one
        name = 'UnitTestSnapshot'
        volName = 'NonExistVolume'
        optional = {'id': 1, 'comment': 'test snapshot',
                    'readOnly': True, 'expirationHours': 300}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.createSnapshot,
            name,
            volName,
            optional
        )

        self.printFooter('create_snapshot_nonExistVolume')

    def test_5_grow_volume(self):
        self.printHeader('grow_volume')

        # add one
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # grow it
        result = self.cl.growVolume(VOLUME_NAME1, 1)

        result = self.cl.getVolume(VOLUME_NAME1)
        size_after = result['sizeMiB']
        self.assertGreater(size_after, SIZE)

        self.printFooter('grow_volume')

    def test_5_grow_volume_bad(self):
        self.printHeader('grow_volume_bad')

        # add one
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # shrink it
        # 3par is returning 409 instead of 400
        self.assertRaises(
            (exceptions.HTTPBadRequest, exceptions.HTTPConflict),
            self.cl.growVolume,
            VOLUME_NAME1,
            -1
        )

        self.printFooter('grow_volume_bad')

    def test_6_copy_volume(self):
        self.printHeader('copy_volume')

        # TODO: Add support for ssh/stopPhysical copy in mock mode
        if self.unitTest:
            self.printFooter('copy_volume')
            return

        # add one
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # copy it
        optional = {'online': True}
        self.cl.copyVolume(VOLUME_NAME1, VOLUME_NAME2, CPG_NAME1, optional)
        self.cl.getVolume(VOLUME_NAME2)
        self.cl.stopOnlinePhysicalCopy(VOLUME_NAME2)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getVolume,
            VOLUME_NAME2
        )

        self.printFooter('copy_volume')

    def test_7_copy_volume_failure(self):
        self.printHeader('copy_volume_failure')

        # add one
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)

        optional = {'online': False, 'tpvv': True}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.copyVolume,
            VOLUME_NAME1,
            VOLUME_NAME2,
            CPG_NAME1,
            optional)

        optional = {'online': False, 'tpdd': True}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.copyVolume,
            VOLUME_NAME1,
            VOLUME_NAME2,
            CPG_NAME1,
            optional)

        # destCPG isn't allowed to go to the 3PAR during an
        # offline copy.  The client strips it out, so this should pass
        optional = {'online': False, 'destCPG': 'test'}
        self.cl.copyVolume(VOLUME_NAME1, VOLUME_NAME2, CPG_NAME1, optional)
        self.cl.getVolume(VOLUME_NAME2)
        self.cl.deleteVolume(VOLUME_NAME2)
        self.cl.deleteVolume(VOLUME_NAME1)

        self.printFooter('copy_volume_failure')

    def test_7_create_volume_set(self):
        self.printHeader('create_volume_set')

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")

        resp = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        print(resp)

        self.printFooter('create_volume_set')

    def test_7_create_volume_set_with_volumes(self):
        self.printHeader('create_volume_set')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)

        members = [VOLUME_NAME1, VOLUME_NAME2]
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1",
                                setmembers=members)

        resp = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        self.assertIsNotNone(resp)
        resp_members = resp['setmembers']
        self.assertIn(VOLUME_NAME1, resp_members)
        self.assertIn(VOLUME_NAME2, resp_members)

        self.printFooter('create_volume_set')

    def test_7_create_volume_set_dup(self):
        self.printHeader('create_volume_set_dup')

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")

        # create it again
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.createVolumeSet,
            VOLUME_SET_NAME1,
            domain=self.DOMAIN,
            comment="Unit test volume set 1"
        )

        self.printFooter('create_volume_set_dup')

    def test_8_get_volume_sets(self):
        self.printHeader('get_volume_sets')

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")
        self.cl.createVolumeSet(VOLUME_SET_NAME2, domain=self.DOMAIN)

        sets = self.cl.getVolumeSets()
        self.assertIsNotNone(sets)
        set_names = [vset['name'] for vset in sets['members']]

        self.assertIn(VOLUME_SET_NAME1, set_names)
        self.assertIn(VOLUME_SET_NAME2, set_names)

        self.printFooter('get_volume_sets')

    def test_8_find_all_volume_sets(self):
        self.printHeader('find_all_volume_sets')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, 1024, optional)
        optional = {'comment': 'test volume 3', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME3, CPG_NAME1, 1024, optional)

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")
        self.cl.createVolumeSet(VOLUME_SET_NAME2,
                                domain=self.DOMAIN,
                                comment="Unit test volume set 2",
                                setmembers=[VOLUME_NAME1])
        self.cl.createVolumeSet(VOLUME_SET_NAME3,
                                domain=self.DOMAIN,
                                comment="Unit test volume set 3",
                                setmembers=[VOLUME_NAME1, VOLUME_NAME2])

        sets = self.cl.findAllVolumeSets(VOLUME_NAME1)
        self.assertIsNotNone(sets)
        set_names = [vset['name'] for vset in sets]

        self.assertIn(VOLUME_SET_NAME2, set_names)
        self.assertIn(VOLUME_SET_NAME3, set_names)
        self.assertNotIn(VOLUME_SET_NAME1, set_names)

        sets = self.cl.findAllVolumeSets(VOLUME_NAME3)
        expected = []
        self.assertEqual(sets, expected)

        self.printFooter('find_all_volume_sets')

    def test_8_find_volume_set(self):
        self.printHeader('find_volume_set')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, 1024, optional)
        optional = {'comment': 'test volume 3', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME3, CPG_NAME1, 1024, optional)

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")
        self.cl.createVolumeSet(VOLUME_SET_NAME2,
                                domain=self.DOMAIN,
                                comment="Unit test volume set 2",
                                setmembers=[VOLUME_NAME1])
        self.cl.createVolumeSet(VOLUME_SET_NAME3,
                                domain=self.DOMAIN,
                                comment="Unit test volume set 3",
                                setmembers=[VOLUME_NAME1, VOLUME_NAME2])

        result = self.cl.findVolumeSet(VOLUME_NAME1)
        self.assertEqual(result, VOLUME_SET_NAME2)

        # Check that None is returned if no volume sets are found.
        result = self.cl.findVolumeSet(VOLUME_NAME3)
        self.assertIsNone(result)

        self.printFooter('find_volumet_set')

    def test_9_del_volume_set_empty(self):
        self.printHeader('del_volume_set_empty')

        self.cl.createVolumeSet(VOLUME_SET_NAME2, domain=self.DOMAIN)
        self.cl.deleteVolumeSet(VOLUME_SET_NAME2)

        self.printFooter('del_volume_set_empty')

    def test_9_del_volume_set_with_volumes(self):
        self.printHeader('delete_volume_set_with_volumes')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)

        members = [VOLUME_NAME1, VOLUME_NAME2]
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1",
                                setmembers=members)

        self.cl.deleteVolumeSet(VOLUME_SET_NAME1)

        self.printFooter('delete_volume_set_with_volumes')

    def test_10_modify_volume_set_change_name(self):
        self.printHeader('modify_volume_set_change_name')

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="First")
        self.cl.modifyVolumeSet(VOLUME_SET_NAME1,
                                newName=VOLUME_SET_NAME2)
        vset = self.cl.getVolumeSet(VOLUME_SET_NAME2)
        self.assertEqual("First", vset['comment'])

        self.printFooter('modify_volume_set_change_name')

    def test_10_modify_volume_set_change_comment(self):
        self.printHeader('modify_volume_set_change_comment')

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="First")
        self.cl.modifyVolumeSet(VOLUME_SET_NAME1,
                                comment="Second")
        vset = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        self.assertEqual("Second", vset['comment'])

        self.printFooter('modify_volume_set_change_comment')

    def test_10_modify_volume_set_change_flash_cache(self):
        self.printHeader('modify_volume_set_change_flash_cache')

        try:
            self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                    comment="First")
            self.cl.modifyVolumeSet(
                VOLUME_SET_NAME1,
                flashCachePolicy=self.cl.FLASH_CACHE_ENABLED)
            vset = self.cl.getVolumeSet(VOLUME_SET_NAME1)
            self.assertEqual(self.cl.FLASH_CACHE_ENABLED,
                             vset['flashCachePolicy'])

            self.cl.modifyVolumeSet(
                VOLUME_SET_NAME1,
                flashCachePolicy=self.cl.FLASH_CACHE_DISABLED)
            vset = self.cl.getVolumeSet(VOLUME_SET_NAME1)
            self.assertEqual(self.cl.FLASH_CACHE_DISABLED,
                             vset['flashCachePolicy'])
        except exceptions.HTTPBadRequest:
            # means we are on a server that doesn't support FlashCachePolicy
            # pre 3.2.1 MU2
            pass
        except exceptions.HTTPNotFound as e:
            # Pass if server doesn't have flash cache
            # Not found (HTTP 404) 285 - Flash cache does not exist
            if e.get_code() == 285:
                pass
            else:
                raise

        self.printFooter('modify_volume_set_change_flash_cache')

    def test_10_modify_volume_set_add_members_to_empty(self):
        self.printHeader('modify_volume_set_add_members_to_empty')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)

        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1")

        members = [VOLUME_NAME1, VOLUME_NAME2]
        self.cl.modifyVolumeSet(VOLUME_SET_NAME1, self.cl.SET_MEM_ADD,
                                setmembers=members)

        resp = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        print(resp)
        self.assertTrue(VOLUME_NAME1 in resp['setmembers'])
        self.assertTrue(VOLUME_NAME2 in resp['setmembers'])

        self.printFooter('modify_volume_set_add_members_to_empty')

    def test_10_modify_volume_set_add_members(self):
        self.printHeader('modify_volume_set_add_members')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)

        members = [VOLUME_NAME1]
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                setmembers=members,
                                comment="Unit test volume set 1")

        members = [VOLUME_NAME2]
        self.cl.modifyVolumeSet(VOLUME_SET_NAME1, self.cl.SET_MEM_ADD,
                                setmembers=members)

        resp = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        print(resp)
        self.assertTrue(VOLUME_NAME1 in resp['setmembers'])
        self.assertTrue(VOLUME_NAME2 in resp['setmembers'])

        self.printFooter('modify_volume_set_add_members')

    def test_10_modify_volume_set_del_members(self):
        self.printHeader('modify_volume_del_members')

        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)
        members = [VOLUME_NAME1, VOLUME_NAME2]
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1",
                                setmembers=members)

        members = [VOLUME_NAME1]
        self.cl.modifyVolumeSet(VOLUME_SET_NAME1,
                                action=self.cl.SET_MEM_REMOVE,
                                setmembers=members)

        resp = self.cl.getVolumeSet(VOLUME_SET_NAME1)
        self.assertIsNotNone(resp)
        resp_members = resp['setmembers']
        self.assertNotIn(VOLUME_NAME1, resp_members)
        self.assertIn(VOLUME_NAME2, resp_members)

        self.printFooter('modify_volume_del_members')

    def _create_vv_sets(self):
        optional = {'comment': 'test volume 1', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)
        optional = {'comment': 'test volume 2', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, SIZE, optional)
        members = [VOLUME_NAME1, VOLUME_NAME2]
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=self.DOMAIN,
                                comment="Unit test volume set 1",
                                setmembers=members)

    def test_11_add_qos(self):
        self.printHeader('add_qos')

        self._create_vv_sets()
        qos = {'bwMinGoalKB': 1024,
               'bwMaxLimitKB': 1024}

        self.cl.createQoSRules(VOLUME_SET_NAME1, qos)
        rule = self.cl.queryQoSRule(VOLUME_SET_NAME1)

        self.assertIsNotNone(rule)
        self.assertEquals(rule['bwMinGoalKB'], qos['bwMinGoalKB'])
        self.assertEquals(rule['bwMaxLimitKB'], qos['bwMaxLimitKB'])

        self.printFooter('add_qos')

    def test_12_modify_qos(self):
        self.printHeader('modify_qos')

        self._create_vv_sets()
        qos_before = {'bwMinGoalKB': 1024,
                      'bwMaxLimitKB': 1024}
        qos_after = {'bwMinGoalKB': 1024,
                     'bwMaxLimitKB': 2048}

        self.cl.createQoSRules(VOLUME_SET_NAME1, qos_before)
        self.cl.modifyQoSRules(VOLUME_SET_NAME1, qos_after)
        rule = self.cl.queryQoSRule(VOLUME_SET_NAME1)

        self.assertIsNotNone(rule)
        self.assertEquals(rule['bwMinGoalKB'], qos_after['bwMinGoalKB'])
        self.assertEquals(rule['bwMaxLimitKB'], qos_after['bwMaxLimitKB'])

        self.printFooter('modify_qos')

    def test_13_delete_qos(self):
        self.printHeader('delete_qos')

        self._create_vv_sets()
        self.cl.createVolumeSet(VOLUME_SET_NAME2)

        qos1 = {'bwMinGoalKB': 1024,
                'bwMaxLimitKB': 1024}
        qos2 = {'bwMinGoalKB': 512,
                'bwMaxLimitKB': 2048}

        self.cl.createQoSRules(VOLUME_SET_NAME1, qos1)
        self.cl.createQoSRules(VOLUME_SET_NAME2, qos2)
        all_qos = self.cl.queryQoSRules()
        self.assertGreaterEqual(all_qos['total'], 2)
        self.assertIn(VOLUME_SET_NAME1,
                      [qos['name'] for qos in all_qos['members']])
        self.assertIn(VOLUME_SET_NAME2,
                      [qos['name'] for qos in all_qos['members']])

        self.cl.deleteQoSRules(VOLUME_SET_NAME1)
        all_qos = self.cl.queryQoSRules()

        self.assertIsNotNone(all_qos)
        self.assertNotIn(VOLUME_SET_NAME1,
                         [qos['name'] for qos in all_qos['members']])
        self.assertIn(VOLUME_SET_NAME2,
                      [qos['name'] for qos in all_qos['members']])

        self.printFooter('delete_qos')

    def test_14_modify_volume_rename(self):
        self.printHeader('modify volume')

        # add one
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        volumeMod = {'newName': VOLUME_NAME2}
        self.cl.modifyVolume(VOLUME_NAME1, volumeMod)
        vol2 = self.cl.getVolume(VOLUME_NAME2)
        self.assertIsNotNone(vol2)
        self.assertEqual(vol2['comment'], optional['comment'])

        self.printFooter('modify volume')

    def test_15_set_volume_metadata(self):
        self.printHeader('set volume metadata')

        optional = {'comment': 'test volume', 'tpvv': True}
        expected_value = 'test_val'
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', expected_value)
        result = self.cl.getVolumeMetaData(VOLUME_NAME1, 'test_key')
        self.assertEqual(result['value'], expected_value)

        self.printFooter('set volume metadata')

    def test_15_set_bad_volume_metadata(self):
        self.printHeader('set bad volume metadata')

        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.setVolumeMetaData,
                          'Fake_Volume',
                          'test_key',
                          'test_val')

        self.printFooter('set bad volume metadata')

    def test_15_set_volume_metadata_existing_key(self):
        self.printHeader('set volume metadata existing key')

        optional = {'comment': 'test volume', 'tpvv': True}
        expected = 'new_test_val'
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', 'test_val')
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', 'new_test_val')
        contents = self.cl.getVolumeMetaData(VOLUME_NAME1, 'test_key')
        self.assertEqual(contents['value'], expected)

        self.printFooter('set volume metadata existing key')

    def test_15_set_volume_metadata_invalid_length(self):
        self.printHeader('set volume metadata invalid length')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)

        # Some backends have a key limit of 31 characters while and other
        # are larger
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.setVolumeMetaData,
                          VOLUME_NAME1,
                          'this_key_will_cause_an_exception ' 'x' * 256,
                          'test_val')

        self.printFooter('set volume metadata invalid length')

    def test_15_set_volume_metadata_invalid_data(self):
        self.printHeader('set volume metadata invalid data')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.setVolumeMetaData,
                          VOLUME_NAME1,
                          None,
                          'test_val')

        self.printFooter('set volume metadata invalid data')

    def test_16_get_volume_metadata(self):
        self.printHeader('get volume metadata')

        optional = {'comment': 'test volume', 'tpvv': True}
        expected_value = 'test_val'
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', expected_value)
        result = self.cl.getVolumeMetaData(VOLUME_NAME1, 'test_key')
        self.assertEqual(expected_value, result['value'])

        self.printFooter('get volume metadata')

    def test_16_get_volume_metadata_missing_volume(self):
        self.printHeader('get volume metadata missing volume')

        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.getVolumeMetaData,
                          'Fake_Volume',
                          'bad_key')

        self.printFooter('get volume metadata missing volume')

    def test_16_get_volume_metadata_missing_key(self):
        self.printHeader('get volume metadata missing key')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.getVolumeMetaData,
                          VOLUME_NAME1,
                          'bad_key')

        self.printFooter('get volume metadata missing key')

    def test_16_get_volume_metadata_invalid_input(self):
        self.printHeader('get volume metadata invalid input')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.getVolumeMetaData,
                          VOLUME_NAME1,
                          '&')

        self.printFooter('get volume metadata invalid input')

    def test_17_get_all_volume_metadata(self):
        self.printHeader('get all volume metadata')

        # Keys present in metadata
        optional = {'comment': 'test volume', 'tpvv': True}
        expected_value_1 = 'test_val'
        expected_value_2 = 'test_val2'
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1,
                                  'test_key_1',
                                  expected_value_1)
        self.cl.setVolumeMetaData(VOLUME_NAME1,
                                  'test_key_2',
                                  expected_value_2)
        result = self.cl.getAllVolumeMetaData(VOLUME_NAME1)

        # Key- Value pairs are unordered
        for member in result['members']:
            if member['key'] == 'test_key_1':
                self.assertEqual(expected_value_1, member['value'])
            elif member['key'] == 'test_key_2':
                self.assertEqual(expected_value_2, member['value'])
            else:
                raise Exception("Unexpected member %s" % member)

        # No keys present in metadata
        optional = {'comment': 'test volume', 'tpvv': True}
        expected_value = {'total': 0, 'members': []}
        self.cl.createVolume(VOLUME_NAME2, CPG_NAME1, 1024, optional)
        result = self.cl.getAllVolumeMetaData(VOLUME_NAME2)
        self.assertEqual(expected_value, result)

        self.printFooter('get all volume metadata')

    def test_17_get_all_volume_metadata_missing_volume(self):
        self.printHeader('get all volume metadata missing volume')

        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.getAllVolumeMetaData,
                          'Fake_Volume')

        self.printFooter('get all volume metadata missing volume')

    def test_18_remove_volume_metadata(self):
        self.printHeader('remove volume metadata')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', 'test_val')
        self.cl.removeVolumeMetaData(VOLUME_NAME1, 'test_key')
        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.getVolumeMetaData,
                          VOLUME_NAME1,
                          'test_key')

        self.printFooter('remove volume metadata')

    def test_18_remove_volume_metadata_missing_volume(self):
        self.printHeader('remove volume metadata missing volume')

        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.removeVolumeMetaData,
                          'Fake_Volume',
                          'test_key')

        self.printFooter('remove volume metadata missing volume')

    def test_18_remove_volume_metadata_missing_key(self):
        self.printHeader('remove volume metadata missing key')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.removeVolumeMetaData,
                          VOLUME_NAME1,
                          'test_key')

        self.printFooter('remove volume metadata missing key')

    def test_18_remove_volume_metadata_invalid_input(self):
        self.printHeader('remove volume metadata invalid input')

        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.removeVolumeMetaData,
                          VOLUME_NAME1,
                          '&')

        self.printFooter('remove volume metadata invalid input')

    def test_19_find_volume_metadata(self):
        self.printHeader('find volume metadata')

        # Volume should be found
        optional = {'comment': 'test volume', 'tpvv': True}
        expected = True
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024, optional)
        self.cl.setVolumeMetaData(VOLUME_NAME1, 'test_key', 'test_val')
        result = self.cl.findVolumeMetaData(VOLUME_NAME1,
                                            'test_key',
                                            'test_val')
        self.assertEqual(result, expected)

        # Volume should not be found
        optional = {'comment': 'test volume', 'tpvv': True}
        expected = False
        result = self.cl.findVolumeMetaData(VOLUME_NAME1,
                                            'bad_key',
                                            'test_val')
        self.assertEqual(result, expected)

        self.printFooter('find volume metadata')

    def test_19_find_volume_metadata_missing_volume(self):
        self.printHeader('find volume metadata missing volume')

        expected = False
        result = self.cl.findVolumeMetaData('Fake_Volume',
                                            'test_key',
                                            'test_val')
        self.assertEqual(result, expected)

        self.printFooter('find volume metadata missing volume')

    def test_20_create_vvset_snapshot_no_optional(self):
        self.printHeader('create_vvset_snapshot_no_optional')

        # create volume to add to volume set
        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # create volume set and add a volume to it
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=DOMAIN,
                                setmembers=[VOLUME_NAME1])

        # @count@ is needed by 3PAR to create volume set snapshots. will
        # create SNAP_NAME1-0 format
        self.cl.createSnapshotOfVolumeSet(SNAP_NAME1 + "-@count@",
                                          VOLUME_SET_NAME1)

        # assert snapshot was created
        snap = SNAP_NAME1 + "-0"
        snapshot = self.cl.getVolume(snap)
        self.assertEqual(VOLUME_NAME1, snapshot['copyOf'])

        # cleanup volume snapshot and volume set
        self.cl.deleteVolume(snap)
        self.cl.deleteVolumeSet(VOLUME_SET_NAME1)

        self.printFooter('create_vvset_snapshot_no_optional')

    def test_20_create_vvset_snapshot(self):
        self.printHeader('create_vvset_snapshot')

        # create volume to add to volume set
        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        # create volume set and add a volume to it
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=DOMAIN,
                                setmembers=[VOLUME_NAME1])

        # @count@ is needed by 3PAR to create volume set snapshots. will
        # create SNAP_NAME1-0 format
        optional = {'expirationHours': 300}
        self.cl.createSnapshotOfVolumeSet(SNAP_NAME1 + "-@count@",
                                          VOLUME_SET_NAME1, optional)

        # assert snapshot was created
        snap = SNAP_NAME1 + "-0"
        snapshot = self.cl.getVolume(snap)
        self.assertEqual(VOLUME_NAME1, snapshot['copyOf'])

        # cleanup volume snapshot and volume set
        self.cl.deleteVolume(snap)
        self.cl.deleteVolumeSet(VOLUME_SET_NAME1)

        self.printFooter('create_vvset_snapshot')

    def test_20_create_vvset_snapshot_badParams(self):
        self.printHeader('create_vvset_snapshot_badParams')

        # add one
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=DOMAIN)

        optional = {'Bad': True, 'expirationHours': 300}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.createSnapshotOfVolumeSet,
            SNAP_NAME1,
            VOLUME_SET_NAME1,
            optional
        )

        self.printFooter('create_vvset_snapshot_badParams')

    def test_20_create_vvset_snapshot_nonExistVolumeSet(self):
        self.printHeader('create_vvset_snapshot_nonExistVolume')

        # add one
        name = 'UnitTestVvsetSnapshot'
        volSetName = 'NonExistVolumeSet'
        optional = {'comment': 'test vvset snapshot',
                    'readOnly': True, 'expirationHours': 300}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.createSnapshotOfVolumeSet,
            name,
            volSetName,
            optional
        )

        self.printFooter('create_vvset_snapshot_nonExistVolume')

    def test_20_create_vvset_emptyVolumeSet(self):
        self.printHeader('test_20_create_vvset_emptyVolumeSet')

        name = 'UnitTestVvsetSnapshot'
        self.cl.createVolumeSet(VOLUME_SET_NAME1, domain=DOMAIN)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.createSnapshotOfVolumeSet,
            name,
            VOLUME_SET_NAME1
        )

        self.cl.deleteVolumeSet(VOLUME_SET_NAME1)

        self.printFooter('test_20_create_vvset_emptyVolumeSet')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_create_remote_copy_group(self):
        self.printHeader('create_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        self.printFooter('create_remote_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_delete_remote_copy_group(self):
        self.printHeader('delete_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Delete remote copy group
        self.cl.removeRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getRemoteCopyGroup,
            REMOTE_COPY_GROUP_NAME1
        )

        self.printFooter('create_delete_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_modify_remote_copy_group(self):
        self.printHeader('modify_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        REMOTE_COPY_TARGETS[0]['syncPeriod'] = 300
        self.cl.modifyRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      {'targets': REMOTE_COPY_TARGETS})
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(300, targets[0]['syncPeriod'])

        self.printFooter('modify_remote_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_add_volume_to_remote_copy_group(self):
        self.printHeader('add_volume_to_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        self.printFooter('add_volume_to_remote_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_add_volume_to_remote_copy_group_nonExistVolume(self):
        self.printHeader('add_volume_to_remote_copy_group_nonExistVolume')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Add non existent volume to remote copy group
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.addVolumeToRemoteCopyGroup,
            REMOTE_COPY_GROUP_NAME1,
            'BAD_VOLUME_NAME',
            REMOTE_COPY_TARGETS
        )

        self.printFooter('add_volume_to_remote_copy_group_nonExistVolume')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_remove_volume_from_remote_copy_group(self):
        self.printHeader('remove_volume_from_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        # Remove volume from remote copy group
        self.cl.removeVolumeFromRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                                RC_VOLUME_NAME)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual([], volumes)

        self.printFooter('remove_volume_from_remote_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_start_remote_copy(self):
        self.printHeader('start_remote_copy')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        self.printFooter('start_remote_copy')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_stop_remote_copy(self):
        self.printHeader('stop_remote_copy')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Stop remote copy for the group
        self.cl.stopRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STOPPED, targets[0]['state'])

        self.printFooter('stop_remote_copy')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_synchronize_remote_copy_group(self):
        self.printHeader('synchronize_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Synchronize the remote copy group
        self.cl.synchronizeRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        assert targets[0]['groupLastSyncTime'] is not None

        self.printFooter('synchronize_remote_copy_group')

    @unittest.skipIf(is_live_test(), SKIP_RCOPY_MESSAGE)
    def test_21_failover_remote_copy_group(self):
        self.printHeader('failover_remote_copy_group')

        # Create empty remote copy group
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      REMOTE_COPY_TARGETS,
                                      optional={"domain": DOMAIN})

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE, optional)

        # Add volume to remote copy group
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           REMOTE_COPY_TARGETS)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['name'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Failover remote copy group
        self.cl.recoverRemoteCopyGroupFromDisaster(REMOTE_COPY_GROUP_NAME1,
                                                   FAILOVER_GROUP)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(True, resp['roleReversed'])

        self.printFooter('failover_remote_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_create_remote_copy_group(self):
        self.printHeader('create_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Check remote copy group on the secondary array
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        self.assertEqual(target_rcg_name, resp['name'])

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_delete_remote_copy_group(self):
        self.printHeader('delete_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Check remote copy group on the secondary array
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        self.assertEqual(target_rcg_name, resp['name'])

        # Delete remote copy group
        self.cl.removeRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getRemoteCopyGroup,
            REMOTE_COPY_GROUP_NAME1
        )

        # Check remote copy does not exist on target array
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.secondary_cl.getRemoteCopyGroup,
            REMOTE_COPY_GROUP_NAME1
        )

        self.printFooter('create_delete_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_modify_remote_copy_group(self):
        self.printHeader('modify_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Check remote copy group on the secondary array
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        self.assertEqual(target_rcg_name, resp['name'])

        # Modify the remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'syncPeriod': 300}]
        self.cl.modifyRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      {'targets': targets})
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(300, targets[0]['syncPeriod'])

        # Check modification on target array
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        targets = resp['targets']
        self.assertEqual(300, targets[0]['syncPeriod'])

        self.printFooter('modify_remote_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_add_volume_to_remote_copy_group(self):
        self.printHeader('add_volume_to_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Check remote copy group on the secondary array
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        self.assertEqual(target_rcg_name, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        self.printFooter('add_volume_to_remote_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_add_volume_to_remote_copy_group_nonExistVolume(self):
        self.printHeader('add_volume_to_remote_copy_group_nonExistVolume')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Check remote copy group on the secondary array
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        self.assertEqual(target_rcg_name, resp['name'])

        # Add non existent volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.addVolumeToRemoteCopyGroup,
            REMOTE_COPY_GROUP_NAME1,
            'BAD_VOLUME_NAME',
            targets
        )

        self.printFooter('add_volume_to_remote_copy_group_nonExistVolume')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_remove_volume_from_remote_copy_group(self):
        self.printHeader('remove_volume_from_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        # Remove volume from remote copy group
        self.cl.removeVolumeFromRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                                RC_VOLUME_NAME,
                                                removeFromTarget=True)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual([], volumes)

        # Check volume does not exist on target array
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.secondary_cl.getVolume,
            RC_VOLUME_NAME
        )

        self.printFooter('remove_volume_from_remote_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_start_remote_copy(self):
        self.printHeader('start_remote_copy')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        self.printFooter('start_remote_copy')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_stop_remote_copy(self):
        self.printHeader('start_remote_copy')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Stop remote copy for the group
        self.cl.stopRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STOPPED, targets[0]['state'])

        self.printFooter('start_remote_copy')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_synchronize_remote_copy_group(self):
        self.printHeader('synchronize_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Synchronize the remote copy group
        self.cl.synchronizeRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        assert targets[0]['groupLastSyncTime'] is not None

        self.printFooter('synchronize_remote_copy_group')

    @unittest.skipIf(no_remote_copy(), SKIP_FLASK_RCOPY_MESSAGE)
    def test_22_failover_remote_copy_group(self):
        self.printHeader('failover_remote_copy_group')

        # Create empty remote copy group
        targets = [{"targetName": self.secondary_target_name,
                    "mode": 2,
                    "userCPG": CPG_NAME1,
                    "snapCPG": CPG_NAME1}]
        optional = {'localSnapCPG': CPG_NAME1,
                    'localUserCPG': CPG_NAME1,
                    'domain': DOMAIN}
        self.cl.createRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                      targets,
                                      optional=optional)

        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        self.assertEqual(REMOTE_COPY_GROUP_NAME1, resp['name'])

        # Create volume
        optional = {'comment': 'test volume', 'tpvv': True,
                    'snapCPG': CPG_NAME1}
        self.cl.createVolume(RC_VOLUME_NAME, CPG_NAME1, SIZE,
                             optional)

        # Add volume to remote copy group
        targets = [{'targetName': self.secondary_target_name,
                    'secVolumeName': RC_VOLUME_NAME}]
        optional = {'volumeAutoCreation': True}
        self.cl.addVolumeToRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1,
                                           RC_VOLUME_NAME,
                                           targets,
                                           optional=optional)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        volumes = resp['volumes']
        self.assertEqual(RC_VOLUME_NAME, volumes[0]['localVolumeName'])
        remote_volumes = volumes[0]['remoteVolumes']
        self.assertEqual(RC_VOLUME_NAME, remote_volumes[0]['remoteVolumeName'])

        # Start remote copy for the group
        self.cl.startRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STARTED, targets[0]['state'])

        # Stop remote copy for the group
        self.cl.stopRemoteCopy(REMOTE_COPY_GROUP_NAME1)
        resp = self.cl.getRemoteCopyGroup(REMOTE_COPY_GROUP_NAME1)
        targets = resp['targets']
        self.assertEqual(RCOPY_STOPPED, targets[0]['state'])

        # Failover remote copy group
        info = self.cl.getStorageSystemInfo()
        client_id = str(info['id'])
        target_rcg_name = REMOTE_COPY_GROUP_NAME1 + ".r" + client_id
        self.secondary_cl.recoverRemoteCopyGroupFromDisaster(
            target_rcg_name, FAILOVER_GROUP)
        resp = self.secondary_cl.getRemoteCopyGroup(target_rcg_name)
        targets = resp['targets']
        self.assertEqual(True, targets[0]['roleReversed'])

        # Restore the remote copy group
        self.secondary_cl.recoverRemoteCopyGroupFromDisaster(
            target_rcg_name, RESTORE_GROUP)
        # Let the restore take affect
        time.sleep(10)

        self.printFooter('failover_remote_copy_group')

    def test_23_get_volume_snapshots(self):
        # Create volume and snaphot it
        optional = {'snapCPG': CPG_NAME1}
        self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, SIZE, optional)

        self.cl.createSnapshot(SNAP_NAME1, VOLUME_NAME1)
        self.cl.createSnapshot(SNAP_NAME2, VOLUME_NAME1)

        # Get the volumes snapshots
        snapshots = self.cl.getVolumeSnapshots(VOLUME_NAME1)

        # Set snapshot names. If the test is not against a live array, we
        # need to add the snapshot suffix.
        if not is_live_test():
            snapshots[0] = snapshots[0] + hpe3parbase.TIME
            snapshots[1] = snapshots[1] + hpe3parbase.TIME

        # If the volume has snapshots, their names will be returned as
        # a list
        self.assertEqual([SNAP_NAME1, SNAP_NAME2], snapshots)

        # Test where volume does not exist
        snapshots = self.cl.getVolumeSnapshots("BAD_VOL")
        # An empty list is returned if the volume does not exist
        self.assertEqual([], snapshots)

# testing
# suite = unittest.TestLoader().
#   loadTestsFromTestCase(HPE3ParClientVolumeTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
