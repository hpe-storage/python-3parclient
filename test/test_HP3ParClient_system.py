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

"""Test class of 3PAR Client System Level APIS"""

import sys
import os
sys.path.insert(0, os.path.realpath(os.path.abspath('../')))

import unittest
import test_HP3ParClient_base

from hp3parclient import client, exceptions

class HP3ParClientSystemTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientSystemTestCase, self).setUp()

    def tearDown(self):
        # very last, tear down base class
        super(HP3ParClientSystemTestCase, self).tearDown()

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

        try:
            self.cl.getTask(-1)
        except exceptions.HTTPBadRequest as ex:
            return

        self.fail("expected an HTTP Bad Request exception")

    def test_query_task_non_int(self):
        self.printHeader("query_task_non_int")

        try:
            self.cl.getTask("nonIntTask")
        except exceptions.HTTPBadRequest as ex:
            return

        self.fail("expected an HTTP Bad Request exception")


#testing
#suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientSystemTestCase)
#unittest.TextTestRunner(verbosity=2).run(suite)
