# (c) Copyright 2016 Hewlett Packard Enterprise Development LP
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

"""Test class of 3PAR Client handling WSAPI retries."""

import importlib
import mock
import requests

from test import HP3ParClient_base as hp3parbase

from hp3parclient import exceptions


class HP3ParClientRetryTestCase(hp3parbase.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientRetryTestCase, self).setUp()

    def tearDown(self):
        # NOTE(aorourke): We mock out the requests library's request method in
        # order to force exceptions so we can test retry attempts. By doing
        # this, we completely destroy the functionaility of requests.
        # Therefore, after every unit test we run, we need to reimport the
        # library to restore proper functionality or all future tests will
        # fail. In Python 2.7 we must use the built in reload() method while
        # in Python 3.4 we must use importlib.reload().
        try:
            reload(requests)
        except NameError:
            importlib.reload(requests)
        super(HP3ParClientRetryTestCase, self).tearDown()

    def test_retry_exhaust_all_attempts_service_unavailable(self):
        http = self.cl.http

        # There should be 5 tries before anything is called.
        self.assertEqual(http.tries, 5)

        # The requests object needs to raise an exception in order for us
        # to test the retry functionality.
        requests.request = mock.Mock()
        requests.request.side_effect = exceptions.HTTPServiceUnavailable(
            "Maximum number of WSAPI connections reached.")

        # This will take ~30 seconds to fail.
        self.assertRaises(
            exceptions.HTTPServiceUnavailable,
            http.get,
            '/volumes')

        # There should be 0 tries left after the call.
        self.assertEqual(http.tries, 0)

    def test_retry_exhaust_all_attempts_connection_error(self):
        http = self.cl.http

        # There should be 5 tries before anything is called.
        self.assertEqual(http.tries, 5)

        # The requests object needs to raise an exception in order for us
        # to test the retry functionality.
        requests.request = mock.Mock()
        requests.request.side_effect = requests.exceptions.ConnectionError(
            "There was a connection error.")

        # This will take ~30 seconds to fail.
        self.assertRaises(
            requests.exceptions.ConnectionError,
            http.get,
            '/volumes')

        # There should be 0 tries left after the call.
        self.assertEqual(http.tries, 0)

    def test_no_retry(self):
        http = self.cl.http

        # There should be 5 tries before anything is called.
        self.assertEqual(http.tries, 5)

        http.get('/volumes')

        # There should be 5 tries left after the call.
        self.assertEqual(http.tries, 5)
