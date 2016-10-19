# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
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

"""Test class of 3PAR Client handling HTTPJSONRESTClient."""

import unittest
import mock
import requests

from hpe3parclient import exceptions
from hpe3parclient import http


class HTTPJSONRESTClientTestCase(unittest.TestCase):

    http = None

    def setUp(self):
        fake_url = 'http://fake-url:0000'
        self.http = http.HTTPJSONRESTClient(fake_url, secure=False,
                                            http_log_debug=True,
                                            suppress_ssl_warnings=False,
                                            timeout=None)

    def tearDown(self):
        self.http = None

    def test_cs_request(self):
        url = "fake-url"
        method = 'GET'

        # Test for HTTPUnauthorized
        self.http._time_request = mock.Mock()
        ex = exceptions.HTTPUnauthorized()
        self.http._time_request.side_effect = ex

        self.http._do_reauth = mock.Mock()
        resp = 'fake_response'
        body = 'fake_body'
        self.http._do_reauth.return_value = (resp, body)

        self.http._cs_request(url, method)
        self.http._time_request.assert_called()
        self.http._do_reauth.assert_called_with(url, method, ex)

        # Test for HTTPForbidden
        ex = exceptions.HTTPForbidden()
        self.http._time_request.side_effect = ex
        self.http._cs_request(url, method)
        self.http._time_request.assert_called()
        self.http._do_reauth.assert_called_with(url, method, ex)

    def test_do_reauth_exception(self):
        url = "fake-url"
        method = 'GET'
        ex = exceptions.HTTPUnauthorized
        self.http.auth_try = 2
        self.http._reauth = mock.Mock()
        self.http._time_request = mock.Mock()
        self.http._time_request.side_effect = ex
        self.assertRaises(ex, self.http._do_reauth, url, method, ex)
        self.http._reauth.assert_called()

    def test_do_reauth_with_auth_try_condition_false(self):
        ex = exceptions.HTTPUnauthorized
        url = "fake-url"
        method = 'GET'
        self.http.auth_try = 1
        self.assertRaises(ex, self.http._do_reauth, url, method, ex)

    def test_request(self):
        self.http._http_log_req = mock.Mock()
        self.http.timeout = 10
        retest = mock.Mock()
        http_method = 'fake this'
        http_url = 'http://fake-url:0000'

        with mock.patch('requests.request', retest, create=True):
            # Test timeout exception
            retest.side_effect = requests.exceptions.Timeout
            self.assertRaises(exceptions.Timeout,
                              self.http.request,
                              http_url, http_method)

            # Test too many redirects exception
            retest.side_effect = requests.exceptions.TooManyRedirects
            self.assertRaises(exceptions.TooManyRedirects,
                              self.http.request,
                              http_url, http_method)

            # Test HTTP Error exception
            retest.side_effect = requests.exceptions.HTTPError
            self.assertRaises(exceptions.HTTPError,
                              self.http.request,
                              http_url, http_method)

            # Test URL required exception
            retest.side_effect = requests.exceptions.URLRequired
            self.assertRaises(exceptions.URLRequired,
                              self.http.request,
                              http_url, http_method)

            # Test request exception
            retest.side_effect = requests.exceptions.RequestException
            self.assertRaises(exceptions.RequestException,
                              self.http.request,
                              http_url, http_method)

            # Test requests exception
            retest.side_effect = requests.exceptions.SSLError
            self.assertRaisesRegexp(exceptions.SSLCertFailed, "failed")

            self.assertEqual(self.http.timeout, 10)

            # Test retry exception
            retest.side_effect = requests.exceptions.ConnectionError
            self.assertRaises(requests.exceptions.ConnectionError,
                              self.http.request,
                              http_url, http_method)
