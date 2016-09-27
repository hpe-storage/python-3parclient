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

"""Test class of 3PAR Client for AOCFG query ."""

from test import HPE3ParClient_base as hpe3parbase
from hpe3parclient import exceptions

DOMAIN = 'UNIT_TEST_DOMAIN'

class HPE3ParClientAOCFGTestCase(hpe3parbase.HPE3ParClientBaseTestCase):

    def setUp(self):
        super(HPE3ParClientAOCFGTestCase, self).setUp()

    def tearDown(self):
        # very last, tear down base class
        super(HPE3ParClientAOCFGTestCase, self).tearDown()

    def test_1_get_AOCFG_bad(self):
        self.printHeader('get_AOCFG_bad')

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getAOCFG, 'BadName')

        self.printFooter('get_AOCFG_bad')

    def test_1_get_AOCFGs(self):
        self.printHeader('get_AOCFGs')

        cpgs = self.cl.getAOCFGs()
        self.assertGreater(len(cpgs), 0, 'getAOCFGs failed with no AOCFGs')
### We should test the links to cpgs....

        self.printFooter('get_AOCFGs')

# testing
# suite = unittest.TestLoader().loadTestsFromTestCase(HPE3ParClientAOCFGTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
