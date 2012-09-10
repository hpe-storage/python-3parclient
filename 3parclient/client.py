# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Hewlett Packard Development Company, L.P.
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
"""
3Par REST Client
"""

import logging
import os
import urlparse
import httplib2

try:
    import json
except ImportError:
    import simplejson as json



class 3ParRESTCLient(httlib2.Http):

    USER_AGENT = 'python-3parclient'

    def __init__(self, user, password, api_url=None,
                 insecure=False, timeout=None, 
                 timings=False, no_cache=False, http_log_debug=False):
        super(HTTPClient, self).__init__(timeout=timeout)
        self.user = user
        self.password = password

        self.session_key = None

	#should be http://<Server:Port>/api/v1
        self.api_url = api_url.rstrip('/')
        self.http_log_debug = http_log_debug

        self.times = []  # [("item", starttime, endtime), ...]

        # httplib2 overrides
        self.force_exception_to_status_code = True
        self.disable_ssl_certificate_validation = insecure

        self.auth_system = auth_system

        self._logger = logging.getLogger(__name__)
        if self.http_log_debug:
            ch = logging.StreamHandler()
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(ch)

    def authenticate(self):
	#make sure we have a user and password
	auth_json = json.dumps({'user':self.user, 'password':self.password})
        self.get(self.api_url+'/credentials', auth_json)
        

    def unauthenticate(self):
        """Forget all of our authentication information."""
	#delete the session on the 3Par
        self.delete(self.api_url+'/credentials/%s' % self.session_key)
        self.session_key = None

    def get_timings(self):
        return self.times

    def reset_timings(self):
        self.times = []

    def http_log_req(self, args, kwargs):
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

        self._logger.debug("\nREQ: %s\n" % "".join(string_parts))
        if 'body' in kwargs:
            self._logger.debug("REQ BODY: %s\n" % (kwargs['body']))

    def http_log_resp(self, resp, body):
        if not self.http_log_debug:
            return
        self._logger.debug("RESP:%s %s\n", resp, body)

    def request(self, *args, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        self.http_log_req(args, kwargs)
        resp, body = super(HTTPClient, self).request(*args, **kwargs)
        self.http_log_resp(resp, body)

        if body:
            try:
                body = json.loads(body)
            except ValueError:
                pass
        else:
            body = None

        if resp.status >= 400:
            raise exceptions.from_response(resp, body)

        return resp, body

    def _time_request(self, url, method, **kwargs):
        start_time = time.time()
        resp, body = self.request(url, method, **kwargs)
        self.times.append(("%s %s" % (method, url),
                           start_time, time.time()))
        return resp, body


    def _cs_request(self, url, method, **kwargs):
        if not self.management_url:
            self.authenticate()

        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            kwargs.setdefault('headers', {})['X-InFormAPI-SessionKey'] = self.session_key

            resp, body = self._time_request(self.management_url + url, method,
                                            **kwargs)
            return resp, body
        except exceptions.Unauthorized, ex:
            try:
                self.authenticate()
                kwargs['headers']['X-InFormAPI-SessionKey'] = self.auth_token
                resp, body = self._time_request(self.management_url + url,
                                                method, **kwargs)
                return resp, body
            except exceptions.Unauthorized:
                raise ex

    def get(self, url, **kwargs):
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self._cs_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        return self._cs_request(url, 'DELETE', **kwargs)
