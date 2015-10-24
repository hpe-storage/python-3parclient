# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# (c) Copyright 2012-2015 Hewlett Packard Enterprise Development LP
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

.. module: exceptions

:Author: Walter A. Boring IV
:Description: This contains the HTTP exceptions that can come back from the
               REST calls to 3PAR
"""

import logging

# Python 3+ override
try:
    basestring
except NameError:
    basestring = str

LOG = logging.getLogger(__name__)


class UnsupportedVersion(Exception):
    """
    Indicates that the user is trying to use an unsupported version of the API
    """
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

    :param error: The error array
    :type error: array

    """
    _error_code = None
    _error_desc = None
    _error_ref = None

    _debug1 = None
    _debug2 = None

    def __init__(self, error=None):
        super(ClientException, self).__init__()

        if not error:
            return

        if isinstance(error, basestring):
            # instead of KeyError below, take it and make it the _error_desc.
            self._error_desc = error
        else:
            if 'code' in error:
                self._error_code = error['code']
            if 'desc' in error:
                self._error_desc = error['desc']
            if 'ref' in error:
                self._error_ref = error['ref']

            if 'debug1' in error:
                self._debug1 = error['debug1']
            if 'debug2' in error:
                self._debug2 = error['debug2']

    def get_code(self):
        return self._error_code

    def get_description(self):
        return self._error_desc

    def get_ref(self):
        return self._error_ref

    def __str__(self):
        formatted_string = self.message
        if self.http_status:
            formatted_string += " (HTTP %s)" % self.http_status
        if self._error_code:
            formatted_string += " %s" % self._error_code
        if self._error_desc:
            formatted_string += " - %s" % self._error_desc
        if self._error_ref:
            formatted_string += " - %s" % self._error_ref

        if self._debug1:
            formatted_string += " (1: '%s')" % self._debug1

        if self._debug2:
            formatted_string += " (2: '%s')" % self._debug2

        return formatted_string

# SSL Errors


class SSLCertFailed(ClientException):
    """
    The SSL certificate from the server could not be verified
    """
    http_status = ""
    message = "SSL Certificate Verification Failed"


#  Python Requests Errors


class RequestException(ClientException):
    """
    There was an ambiguous exception that occurred in Requests
    """
    pass


class ConnectionError(ClientException):
    """
    There was an error connecting to the server
    """
    pass


class HTTPError(ClientException):
    """
    An HTTP error occurred
    """
    pass


class URLRequired(ClientException):
    """
    A valid URL is required to make a request
    """
    pass


class TooManyRedirects(ClientException):
    """
    Too many redirects
    """
    pass


class Timeout(ClientException):
    """
    The request timed out
    """
    pass


# 400 Errors


class HTTPBadRequest(ClientException):
    """
    HTTP 400 - Bad request: you sent some malformed data.
    """
    http_status = 400
    message = "Bad request"


class HTTPUnauthorized(ClientException):
    """
    HTTP 401 - Unauthorized: bad credentials.
    """
    http_status = 401
    message = "Unauthorized"


class HTTPForbidden(ClientException):
    """
    HTTP 403 - Forbidden: your credentials don't give you access to this
    resource.
    """
    http_status = 403
    message = "Forbidden"


class HTTPNotFound(ClientException):
    """
    HTTP 404 - Not found
    """
    http_status = 404
    message = "Not found"


class HTTPMethodNotAllowed(ClientException):
    """
    HTTP 405 - Method not Allowed
    """
    http_status = 405
    message = "Method Not Allowed"


class HTTPNotAcceptable(ClientException):
    """
    HTTP 406 - Method not Acceptable
    """
    http_status = 406
    message = "Method Not Acceptable"


class HTTPProxyAuthRequired(ClientException):
    """
    HTTP 407 - The client must first authenticate itself with the proxy.
    """
    http_status = 407
    message = "Proxy Authentication Required"


class HTTPRequestTimeout(ClientException):
    """
    HTTP 408 - The server timed out waiting for the request.
    """
    http_status = 408
    message = "Request Timeout"


class HTTPConflict(ClientException):
    """
    HTTP 409 - Conflict: A Conflict happened on the server
    """
    http_status = 409
    message = "Conflict"


class HTTPGone(ClientException):
    """
    HTTP 410 - Indicates that the resource requested is no longer available and
               will not be available again.
    """
    http_status = 410
    message = "Gone"


class HTTPLengthRequired(ClientException):
    """
    HTTP 411 - The request did not specify the length of its content, which is
               required by the requested resource.
    """
    http_status = 411
    message = "Length Required"


class HTTPPreconditionFailed(ClientException):
    """
    HTTP 412 - The server does not meet one of the preconditions that the
               requester put on the request.
    """
    http_status = 412
    message = "Over limit"


class HTTPRequestEntityTooLarge(ClientException):
    """
    HTTP 413 - The request is larger than the server is willing or able to
               process
    """
    http_status = 413
    message = "Request Entity Too Large"


