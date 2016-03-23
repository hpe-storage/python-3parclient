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

"""Test class of 3Par Client handling Host."""

from test import HP3ParClient_base as hp3parbase

from hp3parclient import exceptions

# Insert colons into time string to match WWN format.
TIME2 = ""
for i in range(6):
    if i % 2 == 0:
        TIME2 += ":" + hp3parbase.TIME[i]
    else:
        TIME2 += hp3parbase.TIME[i]


DOMAIN = 'UNIT_TEST_DOMAIN'
HOST_NAME1 = 'HOST1_UNIT_TEST' + hp3parbase.TIME
HOST_NAME2 = 'HOST2_UNIT_TEST' + hp3parbase.TIME
WWN1 = "00:00:00:00:00" + TIME2
WWN2 = "11:11:11:11:11" + TIME2
IQN1 = 'iqn.1993-08.org.debian:01:00000' + hp3parbase.TIME
IQN2 = 'iqn.bogus.org.debian:01:0000' + hp3parbase.TIME


class HP3ParClientHostTestCase(hp3parbase.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientHostTestCase, self).setUp()

    def tearDown(self):
        try:
            self.cl.deleteHost(HOST_NAME1)
        except Exception:
            pass
        try:
            self.cl.deleteHost(HOST_NAME2)
        except Exception:
            pass

        # very last, tear down base class
        super(HP3ParClientHostTestCase, self).tearDown()

    def test_1_create_host_badParams(self):
        self.printHeader('create_host_badParams')

        name = 'UnitTestHostBadParams'
        optional = {'iSCSIPaths': 'foo bar'}
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          name,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_badParams')

    def test_1_create_host_no_name(self):
        self.printHeader('create_host_no_name')

        optional = {'domain': 'default'}
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          None,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_no_name')

    def test_1_create_host_exceed_length(self):
        self.printHeader('create_host_exceed_length')

        optional = {'domain': 'ThisDomainNameIsWayTooLongToMakeAnySense'}
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          HOST_NAME1,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_exceed_length')

    def test_1_create_host_empty_domain(self):
        self.printHeader('create_host_empty_domain')

        optional = {'domain': ''}
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          HOST_NAME1,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_empty_domain')

    def test_1_create_host_illegal_string(self):
        self.printHeader('create_host_illegal_string')

        optional = {'domain': 'doma&n'}
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          HOST_NAME1,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_illegal_string')

    def test_1_create_host_param_conflict(self):
        self.printHeader('create_host_param_conflict')
        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        iscsi = [IQN1, IQN2]
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          HOST_NAME1,
                          iscsi,
                          fc,
                          optional)

        self.printFooter('create_host_param_conflict')

    def test_1_create_host_wrong_type(self):
        self.printHeader('create_host_wrong_type')

        optional = {'domain': self.DOMAIN}
        fc = ['00:00:00:00:00:00:00']
        self.assertRaises(exceptions.HTTPBadRequest,
                          self.cl.createHost,
                          HOST_NAME1,
                          None,
                          fc,
                          optional)
        self.printFooter('create_host_wrong_type')

    def test_1_create_host_existent_path(self):
        self.printHeader('create_host_existent_path')
        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        self.assertRaises(exceptions.HTTPConflict,
                          self.cl.createHost,
                          HOST_NAME2,
                          None,
                          fc,
                          optional)

        self.printFooter('create_host_existent_path')

    def test_1_create_host_duplicate(self):
        self.printHeader('create_host_duplicate')

        optional = {'domain': self.DOMAIN}
        self.cl.createHost(HOST_NAME1, None, None, optional)
        self.assertRaises(exceptions.HTTPConflict,
                          self.cl.createHost,
                          HOST_NAME1,
                          None,
                          None,
                          optional)

        self.printFooter('create_host_duplicate')

    def test_1_create_host(self):
        self.printHeader('create_host')

        # add one
        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        # check
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertIsNotNone(host1)
        name1 = host1['name']
        self.assertEqual(HOST_NAME1, name1)
        # add another
        iscsi = [IQN1,
                 IQN2]
        self.cl.createHost(HOST_NAME2, iscsi, None, optional)
        # check
        host2 = self.cl.getHost(HOST_NAME2)
        self.assertIsNotNone(host2)
        name3 = host2['name']
        self.assertEqual(HOST_NAME2, name3)

        self.printFooter('create_host')

    def test_1_create_host_no_optional(self):
        self.printHeader('create_host_no_optional')

        # add one
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc)
        # check
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertIsNotNone(host1)
        name1 = host1['name']
        self.assertEqual(HOST_NAME1, name1)

        self.printFooter('create_host_no_optional')

    def test_2_delete_host_nonExist(self):
        self.printHeader("delete_host_non_exist")

        self.assertRaises(exceptions.HTTPNotFound,
                          self.cl.deleteHost,
                          "UnitTestNonExistHost")

        self.printFooter("delete_host_non_exist")

    def test_2_delete_host(self):
        self.printHeader("delete_host")

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        # check
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertIsNotNone(host1)

        hosts = self.cl.getHosts()
        if hosts and hosts['total'] > 0:
            for host in hosts['members']:
                if 'name' in host and host['name'] == HOST_NAME1:
                    self.cl.deleteHost(host['name'])

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)

        self.printFooter("delete_host")

    def test_3_get_host_bad(self):
        self.printHeader("get_host_bad")

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost,
                          "BadHostName")

        self.printFooter("get_host_bad")

    def test_3_get_host_illegal(self):
        self.printHeader("get_host_illegal")

        self.assertRaises(exceptions.HTTPBadRequest, self.cl.getHost,
                          "B&dHostName")

        self.printFooter("get_host_illegal")

    def test_3_get_hosts(self):
        self.printHeader("get_hosts")

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        iscsi = [IQN1,
                 IQN2]
        self.cl.createHost(HOST_NAME2, iscsi, None, optional)

        hosts = self.cl.getHosts()
        self.assertGreaterEqual(hosts['total'], 2)

        host_names = [host['name']
                      for host in hosts['members'] if 'name' in host]
        self.assertIn(HOST_NAME1, host_names)
        self.assertIn(HOST_NAME2, host_names)

    def test_3_get_host(self):
        self.printHeader("get_host")

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        host1 = self.cl.getHost(HOST_NAME1)
        self.assertEquals(host1['name'], HOST_NAME1)

        self.printFooter('get_host')

    def test_4_modify_host(self):
        self.printHeader('modify_host')

        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME2)

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        # validate host was created
        host1 = self.cl.getHost(HOST_NAME1)
        self.assertEquals(host1['name'], HOST_NAME1)

        # change host name
        mod_request = {'newName': HOST_NAME2}
        self.cl.modifyHost(HOST_NAME1, mod_request)

        # validate host name was changed
        host2 = self.cl.getHost(HOST_NAME2)
        self.assertEquals(host2['name'], HOST_NAME2)

        # host 1 name should be history
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getHost, HOST_NAME1)

        self.printFooter('modfiy_host')

    def test_4_modify_host_no_name(self):
        self.printHeader('modify_host_no_name')

        mod_request = {'newName': HOST_NAME1}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.modifyHost,
            None,
            mod_request
        )

        self.printFooter('modify_host_no_name')

    def test_4_modify_host_param_conflict(self):
        self.printHeader('modify_host_param_conflict')

        fc = [WWN1, WWN2]
        iscsi = [IQN1, IQN2]
        mod_request = {'newName': HOST_NAME1,
                       'FCWWNs': fc, 'iSCSINames': iscsi}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME2,
            mod_request
        )

        self.printFooter('modify_host_param_conflict')

    def test_4_modify_host_illegal_char(self):
        self.printHeader('modify_host_illegal_char')

        mod_request = {'newName': 'New#O$TN@ME'}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME2,
            mod_request
        )

        self.printFooter('modify_host_illegal_char')

    def test_4_modify_host_pathOperation_missing1(self):
        self.printHeader('modify_host_pathOperation_missing1')

        fc = [WWN1, WWN2]
        mod_request = {'FCWWNs': fc}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_pathOperation_missing1')

    def test_4_modify_host_pathOperation_missing2(self):
        self.printHeader('modify_host_pathOperation_missing2')

        iscsi = [IQN1, IQN2]
        mod_request = {'iSCSINames': iscsi}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_pathOperation_missing2')

    def test_4_modify_host_pathOperationOnly(self):
        self.printHeader('modify_host_pathOperationOnly')

        mod_request = {'pathOperation': 1}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME2,
            mod_request
        )

        self.printFooter('modify_host_pathOperationOnly')

    def test_4_modify_host_too_long(self):
        self.printHeader('modify_host_too_long')

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)
        mod_request = {'newName': 'ThisHostNameIsWayTooLongToMakeAnyRealSense'
                                  'AndIsDeliberatelySo'}
        self.assertRaises(
            exceptions.HTTPBadRequest,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_too_long')

    def test_4_modify_host_dup_newName(self):
        self.printHeader('modify_host_dup_newName')

        optional = {'domain': DOMAIN}
        fc = [WWN1, WWN2]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        iscsi = [IQN1, IQN2]
        self.cl.createHost(HOST_NAME2, iscsi, None, optional)
        mod_request = {'newName': HOST_NAME1}
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.modifyHost,
            HOST_NAME2,
            mod_request
        )

        self.printFooter('modify_host_dup_newName')

    def test_4_modify_host_nonExist(self):
        self.printHeader('modify_host_nonExist')

        mod_request = {'newName': HOST_NAME2}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_nonExist')

    def test_4_modify_host_existent_path(self):
        self.printHeader('modify_host_existent_path')

        optional = {'domain': DOMAIN}
        fc = [WWN1,
              WWN2]
        iscsi = [IQN1,
                 IQN2]

        self.cl.createHost(HOST_NAME1, None, fc, optional)
        self.cl.createHost(HOST_NAME2, iscsi, None, optional)

        mod_request = {'pathOperation': 1,
                       'iSCSINames': iscsi}
        self.assertRaises(
            exceptions.HTTPConflict,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_existent_path')

    def test_4_modify_host_nonExistent_path_iSCSI(self):
        self.printHeader('modify_host_nonExistent_path_iSCSI')

        optional = {'domain': DOMAIN}
        iscsi = [IQN1]
        self.cl.createHost(HOST_NAME1, iscsi, None, optional)

        iscsi2 = [IQN2]
        mod_request = {'pathOperation': 2,
                       'iSCSINames': iscsi2}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_nonExistent_path_iSCSI')

    def test_4_modify_host_nonExistent_path_fc(self):
        self.printHeader('modify_host_nonExistent_path_fc')
        optional = {'domain': DOMAIN}
        fc = [WWN1]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        fc2 = [WWN2]
        mod_request = {'pathOperation': 2,
                       'FCWWNs': fc2}
        self.assertRaises(
            exceptions.HTTPNotFound,
            self.cl.modifyHost,
            HOST_NAME1,
            mod_request
        )

        self.printFooter('modify_host_nonExistent_path_fc')

    def test_4_modify_host_add_fc(self):
        self.printHeader('modify_host_fc')

        optional = {'domain': DOMAIN}
        fc = [WWN1]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        fc2 = [WWN2]
        mod_request = {'pathOperation': 1,
                       'FCWWNs': fc2}
        self.cl.modifyHost(HOST_NAME1, mod_request)

        newHost = self.cl.getHost(HOST_NAME1)
        fc_paths = newHost['FCPaths']
        for path in fc_paths:
            if path['wwn'] == WWN2.replace(':', ''):
                self.printFooter('modify_host_add_fc')
                return
        self.fail('Failed to add FCWWN')

    def test_4_modify_host_remove_fc(self):
        self.printHeader('modify_host_remove_fc')

        optional = {'domain': DOMAIN}
        fc = [WWN1]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        mod_request = {'pathOperation': 2,
                       'FCWWNs': fc}
        self.cl.modifyHost(HOST_NAME1, mod_request)

        newHost = self.cl.getHost(HOST_NAME1)
        fc_paths = newHost['FCPaths']
        for path in fc_paths:
            if path['wwn'] == WWN1.replace(':', ''):
                self.fail('Failed to remove FCWWN')
                return

        self.printFooter('modify_host_remove_fc')

    def test_4_modify_host_add_iscsi(self):
        self.printHeader('modify_host_add_iscsi')

        optional = {'domain': DOMAIN}
        iscsi = [IQN1]
        self.cl.createHost(HOST_NAME1, iscsi, None, optional)

        iscsi2 = [IQN2]
        mod_request = {'pathOperation': 1,
                       'iSCSINames': iscsi2}
        self.cl.modifyHost(HOST_NAME1, mod_request)

        newHost = self.cl.getHost(HOST_NAME1)
        iscsi_paths = newHost['iSCSIPaths']
        for path in iscsi_paths:
            print(path)
            if path['name'] == IQN2:
                self.printFooter('modify_host_add_iscsi')
                return

        self.fail('Failed to add iSCSI')

    def test_4_modify_host_remove_iscsi(self):
        self.printHeader('modify_host_remove_iscsi')

        optional = {'domain': DOMAIN}
        iscsi = [IQN1]
        self.cl.createHost(HOST_NAME1, iscsi, None, optional)

        mod_request = {'pathOperation': 2,
                       'iSCSINames': iscsi}
        self.cl.modifyHost(HOST_NAME1, mod_request)

        newHost = self.cl.getHost(HOST_NAME1)
        iscsi_paths = newHost['iSCSIPaths']
        for path in iscsi_paths:
            if path['name'] == IQN2:
                self.fail('Failed to remove iSCSI')
                return

        self.printFooter('modify_host_remove_iscsi')

    def test_5_query_host_iqn(self):
        self.printHeader('query_host_iqn')
        optional = {'domain': DOMAIN}
        iscsi = [IQN1]
        self.cl.createHost(HOST_NAME1, iscsi, None, optional)

        hosts = self.cl.queryHost(iqns=[iscsi.pop()])
        self.assertIsNotNone(hosts)
        self.assertEqual(1, hosts['total'])
        self.assertEqual(hosts['members'].pop()['name'], HOST_NAME1)

        self.printFooter('query_host_iqn')

    def test_5_query_host_iqn2(self):
        # TODO test multiple iqns in one query
        pass

    def test_5_query_host_wwn(self):
        self.printHeader('query_host_wwn')
        optional = {'domain': DOMAIN}
        fc = [WWN1]
        self.cl.createHost(HOST_NAME1, None, fc, optional)

        hosts = self.cl.queryHost(wwns=[fc.pop().replace(':', '')])
        self.assertIsNotNone(hosts)
        self.assertEqual(1, hosts['total'])
        self.assertEqual(hosts['members'].pop()['name'], HOST_NAME1)

        self.printFooter('query_host_wwn')

    def test_5_query_host_wwn2(self):
        # TODO test multiple wwns in one query
        pass

    def test_5_query_host_iqn_and_wwn(self):
        self.printHeader('query_host_iqn_and_wwn')

        optional = {'domain': DOMAIN}
        iscsi = [IQN1]
        self.cl.createHost(HOST_NAME1, iscsi, None, optional)
        fc = [WWN1]
        self.cl.createHost(HOST_NAME2, None, fc, optional)

        hosts = self.cl.queryHost(iqns=[IQN1],
                                  wwns=[WWN1.replace(':', '')])

        self.assertIsNotNone(hosts)
        self.assertEqual(2, hosts['total'])
        self.assertIn(HOST_NAME1, [host['name'] for host in hosts['members']])
        self.assertIn(HOST_NAME2, [host['name'] for host in hosts['members']])
        self.printFooter('query_host_iqn_and_wwn')
