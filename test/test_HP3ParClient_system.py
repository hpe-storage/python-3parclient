# (c) Copyright 2015 Hewlett Packard Development Company, L.P.
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

"""Test class of 3PAR Client System Level APIS."""

from testconfig import config
import unittest
from test import HP3ParClient_base as hp3parbase

from hp3parclient import exceptions


class HP3ParClientSystemTestCase(hp3parbase.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientSystemTestCase, self).setUp(withSSH=True)

    def tearDown(self):
        # very last, tear down base class
        super(HP3ParClientSystemTestCase, self).tearDown()

    def test_get_patch(self):
        """This can work with or without a patch, but you need to manually
           enter a valid one or use the bogus one.

        """

        self.printHeader('get_patch')

        # actual patch you might be able to test with somewhere:
        # patch_id = 'P16'
        #
        # bogus patch name that should consistently be not recognized:
        patch_id = 'P16-BOGUS'

        result = self.cl.getPatch(patch_id)
        self.assertIsNotNone(result)
        if len(result) > 1:
            # found patch test results
            self.assertGreater(len(result), 1)
            self.assertTrue("Patch detail info for " + patch_id in result[0])
        else:
            # bogus/not-found patch test results
            self.assertEqual(len(result), 1)
            self.assertTrue("Patch " + patch_id + " not recognized"
                            in result[0])

        self.printFooter('get_patch')

    @unittest.skipIf(config['TEST']['unit'].lower() == 'true',
                     "only works with real array")
    def test_get_patches(self):
        """This test includes history (not just patches),
           so it should always have results.

        """

        self.printHeader('get_patches')
        result = self.cl.getPatches()
        self.assertIsNotNone(result)
        self.assertGreater(result['total'], 0)
        self.assertGreater(len(result['members']), 0)
        self.printFooter('get_patches')

    @unittest.skipIf(config['TEST']['unit'].lower() == 'true',
                     "only works with real array")
    def test_get_patches_no_hist(self):
        """This test expects to find no patches installed
           (typical in our test environment).

        """

        self.printHeader('get_patches')
        result = self.cl.getPatches(history=False)
        self.assertIsNotNone(result)
        self.assertEqual(result['total'], 0)
        self.assertEqual(len(result['members']), 0)
        self.printFooter('get_patches')

    def test_getStorageSystemInfo(self):
        self.printHeader('getStorageSystemInfo')
        info = self.cl.getStorageSystemInfo()
        self.assertIsNotNone(info)

        self.printFooter('getStorageSystemInfo')

    def test_getWSAPIConfigurationInfo(self):
        self.printHeader('getWSAPIConfigurationInfo')

        info = self.cl.getWSAPIConfigurationInfo()
        self.assertIsNotNone(info)
        self.printFooter('getWSAPIConfigurationInfo')

    def test_query_task(self):
        self.printHeader("query_task")

        tasks = self.cl.getAllTasks()
        self.assertIsNotNone(tasks)
        self.assertGreater(tasks['total'], 0)

        first_task = tasks['members'].pop()
        self.assertIsNotNone(first_task)

        task = self.cl.getTask(first_task['id'])
        self.assertEqual(first_task, task)
        self.printFooter("query_task")

    def test_query_task_negative(self):
        self.printHeader("query_task_negative")

        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.getTask,
            -1
        )

        self.printFooter("query_task_negative")

    def test_query_task_non_int(self):
        self.printHeader("query_task_non_int")

        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.getTask,
            "nonIntTask"
        )

        self.printFooter("query_task_non_int")

    def test_get_overall_system_capacity(self):
        self.printHeader("get_overall_system_capacity")
        capacity = self.cl.getOverallSystemCapacity()
        self.assertIsNotNone(capacity)
        self.printFooter("get_overall_system_capacity")


# testing
# suite = unittest.TestLoader().
#     loadTestsFromTestCase(HP3ParClientSystemTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
