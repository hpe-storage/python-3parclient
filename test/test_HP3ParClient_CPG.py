# (c) Copyright 2015 Hewlett Packard Development Company, L.P.
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

"""Test class of 3Par Client handling CPG."""

import HP3ParClient_base as hp3parbase
from hp3parclient import exceptions

DOMAIN = 'UNIT_TEST_DOMAIN'
CPG_NAME1 = 'CPG1_UNIT_TEST' + hp3parbase.TIME
CPG_NAME2 = 'CPG2_UNIT_TEST' + hp3parbase.TIME


class HP3ParClientCPGTestCase(hp3parbase.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientCPGTestCase, self).setUp()

    def tearDown(self):
        try:
            self.cl.deleteCPG(CPG_NAME1)
        except Exception:
            pass

        try:
            self.cl.deleteCPG(CPG_NAME2)
        except Exception:
            pass

        # very last, tear down base class
        super(HP3ParClientCPGTestCase, self).tearDown()

    def test_1_create_CPG(self):
        self.printHeader('create_CPG')

        # add one
        optional = self.CPG_OPTIONS
        name = CPG_NAME1
        self.cl.createCPG(name, optional)

        # check
        cpg1 = self.cl.getCPG(name)
        self.assertIsNotNone(cpg1)
        cpgName = cpg1['name']
        self.assertEqual(name, cpgName)

        # add another
        name = CPG_NAME2
        optional2 = optional.copy()
        if self.CPG_LDLAYOUT_HA is None:
            more_optional = {'LDLayout': {'RAIDType': 2}}
        else:
            more_optional = {'LDLayout': {'RAIDType': 2,
                                          'HA': self.CPG_LDLAYOUT_HA}}
        optional2.update(more_optional)
        self.cl.createCPG(name, optional2)

        # check
        cpg2 = self.cl.getCPG(name)
        self.assertIsNotNone(cpg2)
        cpgName = cpg2['name']
        self.assertEqual(name, cpgName)

        self.printFooter('create_CPG')

    def test_1_create_CPG_badDomain(self):
        self.printHeader('create_CPG_badDomain')

        optional = {'domain': 'BAD_DOMAIN'}
        self.assertRaises(exceptions.HTTPNotFound, self.cl.createCPG,
                          CPG_NAME1, optional)

        self.printFooter('create_CPG_badDomain')

    def test_1_create_CPG_dup(self):
        self.printHeader('create_CPG_dup')

        optional = self.CPG_OPTIONS
        name = CPG_NAME1
        self.cl.createCPG(name, optional)
        self.assertRaises(exceptions.HTTPConflict, self.cl.createCPG,
                          CPG_NAME1, optional)

        self.printFooter('create_CPG_dup')

    def test_1_create_CPG_badParams(self):
        self.printHeader('create_CPG_badParams')

        optional = {'domainBad': 'UNIT_TEST'}
        self.assertRaises(exceptions.HTTPBadRequest, self.cl.createCPG,
                          CPG_NAME1, optional)

        self.printFooter('create_CPG_badParams')

    def test_1_create_CPG_badParams2(self):
        self.printHeader('create_CPG_badParams2')

        optional = {'domain': 'UNIT_TEST'}
        more_optional = {'LDLayout': {'RAIDBadType': 1}}
        optional.update(more_optional)
        self.assertRaises(exceptions.HTTPBadRequest, self.cl.createCPG,
                          CPG_NAME1, optional)

        self.printFooter('create_CPG_badParams2')

    def test_2_get_CPG_bad(self):
        self.printHeader('get_CPG_bad')

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getCPG, 'BadName')

        self.printFooter('get_CPG_bad')

    def test_2_get_CPGs(self):
        self.printHeader('get_CPGs')

        optional = self.CPG_OPTIONS
        name = CPG_NAME1
        self.cl.createCPG(name, optional)

        cpgs = self.cl.getCPGs()
        self.assertGreater(len(cpgs), 0, 'getCPGs failed with no CPGs')
        self.assertTrue(self.findInDict(cpgs['members'], 'name', CPG_NAME1))

        self.printFooter('get_CPGs')

    def test_3_delete_CPG_nonExist(self):
        self.printHeader('delete_CPG_nonExist')

        self.assertRaises(exceptions.HTTPNotFound, self.cl.deleteCPG,
                          'NonExistCPG')

        self.printFooter('delete_CPG_nonExist')

    def test_3_delete_CPGs(self):
        self.printHeader('delete_CPGs')

        # add one
        optional = self.CPG_OPTIONS
        self.cl.createCPG(CPG_NAME1, optional)

        cpg = self.cl.getCPG(CPG_NAME1)
        self.assertTrue(cpg['name'], CPG_NAME1)

        cpgs = self.cl.getCPGs()
        if cpgs and cpgs['total'] > 0:
            for cpg in cpgs['members']:
                if cpg['name'] == CPG_NAME1:
                    # pprint.pprint("Deleting CPG %s " % cpg['name'])
                    self.cl.deleteCPG(cpg['name'])

        # check
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getCPG, CPG_NAME1)

        self.printFooter('delete_CPGs')

    def test_4_get_cpg_available_space(self):
        self.printHeader('get_cpg_available_space')

        optional = self.CPG_OPTIONS
        name = CPG_NAME1
        self.cl.createCPG(name, optional)

        cpg1 = self.cl.getCPGAvailableSpace(name)
        self.assertIsNotNone(cpg1)

        self.printFooter('get_cpg_available_space')

    def test_4_get_cpg_available_space_bad_cpg(self):
        self.printHeader('get_cpg_available_space_bad_cpg')

        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.getCPGAvailableSpace,
            'BadName')

        self.printFooter('get_cpg_available_space_bad_cpg')


# testing
# suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientCPGTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
