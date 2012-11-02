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
HP3Par HTTP Client
:Author: Walter A. Boring IV
:Description: This is the HTTP Client that is used to make the actual calls. IT includes the authentication that knows the cookie name for 3PAR.

"""

import logging
import os
import urlparse
import httplib2
import time
import pprint

try:
    import json
except ImportError:
    import simplejson as json

from hp3parclient import exceptions

class HTTPJSONRESTClient(httplib2.Http):
    """ 
    An HTTP REST Client that sends and recieves JSON data as the body of the HTTP request

    :param api_url: The url to the WSAPI service on 3PAR ie. http://<3par server>:8008/api/v1
    :type api_url: str
    :param insecure: Use https? requires a local certificate
    :type insecure: bool

    """

    USER_AGENT = 'python-3parclient'
    SESSION_COOKIE_NAME = 'X-Hp3Par-Wsapi-Sessionkey'

    def __init__(self, api_url, insecure=False, http_log_debug=False):
        super(HTTPJSONRESTClient, self).__init__(disable_ssl_certificate_validation=True)

        self.session_key = None

	#should be http://<Server:Port>/api/v1
        self.api_url = api_url.rstrip('/')
	self.set_debug_flag(http_log_debug)

        self.times = []  # [("item", starttime, endtime), ...]

        # httplib2 overrides
        self.force_exception_to_status_code = True
        #self.disable_ssl_certificate_validation = insecure

        self._logger = logging.getLogger(__name__)

    def set_debug_flag(self, flag):
        """
        This turns on/off http request/response debugging output to console

        :param flag: Set to True to enable debugging output
        :type flag: bool

        """
	self.http_log_debug = flag
        if self.http_log_debug:
            ch = logging.StreamHandler()
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(ch)

    def authenticate(self, user, password, optional=None):
        """
        This tries to create an authenticated session with the 3PAR server

        :param user: The username
        :type user: str
        :param password: Password
        :type password: str

        """
        #this prevens re-auth attempt if auth fails
	self.auth_try = 1

        info = {'user':user, 'password':password}
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
        This clears the authenticated session with the 3PAR server.  It logs out.
        
        """
	#delete the session on the 3Par
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

        self._logger.debug("\nREQ: %s\n" % "".join(string_parts))
        if 'body' in kwargs:
            self._logger.debug("REQ BODY: %s\n" % (kwargs['body']))

    def _http_log_resp(self, resp, body):
        if not self.http_log_debug:
            return
        self._logger.debug("RESP:%s\n", pprint.pformat(resp))
        self._logger.debug("RESP BODY:%s\n", body)

    def request(self, *args, **kwargs):
        """
        This makes an HTTP Request to the 3Par server.  You should use get, post, delete instead.
        """
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        self._http_log_req(args, kwargs)
        resp, body = super(HTTPJSONRESTClient, self).request(*args, **kwargs)
        self._http_log_resp(resp, body)
      
        # Try and conver the body response to an object
        # This assumes the body of the reply is JSON 
        if body:
            try:
                body = json.loads(body)
            except ValueError:
                #pprint.pprint("failed to decode json\n")
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


    def _do_reauth(self, url, method, ex, **kwargs):
	print "_do_reauth called"
        try:
	    if self.auth_try != 1:
               self._reauth()
               resp, body = self._time_request(self.api_url + url, method, **kwargs)
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
            if self.session_key and self.auth_try != 1 :
                kwargs.setdefault('headers', {})[self.SESSION_COOKIE_NAME] = self.session_key

            resp, body = self._time_request(self.api_url + url, method,
                                            **kwargs)
            return resp, body
        except exceptions.HTTPUnauthorized, ex:
            print "_CS_REQUEST HTTPUnauthorized"
	    resp, body = self._do_reauth(url, method, ex, **kwargs)
        except exceptions.HTTPForbidden, ex:
            print "_CS_REQUEST HTTPForbidden"
            resp, body = self._do_reauth(url, method, ex, **kwargs)


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
        :returns: body - the body of the response.  If the body was JSON, it will be an object
        """
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        """
        Make an HTTP POST request to the server.

        .. code-block:: python
            
            #example call
            try {
                info = {'name': 'new volume name', 'cpg': 'MyCPG', 'sizeMiB': 300}
                headers, body = http.post('/volumes', body=info)
            } except exceptions.HTTPUnauthorized as ex:
                print "Not logged in"
            }

        :param url: The relative url from the 3PAR api_url
        :type url: str

        :returns: headers - dict of HTTP Response headers
        :returns: body - the body of the response.  If the body was JSON, it will be an object
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
        :returns: body - the body of the response.  If the body was JSON, it will be an object
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
        :returns: body - the body of the response.  If the body was JSON, it will be an object
        """
        return self._cs_request(url, 'DELETE', **kwargs)
