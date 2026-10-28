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
            with mock.patch('time.sleep'):
                self.assertRaises(requests.exceptions.ConnectionError,
                                  self.http.request,
                                  http_url, http_method)

    def test_unauthenticate_without_session_key(self):
        self.http.session_key = None
        with mock.patch.object(self.http, 'delete') as mock_delete:
            self.http.unauthenticate()
        mock_delete.assert_not_called()

    def test_unauthenticate_with_session_key(self):
        self.http.session_key = 'abc'
        with mock.patch.object(self.http, 'delete') as mock_delete:
            self.http.unauthenticate()
        mock_delete.assert_called_once_with('/credentials/abc')
        self.assertIsNone(self.http.session_key)

    @mock.patch('time.sleep')
    def test_request_retries_reset_after_exhaustion(self, mock_sleep):
        self.http._http_log_req = mock.Mock()
        self.http._http_log_resp = mock.Mock()
        http_url = 'http://fake-url:0000/credentials'
        unavailable = exceptions.HTTPServiceUnavailable()
        ok = mock.Mock(status_code=200, text='{"key": "abc"}',
                       url=http_url,
                       headers=requests.structures.CaseInsensitiveDict())

        with mock.patch('requests.request') as retest:
            retest.side_effect = unavailable
            self.assertRaises(exceptions.HTTPServiceUnavailable,
                              self.http.request, http_url, 'POST')
            self.assertEqual(5, retest.call_count)
            self.assertEqual([mock.call(1), mock.call(3), mock.call(7),
                              mock.call(15)], mock_sleep.call_args_list)

            # A later request must still reach the array with a fresh budget.
            retest.reset_mock(side_effect=True)
            mock_sleep.reset_mock()
            retest.return_value = ok
            resp, body = self.http.request(http_url, 'POST')

            self.assertEqual(1, retest.call_count)
            mock_sleep.assert_not_called()
            self.assertEqual({'key': 'abc'}, body)
            self.assertEqual(5, self.http.tries)
            self.assertEqual(0, self.http.delay)

    def test_request_without_attempt_raises(self):
        self.http.tries = 0
        http_url = 'http://fake-url:0000/credentials'

        with mock.patch('requests.request') as request:
            self.assertRaises(exceptions.RequestException,
                              self.http.request, http_url, 'POST')

        request.assert_not_called()
