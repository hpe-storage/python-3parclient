# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012-2016 Hewlett Packard Development Company, L.P.
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
""" HTTPJSONRESTClient.

.. module: http

:Author: Walter A. Boring IV
:Description: This is the HTTP Client that is used to make the actual calls.
 It includes the authentication that knows the cookie name for 3PAR.

"""

import logging
import requests
import time

try:
    import json
except ImportError:
    import simplejson as json

from hp3parclient import exceptions


class HTTPJSONRESTClient(object):
    """
    An HTTP REST Client that sends and recieves JSON data as the body of the
    HTTP request.

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080
    :type api_url: str
    :param secure: Validate SSL cert? Default will not validate
    :type secure: bool
    :param http_log_debug: Turns on http log debugging. Default will not log
    :type http_log_debug: bool
    :param suppress_ssl_warnings: Suppresses log warning messages if True
    :type suppress_ssl_warnings: bool

    """

    USER_AGENT = 'python-3parclient'
    SESSION_COOKIE_NAME = 'X-Hp3Par-Wsapi-Sessionkey'
    http_log_debug = False
    _logger = logging.getLogger(__name__)

    # Retry constants
    retry_exceptions = (exceptions.HTTPServiceUnavailable,
                        requests.exceptions.ConnectionError)
    tries = 5
    delay = 0
    backoff = 2

    def __init__(self, api_url, secure=False, http_log_debug=False,
                 suppress_ssl_warnings=False):
        if suppress_ssl_warnings:
            requests.packages.urllib3.disable_warnings()
        self.session_key = None

        # should be http://<Server:Port>/api/v1
        self.set_url(api_url)
        self.set_debug_flag(http_log_debug)

        self.times = []  # [("item", starttime, endtime), ...]
        self.secure = secure

    def set_url(self, api_url):
        # should be http://<Server:Port>/api/v1
        self.api_url = api_url.rstrip('/')

    def set_debug_flag(self, flag):
        """
        This turns on/off http request/response debugging output to console

        :param flag: Set to True to enable debugging output
        :type flag: bool

        """
        if not HTTPJSONRESTClient.http_log_debug and flag:
            ch = logging.StreamHandler()
            HTTPJSONRESTClient._logger.setLevel(logging.DEBUG)
            HTTPJSONRESTClient._logger.addHandler(ch)
            HTTPJSONRESTClient.http_log_debug = True

    def authenticate(self, user, password, optional=None):
        """
        This tries to create an authenticated session with the 3PAR server

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        # this prevens re-auth attempt if auth fails
        self.auth_try = 1
        self.session_key = None

        info = {'user': user, 'password': password}
        self._auth_optional = None

        if optional:
            self._auth_optional = optional
            info.update(optional)

        resp, body = self.post('/credentials', body=info)
        if body and 'key' in body:
            self.session_key = body['key']
        self.auth_try = 0
        self.user = user
        self.password = password

    def _reauth(self):
        self.authenticate(self.user, self.password, self._auth_optional)

    def unauthenticate(self):
        """
        This clears the authenticated session with the 3PAR server.

        """
        # delete the session on the 3Par
        self.delete('/credentials/%s' % self.session_key)
        self.session_key = None

    def get_timings(self):
        """
        Ths gives an array of the request timings since last reset_timings call
        """
        return self.times

    def reset_timings(self):
        """
        This resets the request/response timings array
        """
        self.times = []

    def _http_log_req(self, args, kwargs):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i']
        for element in args:
            if element in ('GET', 'POST'):
                string_parts.append(' -X %s' % element)
            else:
                string_parts.append(' %s' % element)

        for element in kwargs['headers']:
            header = ' -H "%s: %s"' % (element, kwargs['headers'][element])
            string_parts.append(header)

        HTTPJSONRESTClient._logger.debug("\nREQ: %s\n" % "".join(string_parts))
        if 'body' in kwargs:
            HTTPJSONRESTClient._logger.debug("REQ BODY: %s\n" %
                                             (kwargs['body']))

    def _http_log_resp(self, resp, body):
        if not self.http_log_debug:
            return
        # Replace commas with newlines to break the debug into new lines,
        # making it easier to read
        HTTPJSONRESTClient._logger.debug("RESP:%s\n",
                                         str(resp).replace("',", "'\n"))
        HTTPJSONRESTClient._logger.debug("RESP BODY:%s\n", body)

    def request(self, *args, **kwargs):
        """
        This makes an HTTP Request to the 3Par server.
        You should use get, post, delete instead.

        """
        if self.session_key and self.auth_try != 1:
            kwargs.setdefault('headers', {})[self.SESSION_COOKIE_NAME] = \
                self.session_key

        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])
            payload = kwargs['body']
        else:
            payload = None

        # args[0] contains the URL, args[1] contains the HTTP verb/method
        http_url = args[0]
        http_method = args[1]

        self._http_log_req(args, kwargs)
        r = None
        resp = None
        body = None
        while r is None and self.tries > 0:
            try:
                # Check to see if the request is being retried. If it is, we
                # want to delay.
                if self.delay:
                    time.sleep(self.delay)

                r = requests.request(http_method, http_url, data=payload,
                                     headers=kwargs['headers'],
                                     verify=self.secure)

                resp = r.headers
                body = r.text
                if isinstance(body, bytes):
                    body = body.decode('utf-8')

                # resp['status'], status['content-location'], and resp.status
                # need to be manually set as Python Requests doesn't provide
                # them automatically.
                resp['status'] = str(r.status_code)
                resp.status = r.status_code
                if 'location' not in resp:
                    resp['content-location'] = r.url

                r.close()
                self._http_log_resp(resp, body)

                # Try and convert the body response to an object
                # This assumes the body of the reply is JSON
                if body:
                    try:
                        body = json.loads(body)
                    except ValueError:
                        pass
                else:
                    body = None

                if resp.status >= 400:
                    if body and 'message' in body:
                        body['desc'] = body['message']

                    raise exceptions.from_response(resp, body)
            except self.retry_exceptions as ex:
                # If we catch an exception where we want to retry, we need to
                # decrement the retry count prepare to try again.
                r = None
                self.tries -= 1
                self.delay = self.delay * self.backoff + 1

                # Raise exception, we have exhausted all retries.
                if self.tries is 0:
                    raise ex
            except requests.exceptions.SSLError as err:
                HTTPJSONRESTClient._logger.error(
                    "SSL certificate verification failed: (%s). You must have "
                    "a valid SSL certificate or disable SSL "
                    "verification.", err)
                raise exceptions.SSLCertFailed("SSL Certificate Verification "
                                               "Failed.")
            except requests.exceptions.RequestException as err:
                raise exceptions.RequestException(
                    "Request Exception: %s" % err)
            except requests.exceptions.HTTPError as err:
                raise exceptions.HTTPError("HTTP Error: %s" % err)
            except requests.exceptions.URLRequired as err:
                raise exceptions.URLRequired("URL Required: %s" % err)
            except requests.exceptions.TooManyRedirects as err:
                raise exceptions.TooManyRedirects(
                    "Too Many Redirects: %s" % err)
            except requests.exceptions.Timeout as err:
                raise exceptions.Timeout("Timeout: %s" % err)

        return resp, body

    def _time_request(self, url, method, **kwargs):
        start_time = time.time()
        resp, body = self.request(url, method, **kwargs)
        self.times.append(("%s %s" % (method, url),
                           start_time, time.time()))
        return resp, body

    def _do_reauth(self, url, method, ex, **kwargs):
        # print("_do_reauth called")
        try:
            if self.auth_try != 1:
                self._reauth()
                resp, body = self._time_request(self.api_url + url, method,
                                                **kwargs)
                return resp, body
            else:
                raise ex
        except exceptions.HTTPUnauthorized:
            raise ex

    def _cs_request(self, url, method, **kwargs):
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            resp, body = self._time_request(self.api_url + url, method,
                                            **kwargs)
            return resp, body
        except exceptions.HTTPUnauthorized as ex:
            # print("_CS_REQUEST HTTPUnauthorized")
            resp, body = self._do_reauth(url, method, ex, **kwargs)
            return resp, body
        except exceptions.HTTPForbidden as ex:
            # print("_CS_REQUEST HTTPForbidden")
            resp, body = self._do_reauth(url, method, ex, **kwargs)
            return resp, body

    def get(self, url, **kwargs):
        """
        Make an HTTP GET request to the server.

        .. code-block:: python

            #example call
            try {
                headers, body = http.get('/volumes')
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        """
        Make an HTTP POST request to the server.

        .. code-block:: python

            #example call
            try {
                info = {'name': 'new volume name', 'cpg': 'MyCPG',
                        'sizeMiB': 300}
                headers, body = http.post('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        """
        Make an HTTP PUT request to the server.

        .. code-block:: python

            #example call
            try {
                info = {'name': 'something'}
                headers, body = http.put('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON,
                         it will be an object
        """
        return self._cs_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        """
        Make an HTTP DELETE request to the server.

        .. code-block:: python

            #example call
            try {
                headers, body = http.delete('/volumes/%s' % name)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it
                         will be an object
        """
        return self._cs_request(url, 'DELETE', **kwargs)
