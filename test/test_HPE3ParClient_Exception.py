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

"""Test class of 3PAR Client handling exceptions."""

from test import HPE3ParClient_base as hpe3parbase
from hpe3parclient import exceptions


class HPE3ParClientExceptionTestCase(hpe3parbase.HPE3ParClientBaseTestCase):

    def setUp(self):
        super(HPE3ParClientExceptionTestCase, self).setUp()

    def tearDown(self):
        super(HPE3ParClientExceptionTestCase, self).tearDown()

    def test_from_response_string_format(self):
        self.printHeader('from_response')

        # Fake response representing an internal server error.
        class FakeResponse(object):
            status = 500
        fake_response = FakeResponse()

        output = exceptions.from_response(fake_response, {}).__str__()
        self.assertEquals('Internal Server Error (HTTP 500)', output)

        self.printFooter('from_response')

    def test_client_exception_string_format(self):
        self.printHeader('client_exception')

        fake_error = {'code': 999,
                      'desc': 'Fake Description',
                      'ref': 'Fake Ref',
                      'debug1': 'Fake Debug 1',
                      'debug2': 'Fake Debug 2', }

        # Create a fake exception and check that the output is
        # converted properly.
        client_ex = exceptions.ClientException(error=fake_error)
        client_ex.message = "Fake Error"
        client_ex.http_status = 500
        output = client_ex.__str__()

        self.assertEquals("Fake Error (HTTP 500) 999 - Fake Description - "
                          "Fake Ref (1: 'Fake Debug 1') (2: 'Fake Debug 2')",
                          output)

        self.printFooter('client_exception')