class HTTPRequestURITooLong(ClientException):
    """
    HTTP 414 - The URI provided was too long for the server to process.
    """
    http_status = 414
    message = "Request URI Too Large"


class HTTPUnsupportedMediaType(ClientException):
    """
    HTTP 415 - The request entity has a media type which the server or resource
               does not support.
    """
    http_status = 415
    message = "Unsupported Media Type"


class HTTPRequestedRangeNotSatisfiable(ClientException):
    """
    HTTP 416 - The client has asked for a portion of the file, but the server
               cannot supply that portion.
    """
    http_status = 416
    message = "Requested Range Not Satisfiable"


class HTTPExpectationFailed(ClientException):
    """
    HTTP 417 - The server cannot meet the requirements of the Expect
               request-header field.
    """
    http_status = 417
    message = "Expectation Failed"


class HTTPTeaPot(ClientException):
    """
    HTTP 418 - I'm a Tea Pot
    """
    http_status = 418
    message = "I'm A Teapot. (RFC 2324)"


# 500 Errors


class HTTPInternalServerError(ClientException):
    """
    HTTP 500 - Internal Server Error: an internal error occured.
    """
    http_status = 500
    message = "Internal Server Error"


class HTTPNotImplemented(ClientException):
    """
    HTTP 501 - Not Implemented: the server does not support this operation.
    """
    http_status = 501
    message = "Not Implemented"


class HTTPBadGateway(ClientException):
    """
    HTTP 502 - The server was acting as a gateway or proxy and received an
               invalid response from the upstream server.
    """
    http_status = 502
    message = "Bad Gateway"


class HTTPServiceUnavailable(ClientException):
    """
    HTTP 503 - The server is currently unavailable
    """
    http_status = 503
    message = "Service Unavailable"


class HTTPGatewayTimeout(ClientException):
    """
    HTTP 504 - The server was acting as a gateway or proxy and did
               not receive a timely response from the upstream server.
    """
    http_status = 504
    message = "Gateway Timeout"


class HTTPVersionNotSupported(ClientException):
    """
    HTTP 505 - The server does not support the HTTP protocol version used
               in the request.
    """
    http_status = 505
    message = "Version Not Supported"


# In Python 2.4 Exception is old-style and thus doesn't have a __subclasses__()
# so we can do this:
#     _code_map = dict((c.http_status, c)
#                      for c in ClientException.__subclasses__())
#
# Instead, we have to hardcode it:
_code_map = dict((c.http_status, c) for c in
                 [HTTPBadRequest, HTTPUnauthorized,
                  HTTPForbidden, HTTPNotFound, HTTPMethodNotAllowed,
                  HTTPNotAcceptable, HTTPProxyAuthRequired,
                  HTTPRequestTimeout, HTTPConflict, HTTPGone,
                  HTTPLengthRequired, HTTPPreconditionFailed,
                  HTTPRequestEntityTooLarge, HTTPRequestURITooLong,
                  HTTPUnsupportedMediaType, HTTPRequestedRangeNotSatisfiable,
                  HTTPExpectationFailed, HTTPTeaPot,
                  HTTPNotImplemented, HTTPBadGateway,
                  HTTPServiceUnavailable, HTTPGatewayTimeout,
                  HTTPVersionNotSupported, HTTPInternalServerError])


def from_response(response, body):
    """
    Return an instance of an ClientException or subclass
    based on a Python Requests response.

    Usage::

        resp, body = http.request(...)
        if resp.status != 200:
            raise exception_from_response(resp, body)

    """
    cls = _code_map.get(response.status, ClientException)
    return cls(body)


class SSHException(Exception):
    """This is the basis for the SSH Exceptions."""

    code = 500
    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in list(kwargs.items()):
                    LOG.error("%s: %s" % (name, value))
                # at least get the core message out if something happened
                message = self.message

        self.msg = message
        super(SSHException, self).__init__(message)


class SSHInjectionThreat(SSHException):
    message = "SSH command injection detected: %(command)s"


class GrowVolumeException(SSHException):
    message = "SSH grow volume failed: %(command)s"


class CopyVolumeException(SSHException):
    message = "SSH copy volume failed: %(command)s"


class SetQOSRuleException(SSHException):
    message = "SSH set QOS rule failed: %(command)s"


class SrstatldException(SSHException):
    message = "SSH command failed: %(command)s"


class ProcessExecutionError(Exception):
    def __init__(self, stdout=None, stderr=None, exit_code=None, cmd=None,
                 description=None):
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout
        self.cmd = cmd
        self.description = description

        if description is None:
            description = "Unexpected error while running command."
        if exit_code is None:
            exit_code = '-'
        message = ("%s\nCommand: %s\nExit code: %s\nStdout: %r\nStderr: %r"
                   % (description, cmd, exit_code, stdout, stderr))
        super(ProcessExecutionError, self).__init__(message)
