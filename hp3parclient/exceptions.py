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
Exceptions for the client
"""

import pprint

class UnsupportedVersion(Exception):
    """Indicates that the user is trying to use an unsupported
    version of the API"""
    pass

class CommandError(Exception):
    pass

class AuthorizationFailure(Exception):
    pass

class NoUniqueMatch(Exception):
    pass

class ClientException(Exception):
    """
    The base exception class for all exceptions this library raises.
    """
    error_code = None
    error_desc = None

    debug1 = None
    debug2 = None
    def __init__(self, error=None):
        if 'code' in error:
            self.error_code = error['code']
        if 'desc' in error:
            self.error_desc = error['desc']
        if 'debug1' in error:
            self.debug1 = error['debug1']
        if 'debug2' in error:
            self.debug2 = error['debug2']


    def __str__(self):
        formatted_string = "%s (HTTP %s)" % (self.message, self.http_status)
        if self.error_code:
            formatted_string += " %s" % self.error_code
        if self.error_desc:
            formatted_string += " - %s" % self.error_desc

        if self.debug1:
            formatted_string += " (1: '%s')" % self.debug1

        if self.debug2:
            formatted_string += " (2: '%s')" % self.debug2
          
        return formatted_string


class BadRequest(ClientException):
    """
    HTTP 400 - Bad request: you sent some malformed data.
    """
    http_status = 400
    message = "Bad request"


class Unauthorized(ClientException):
    """
    HTTP 401 - Unauthorized: bad credentials.
    """
    http_status = 401
    message = "Unauthorized"


class Forbidden(ClientException):
    """
    HTTP 403 - Forbidden: your credentials don't give you access to this
    resource.
    """
    http_status = 403
    message = "Forbidden"


class NotFound(ClientException):
    """
    HTTP 404 - Not found
    """
    http_status = 404
    message = "Not found"

class MethodNotAllowed(ClientException):
    """
    HTTP 405 - Method not Allowed 
    """
    http_status = 405
    message = "Method Not Allowed"

class Conflict(ClientException):
    """
    HTTP 409 - Conflict: A Conflict happened on the server
    """
    http_status = 409
    message = "Conflict"

class OverLimit(ClientException):
    """
    HTTP 413 - Over limit: you're over the API limits for this time period.
    """
    http_status = 413
    message = "Over limit"



# NotImplemented is a python keyword.
class HTTPNotImplemented(ClientException):
    """
    HTTP 501 - Not Implemented: the server does not support this operation.
    """
    http_status = 501
    message = "Not Implemented"

# In Python 2.4 Exception is old-style and thus doesn't have a __subclasses__()
# so we can do this:
#     _code_map = dict((c.http_status, c)
#                      for c in ClientException.__subclasses__())
#
# Instead, we have to hardcode it:
_code_map = dict((c.http_status, c) for c in [BadRequest, Unauthorized,
                   Forbidden, NotFound, MethodNotAllowed, Conflict, 
                   OverLimit, HTTPNotImplemented])


def from_response(response, body):
    """
    Return an instance of an ClientException or subclass
    based on an httplib2 response.

    Usage::

        resp, body = http.request(...)
        if resp.status != 200:
            raise exception_from_response(resp, body)
    """
    cls = _code_map.get(response.status, ClientException)
    return cls(body)
