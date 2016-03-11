# (c) Copyright 2012-2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Test class of 3PAR Client handling of Host Sets."""
import unittest
from test import HPE3ParClient_base
import random

from hpe3parclient import exceptions

VOLUME_SIZE = 512
EXPORTED_VLUN = 26
HOST_IN_SET = 77
INV_INPUT_PARAM_CONFLICT = 44
LUN_1 = random.randint(1, 10)
LUN_2 = random.randint(1, 10)

# Ensure LUN1 and LUN2 are distinct.
while LUN_1 == LUN_2:
    LUN_2 = random.randint(1, 10)

host_sets_to_delete = []
hosts_to_delete = []
cpgs_to_delete = []
volumes_to_delete = []
vluns_to_delete = []

# Additional test names declared in test cases to account for variation
# in desired name format and aid in manual cleanup.


class HPE3ParClientHostSetTestCase(HPE3ParClient_base
                                   .HPE3ParClientBaseTestCase):

    def setUp(self, withSSH=False):

        super(HPE3ParClientHostSetTestCase, self).setUp(withSSH=False)

    # noinspection PyBroadException
    def tearDown(self):
        """Clean-up -- without fail -- more than humanly possible."""

        for vlun in vluns_to_delete:
            try:
                self.cl.deleteVLUN(*vlun)
            except Exception:
                pass
        del vluns_to_delete[:]

        for volume_name in volumes_to_delete:
            try:
                self.cl.deleteVolume(volume_name)
            except Exception:
                pass
        del volumes_to_delete[:]

        for cpg_name in cpgs_to_delete:
            try:
                self.cl.deleteCPG(cpg_name)
            except Exception:
                pass
        del cpgs_to_delete[:]

        for host_name in hosts_to_delete:
            try:
                self.cl.removeHostFromItsHostSet(host_name)
            except Exception:
                pass
            try:
                self.cl.deleteHost(host_name)
            except Exception:
                pass
        del hosts_to_delete[:]

        for host_set_name in host_sets_to_delete:
            try:
                self.cl.deleteHostSet(host_set_name)
            except Exception:
                pass
        del host_sets_to_delete[:]

        # very last, tear down base class
        super(HPE3ParClientHostSetTestCase, self).tearDown()

    def test_crud_host_without_host_set(self):
        """CRUD test for attach/detach VLUN to host w/o a host set."""
        self.printHeader("crud_host_without_host_set")

        test_prefix = 'UT1_'
        #
        # CREATE
        #
        # Create Host
        host_name = test_prefix + "HOST_" + HPE3ParClient_base.TIME
        hosts_to_delete.append(host_name)

        optional = {'domain': self.DOMAIN}
        self.cl.createHost(host_name, optional=optional)

        # Create CPG
        cpg_name = test_prefix + "CPG_" + HPE3ParClient_base.TIME
        cpgs_to_delete.append(cpg_name)

        optional = self.CPG_OPTIONS
        self.cl.createCPG(cpg_name, optional)

        # Create Volumes
        volume_name1 = test_prefix + "VOL1_" + HPE3ParClient_base.TIME
        volume_name2 = test_prefix + "VOL2_" + HPE3ParClient_base.TIME
        volumes_to_delete.extend([volume_name1, volume_name2])
        self.cl.createVolume(volume_name1, cpg_name, VOLUME_SIZE)
        self.cl.createVolume(volume_name2, cpg_name, VOLUME_SIZE)

        # Create VLUNs
        vlun1 = [volume_name1, LUN_1, host_name, self.port]
        vlun2 = [volume_name2, LUN_2, host_name, self.port]
        vluns_to_delete.extend([vlun1, vlun2])

        self.cl.createVLUN(*vlun1)
        self.cl.createVLUN(*vlun2)

        #
        # READ
        #
        host = self.cl.getHost(host_name)
        self.assertEqual(host['name'], host_name)

        cpg = self.cl.getCPG(cpg_name)
        self.assertEqual(cpg['name'], cpg_name)

        volume = self.cl.getVolume(volume_name1)
        self.assertEqual(volume['name'], volume_name1)

        volume = self.cl.getVolume(volume_name2)
        self.assertEqual(volume['name'], volume_name2)

        host_vluns = self.cl.getHostVLUNs(host_name)
        self.assertIn(volume_name1,
                      [vlun['volumeName'] for vlun in host_vluns])
        self.assertIn(volume_name2,
                      [vlun['volumeName'] for vlun in host_vluns])

        vlun = self.cl.getVLUN(volume_name1)
        self.assertEqual(vlun['volumeName'], volume_name1)
        vlun = self.cl.getVLUN(volume_name2)
        self.assertEqual(vlun['volumeName'], volume_name2)

        #
        # DELETE
        #
        # Try to delete everything in this test as part of the successful test.
        # The tearDown() also tries to cleanup in case of test failure.

        self.cl.deleteVLUN(*vlun1)

        # Make sure that we cannot delete the host while there is still a vlun
        with self.assertRaises(exceptions.HTTPConflict) as cm:
            self.cl.deleteHost(host_name)
        e = cm.exception
        self.assertEqual(e.get_code(), 26)
        self.assertEqual(e.get_description(), "has exported VLUN")

        self.cl.deleteVLUN(*vlun2)

        # Now we can delete the host
        self.cl.deleteHost(host_name)

        # Should be able to clean-up these, too
        self.cl.deleteVolume(volume_name1)
        self.cl.deleteVolume(volume_name2)
        self.cl.deleteCPG(cpg_name)

        self.printFooter("crud_host_without_host_set")

    def test_crud_host_with_host_set(self):
        """CRUD test for attach/detach VLUN to host in host set."""
        self.printHeader("crud_host_with_host_set")

        test_prefix = 'UT2_'

        #
        # CREATE
        #

        # Create Host
        host_name = test_prefix + "HOST_" + HPE3ParClient_base.TIME
        hosts_to_delete.append(host_name)

        optional = {'domain': self.DOMAIN}
        self.cl.createHost(host_name, optional=optional)

        # Create Host Set
        host_set_name = test_prefix + "HOST_SET_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name)
        host_set_id = self.cl.createHostSet(
            host_set_name, self.DOMAIN,
            unittest.TestCase.shortDescription(self), [host_name])
        self.assertEqual(host_set_name, host_set_id)

        # Create CPG
        cpg_name = test_prefix + "CPG_" + HPE3ParClient_base.TIME
        cpgs_to_delete.append(cpg_name)

        optional = self.CPG_OPTIONS
        self.cl.createCPG(cpg_name, optional)

        # Create Volumes
        volume_name1 = test_prefix + "VOL1_" + HPE3ParClient_base.TIME
        volume_name2 = test_prefix + "VOL2_" + HPE3ParClient_base.TIME
        volumes_to_delete.extend([volume_name1, volume_name2])
        self.cl.createVolume(volume_name1, cpg_name, VOLUME_SIZE)
        self.cl.createVolume(volume_name2, cpg_name, VOLUME_SIZE)

        # Create VLUNs
        vlun1 = [volume_name1, LUN_1, host_name, self.port]
        vlun2 = [volume_name2, LUN_2, host_name, self.port]
        vluns_to_delete.extend([vlun1, vlun2])

        self.cl.createVLUN(*vlun1)
        self.cl.createVLUN(*vlun2)

        #
        # READ
        #
        host = self.cl.getHost(host_name)
        self.assertEqual(host['name'], host_name)

        host_sets = self.cl.getHostSets()
        host_set = self.cl.getHostSet(host_set_name)
        found_host_set = self.cl.findHostSet(host_name)
        self.assertIsNotNone(host_sets)
        self.assertIsNotNone(host_set)
        self.assertIsNotNone(found_host_set)
        self.assertEqual(host_set['name'], found_host_set)
        self.assertIn(host_set, host_sets['members'])

        cpg = self.cl.getCPG(cpg_name)
        self.assertEqual(cpg['name'], cpg_name)

        volume = self.cl.getVolume(volume_name1)
        self.assertEqual(volume['name'], volume_name1)

        volume = self.cl.getVolume(volume_name2)
        self.assertEqual(volume['name'], volume_name2)

        host_vluns = self.cl.getHostVLUNs(host_name)
        self.assertIn(volume_name1,
                      [vlun['volumeName'] for vlun in host_vluns])
        self.assertIn(volume_name2,
                      [vlun['volumeName'] for vlun in host_vluns])

        vlun = self.cl.getVLUN(volume_name1)
        self.assertEqual(vlun['volumeName'], volume_name1)
        vlun = self.cl.getVLUN(volume_name2)
        self.assertEqual(vlun['volumeName'], volume_name2)

        #
        # DELETE
        #
        # Try to delete everything in this test as part of the successful test.
        # The tearDown() also tries to cleanup in case of test failure.

        self.cl.deleteVLUN(*vlun1)

        # Make sure that we cannot delete the host while there is still a vlun
        with self.assertRaises(exceptions.HTTPConflict) as cm:
            self.cl.deleteHost(host_name)
        e = cm.exception
        self.assertEqual(e.get_code(), EXPORTED_VLUN)
        self.assertEqual(e.get_description(), "has exported VLUN")

        self.cl.deleteVLUN(*vlun2)

        # Make sure that we cannot delete the host while it is in a host set
        with self.assertRaises(exceptions.HTTPConflict) as cm:
            self.cl.deleteHost(host_name)
        e = cm.exception
        self.assertEqual(e.get_code(), HOST_IN_SET)
        self.assertEqual(e.get_description(), "host is a member of a set")

        self.cl.removeHostFromItsHostSet(host_name)

        # Now we can delete the host
        self.cl.deleteHost(host_name)

        # Should be able to clean-up these too
        self.cl.deleteHostSet(host_set_name)
        self.cl.deleteVolume(volume_name1)
        self.cl.deleteVolume(volume_name2)
        self.cl.deleteCPG(cpg_name)

        self.printFooter("crud_host_with_host_set")

    def test_host_set_name_too_long(self):
        """Host set name too long."""
        self.printHeader("host_set_name_too_long")

        test_prefix = 'UT_'

        # name too long
        host_set_name = (test_prefix + "HOST_SET_NAME_IS_TOOOOOOOOOO_LONG_" +
                         HPE3ParClient_base.TIME)
        host_sets_to_delete.append(host_set_name)

        pre_count = len(self.cl.getHostSets()['members'])
        with self.assertRaises(exceptions.HTTPBadRequest) as cm:
            self.cl.createHostSet(host_set_name)
        e = cm.exception
        self.assertEqual(
            e.get_description(),
            "invalid input: string length exceeds limit")

        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count, post_count)
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getHostSet,
            host_set_name
        )

        with self.assertRaises(exceptions.HTTPBadRequest) as cm:
            self.cl.modifyHostSet(host_set_name, comment="not gonna happen")
        e = cm.exception
        self.assertEqual(
            e.get_description(),
            "invalid input: string length exceeds limit")

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.deleteHostSet,
            host_set_name
        )

        self.printFooter("host_set_name_too_long")

    def test_host_set_name_invalid(self):
        """Host set name with invalid characters."""
        self.printHeader("host_set_name_invalid")

        # name has invalid characters
        host_set_name = "HostSet-!nval!d"
        with self.assertRaises(exceptions.HTTPBadRequest) as cm:
            self.cl.getHostSet(host_set_name)
        e = cm.exception
        self.assertEqual(e.get_description(),
                         "illegal character in input")

        self.printFooter("host_set_name_invalid")

    def test_duplicate_host_set_name(self):
        """Host set name already exists."""
        self.printHeader("duplicate_host_set_name")

        test_prefix = 'UT3_'

        # create same one twice
        host_set_name = test_prefix + "HS_X_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name)
        pre_count = len(self.cl.getHostSets()['members'])
        original_comment = "original comment"
        host_set_id = self.cl.createHostSet(host_set_name,
                                            comment=original_comment)
        self.assertEqual(host_set_name, host_set_id)
        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count + 1, post_count)
        pre_count = post_count
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.createHostSet,
            host_set_name
        )
        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count, post_count)

        self.printFooter("duplicate_host_set_name")

    def test_modify_param_conflict(self):
        """Test modify of host sets parameter conflict."""
        self.printHeader("modify_param_conflict")

        test_prefix = 'UT4_'

        host_set_name1 = test_prefix + "HS1_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        host_set_name2 = test_prefix + "HS2_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name2)
        new_comment = "new comment"
        new_member = "bogushost"
        with self.assertRaises(exceptions.HTTPBadRequest) as cm:
            self.cl.modifyHostSet(host_set_name1, 1, host_set_name2,
                                  new_comment, setmembers=[new_member])
        e = cm.exception
        self.assertEqual(e.get_description(),
                         "invalid input: parameters cannot be present"
                         " at the same time")
        self.assertEqual(e.get_code(), INV_INPUT_PARAM_CONFLICT)

        self.printFooter("modify_param_conflict")

    def test_bogus_host(self):
        """Modify of host set with bogus host."""
        self.printHeader("bogus_host")

        test_prefix = 'UT5_'

        host_set_name1 = test_prefix + "HS1_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        new_member = "bogushost"

        with self.assertRaises(exceptions.HTTPNotFound) as cm:
            self.cl.modifyHostSet(host_set_name1, 1, setmembers=[new_member])
        e = cm.exception
        self.assertEqual(e.get_description(), "host does not exist")
        self.assertEqual(e.get_code(), 17)

        self.printFooter("bogus_host")

    def test_modify(self):
        """Test modify of host sets."""
        self.printHeader("modify")

        test_prefix = 'UT6_'

        host_set_name1 = test_prefix + "HS1_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        host_set_name2 = test_prefix + "HS2_" + HPE3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name2)
        new_comment = "new comment"

        self.cl.modifyHostSet(host_set_name1, newName=host_set_name2)
        self.cl.modifyHostSet(host_set_name2, comment=new_comment)

        created_host1 = test_prefix + "HOST1_" + HPE3ParClient_base.TIME
        hosts_to_delete.append(created_host1)
        self.cl.createHost(created_host1)
        self.cl.modifyHostSet(host_set_name2, 1, setmembers=[created_host1])
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getHostSet,
            host_set_name1
        )

        host2 = self.cl.getHostSet(host_set_name2)
        self.assertEqual(host2['name'], host_set_name2)
        self.assertEqual(host2['comment'], new_comment)
        self.assertEqual(host2['setmembers'], [created_host1])

        created_host2 = test_prefix + "HOST2_" + HPE3ParClient_base.TIME
        hosts_to_delete.append(created_host2)
        self.cl.createHost(created_host2)
        self.cl.modifyHostSet(host_set_name2, 1, setmembers=[created_host2])

        host2 = self.cl.getHostSet(host_set_name2)
        self.assertEqual(host2['setmembers'], [created_host1, created_host2])

        self.printFooter("modify")
