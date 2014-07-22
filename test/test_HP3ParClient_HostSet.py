# (c) Copyright 2012-2014 Hewlett Packard Development Company, L.P.
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

"""Test class of 3Par Client handling of Host Sets."""
import sys
import os
sys.path.insert(0, os.path.realpath(os.path.abspath('../')))
from hp3parclient import exceptions
import unittest
import HP3ParClient_base
import random

PORT_1 = {'node': 1, 'cardPort': 1, 'slot': 1}
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


class HP3ParClientHostSetTestCase(HP3ParClient_base.HP3ParClientBaseTestCase):

    def setUp(self, withSSH=False):

        super(HP3ParClientHostSetTestCase, self).setUp(withSSH=True)

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
        super(HP3ParClientHostSetTestCase, self).tearDown()

    def test_crud_host_without_host_set(self):
        """CRUD test for attach/detach VLUN to host w/o a host set."""

        test_prefix = 'UT1_'
        #
        # CREATE
        #
        # Create Host
        host_name = test_prefix + "HOST_" + HP3ParClient_base.TIME
        hosts_to_delete.append(host_name)

        optional = {'domain': self.DOMAIN}
        self.cl.createHost(host_name, optional=optional)

        # Create CPG
        cpg_name = test_prefix + "CPG_" + HP3ParClient_base.TIME
        cpgs_to_delete.append(cpg_name)

        optional = self.CPG_OPTIONS
        self.cl.createCPG(cpg_name, optional)

        # Create Volumes
        volume_name1 = test_prefix + "VOL1_" + HP3ParClient_base.TIME
        volume_name2 = test_prefix + "VOL2_" + HP3ParClient_base.TIME
        volumes_to_delete.extend([volume_name1, volume_name2])
        self.cl.createVolume(volume_name1, cpg_name, VOLUME_SIZE)
        self.cl.createVolume(volume_name2, cpg_name, VOLUME_SIZE)

        # Create VLUNs
        vlun1 = [volume_name1, LUN_1, host_name, PORT_1]
        vlun2 = [volume_name2, LUN_2, host_name, PORT_1]
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
        try:
            self.cl.deleteHost(host_name)
        except exceptions.HTTPConflict as e:
            self.assertEqual(e.get_code(), 26)
            self.assertEqual(e.get_description(), "has exported VLUN")
            pass
        except Exception:
            raise
        else:
            self.fail("Expected an exception when deleting a host with a vlun")

        self.cl.deleteVLUN(*vlun2)

        # Now we can delete the host
        self.cl.deleteHost(host_name)

        # Should be able to clean-up these, too
        self.cl.deleteVolume(volume_name1)
        self.cl.deleteVolume(volume_name2)
        self.cl.deleteCPG(cpg_name)

    def test_crud_host_with_host_set(self):
        """CRUD test for attach/detach VLUN to host in host set."""

        test_prefix = 'UT2_'

        #
        # CREATE
        #

        # Create Host
        host_name = test_prefix + "HOST_" + HP3ParClient_base.TIME
        hosts_to_delete.append(host_name)

        optional = {'domain': self.DOMAIN}
        self.cl.createHost(host_name, optional=optional)

        # Create Host Set
        host_set_name = test_prefix + "HOST_SET_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name)
        host_set_id = self.cl.createHostSet(
            host_set_name, self.DOMAIN,
            unittest.TestCase.shortDescription(self), [host_name])
        self.assertEqual(host_set_name, host_set_id)

        # Create CPG
        cpg_name = test_prefix + "CPG_" + HP3ParClient_base.TIME
        cpgs_to_delete.append(cpg_name)

        optional = self.CPG_OPTIONS
        self.cl.createCPG(cpg_name, optional)

        # Create Volumes
        volume_name1 = test_prefix + "VOL1_" + HP3ParClient_base.TIME
        volume_name2 = test_prefix + "VOL2_" + HP3ParClient_base.TIME
        volumes_to_delete.extend([volume_name1, volume_name2])
        self.cl.createVolume(volume_name1, cpg_name, VOLUME_SIZE)
        self.cl.createVolume(volume_name2, cpg_name, VOLUME_SIZE)

        # Create VLUNs
        vlun1 = [volume_name1, LUN_1, host_name, PORT_1]
        vlun2 = [volume_name2, LUN_2, host_name, PORT_1]
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
        try:
            self.cl.deleteHost(host_name)
        except exceptions.HTTPConflict as e:
            self.assertEqual(e.get_code(), EXPORTED_VLUN)
            self.assertEqual(e.get_description(), "has exported VLUN")
            pass
        except Exception:
            raise
        else:
            self.fail("Expected an exception when deleting a host with a vlun")

        self.cl.deleteVLUN(*vlun2)

        # Make sure that we cannot delete the host while it is in a host set
        try:
            self.cl.deleteHost(host_name)
        except exceptions.HTTPConflict as e:
            self.assertEqual(e.get_code(), HOST_IN_SET)
            self.assertEqual(e.get_description(), "host is a member of a set")
            pass
        except Exception:
            raise
        else:
            self.fail("Expected an exception when deleting a host in a host "
                      "set")

        self.cl.removeHostFromItsHostSet(host_name)

        # Now we can delete the host
        self.cl.deleteHost(host_name)

        # Should be able to clean-up these too
        self.cl.deleteHostSet(host_set_name)
        self.cl.deleteVolume(volume_name1)
        self.cl.deleteVolume(volume_name2)
        self.cl.deleteCPG(cpg_name)

    def test_host_set_name_too_long(self):
        """Host set name too long."""

        test_prefix = 'UT_'

        # name too long
        host_set_name = (test_prefix + "HOST_SET_NAME_IS_TOOOOOOOOOO_LONG_"
                         + HP3ParClient_base.TIME)
        host_sets_to_delete.append(host_set_name)

        pre_count = len(self.cl.getHostSets()['members'])
        try:
            self.cl.createHostSet(host_set_name)
        except exceptions.HTTPBadRequest as e:
            self.assertEqual(
                e.get_description(),
                "invalid input: string length exceeds limit")
        except Exception:
            raise
        else:
            self.fail("Expected an exception for host set name too long.")

        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count, post_count)
        try:
            self.cl.getHostSet(host_set_name)
        except exceptions.HTTPNotFound:
            pass
        except Exception:
            raise
        else:
            self.fail("Expected not found")

        try:
            self.cl.modifyHostSet(host_set_name, comment="not gonna happen")
        except exceptions.HTTPBadRequest as e:
            self.assertEqual(
                e.get_description(),
                "invalid input: string length exceeds limit")
        except Exception:
            raise
        else:
            self.fail("Expected an exception for host set name too long.")

        try:
            self.cl.deleteHostSet(host_set_name)
        except exceptions.HTTPNotFound:
            pass
        except Exception:
            raise
        else:
            self.fail("Expected host set not found")

    def test_host_set_name_invalid(self):
        """Host set name with invalid characters."""

        # name has invalid characters
        host_set_name = "HostSet-!nval!d"
        try:
            self.cl.getHostSet(host_set_name)
        except exceptions.HTTPBadRequest as e:
            self.assertEqual(e.get_description(),
                             "illegal character in input")
        except Exception:
            raise
        else:
            self.fail("Expected illegal character in host set")

    def test_duplicate_host_set_name(self):
        """Host set name already exists."""

        test_prefix = 'UT3_'

        # create same one twice
        host_set_name = test_prefix + "HS_X_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name)
        pre_count = len(self.cl.getHostSets()['members'])
        original_comment = "original comment"
        host_set_id = self.cl.createHostSet(host_set_name,
                                            comment=original_comment)
        self.assertEqual(host_set_name, host_set_id)
        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count + 1, post_count)
        pre_count = post_count
        try:
            self.cl.createHostSet(host_set_name)
        except exceptions.HTTPConflict:
            pass
        except Exception:
            raise
        else:
            self.fail("Expected HttpConflict creating host set twice")
        post_count = len(self.cl.getHostSets()['members'])
        self.assertEqual(pre_count, post_count)

    def test_modify_param_conflict(self):
        """Test modify of host sets parameter conflict."""

        test_prefix = 'UT4_'

        host_set_name1 = test_prefix + "HS1_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        host_set_name2 = test_prefix + "HS2_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name2)
        new_comment = "new comment"
        new_member = "bogushost"
        try:
            self.cl.modifyHostSet(host_set_name1, 1, host_set_name2,
                                  new_comment, setmembers=[new_member])
        except exceptions.HTTPBadRequest as e:
            self.assertEqual(e.get_description(),
                             "invalid input: parameters cannot be present"
                             " at the same time")
            self.assertEqual(e.get_code(), INV_INPUT_PARAM_CONFLICT)
        else:
            self.fail("expected exception")

    def test_bogus_host(self):
        """Modify of host set with bogus host."""

        test_prefix = 'UT5_'

        host_set_name1 = test_prefix + "HS1_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        new_member = "bogushost"

        try:
            self.cl.modifyHostSet(host_set_name1, 1, setmembers=[new_member])
        except exceptions.HTTPNotFound as e:
            self.assertEqual(e.get_description(), "host does not exist")
            self.assertEqual(e.get_code(), 17)
        else:
            self.fail("expected exception")

    def test_modify(self):
        """Test modify of host sets."""

        test_prefix = 'UT6_'

        host_set_name1 = test_prefix + "HS1_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name1)
        self.cl.createHostSet(host_set_name1)
        host_set_name2 = test_prefix + "HS2_" + HP3ParClient_base.TIME
        host_sets_to_delete.append(host_set_name2)
        new_comment = "new comment"

        self.cl.modifyHostSet(host_set_name1, newName=host_set_name2)
        self.cl.modifyHostSet(host_set_name2, comment=new_comment)

        created_host1 = test_prefix + "HOST1_" + HP3ParClient_base.TIME
        hosts_to_delete.append(created_host1)
        self.cl.createHost(created_host1)
        self.cl.modifyHostSet(host_set_name2, 1, setmembers=[created_host1])

        try:
            self.cl.getHostSet(host_set_name1)
        except exceptions.HTTPNotFound:
            pass
        else:
            self.fail("expected exception")

        host2 = self.cl.getHostSet(host_set_name2)
        self.assertEqual(host2['name'], host_set_name2)
        self.assertEqual(host2['comment'], new_comment)
        self.assertEqual(host2['setmembers'], [created_host1])

        created_host2 = test_prefix + "HOST2_" + HP3ParClient_base.TIME
        hosts_to_delete.append(created_host2)
        self.cl.createHost(created_host2)
        self.cl.modifyHostSet(host_set_name2, 1, setmembers=[created_host2])

        host2 = self.cl.getHostSet(host_set_name2)
        self.assertEqual(host2['setmembers'], [created_host1, created_host2])
