# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
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

"""Test class of 3Par Client handling File Persona API."""

import pprint
import re
import time
import unittest

from testconfig import config
from functools import wraps

from test import HPE3ParClient_base as hpe3parbase

cpgs_to_delete = []
fpgs_to_delete = []
vfss_to_delete = []
fstores_to_delete = []
fshares_to_delete = []
SKIP_MSG = "Skipping test because skip_file_persona=true in config."


def is_live_test():
    return config['TEST']['unit'].lower() == 'false'


def skip_file_persona():
    return config['TEST']['skip_file_persona'].lower() == 'true'


class HPE3ParFilePersonaClientTestCase(hpe3parbase.HPE3ParClientBaseTestCase):

    interfaces = None
    DEBUG = config['TEST']['debug'].lower() == 'true'

    def debug_print(self, obj, **kwargs):
        if self.DEBUG:
            print(pprint.pformat(obj, **kwargs))

    def setUp(self, withSSH=True, withFilePersona=True):
        self.withSSH = withSSH
        self.withFilePersona = withFilePersona
        super(HPE3ParFilePersonaClientTestCase, self).setUp(
            withSSH=self.withSSH, withFilePersona=self.withFilePersona)

        # Only get the tpdinterface once and reuse it for all the tests.
        if self.interfaces is None:
            self.interfaces = self.cl.gettpdinterface()

            save_interface = open('test/tpdinterface/interface.save', 'w')
            for k, v in list(self.interfaces.items()):
                save_interface.write(' {%s {' % k)
                for header in v:
                    if isinstance(header, str):
                        save_interface.write(' {%s 0}' % header)
                    else:
                        h, sub = header
                        save_interface.write(' {%s 0}' % h)
                        for s in sub:
                            save_interface.write(' {%s,%s 0}' % (h, s))

                save_interface.write('}}')
            save_interface.close()

        else:
            self.cl.interfaces = HPE3ParFilePersonaClientTestCase.interfaces

    def tearDown(self):
        """Clean-up -- without fail -- more than humanly possible."""

        # Start by removing and cleaning fsnaps so other things can be deleted.
        for fpgname, vfsname, fstore in fstores_to_delete:
            try:
                self.cl.removefsnap(vfsname, fstore, fpg=fpgname)
                self.cl.startfsnapclean(fpgname, reclaimStrategy='maxspeed')

                # TODO: get smart about cleaning snapshots
                time.sleep(5)

            except Exception as e:
                print(e)
                pass

        for fpgname, vfsname, fstore, share, protocol in fshares_to_delete:
            try:
                self.cl.removefshare(protocol, vfsname, share,
                                     fstore=fstore,
                                     fpg=fpgname)
            except Exception as e:
                print(e)
                pass
        del fshares_to_delete[:]

        for fpgname, vfsname, fstore in fstores_to_delete:
            try:
                self.cl.removefstore(vfsname, fstore, fpg=fpgname)
            except Exception as e:
                print(e)
                pass
        del fstores_to_delete[:]

        for fpgname, vfsname in vfss_to_delete:
            try:
                self.cl.removevfs(vfsname, fpg=fpgname)
            except Exception as e:
                print(e)
                pass
        del vfss_to_delete[:]

        for fpgname in fpgs_to_delete:
            try:
                self.cl.removefpg(fpgname, wait=True)
            except Exception as e:
                print(e)
                pass
        del fpgs_to_delete[:]

        for cpgname in cpgs_to_delete:
            try:
                self.cl.deleteCPG(cpgname)
            except Exception as e:
                print(e)
                pass
        del cpgs_to_delete[:]

        # very last, tear down base class
        super(HPE3ParFilePersonaClientTestCase, self).tearDown()

    def print_header_and_footer(func):
        """Print header and footer for unit tests."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            test = args[0]
            test.printHeader(unittest.TestCase.id(test))
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            print("Elapsed Time: %ss" % elapsed_time)
            test.printFooter(unittest.TestCase.id(test))
            return result
        return wrapper

    def find_expected_in_result(self, expected, result):
        for line in result:
            if re.search(expected, line):
                break
        else:
            print("Did NOT find expected error. Expected: %s" % expected)
            print(pprint.pformat(result))
            self.fail("Did NOT find expected error. Expected: %s" % expected)

    def find_expected_key_val_in_members(self, expected, members):
        for member in members:
            if expected in list(member.items()):
                break
        else:
            self.fail("Did NOT find expected error. Expected: %s" % expected)

    def get_fpg_count(self):
        return self.cl.getfpg()['total']

    def get_vfs_count(self, fpg=None):
        return self.cl.getvfs(fpg=fpg)['total']

    def validate_getfs_members(self, members):

        for member in members:
            self.assertEqual([], member['ad'])

            self.assertIsInstance(member['auth'], dict)
            self.assertIsInstance(member['auth']['order'], list)
            for auth in member['auth']['order']:
                self.assertIn(auth, ['Ldap', 'ActiveDirectory', 'Local'])

            self.assertIsInstance(member['dns'], dict)
            self.assertIsInstance(member['dns']['addresses'], str)
            self.assertIsInstance(member['dns']['suffixes'], str)

            self.assertIsInstance(member['gwaddress'], dict)
            self.assertIsInstance(member['gwaddress']['address'], str)
            self.assertIsInstance(member['gwaddress']['nsCuid'], str)

            self.assertIsInstance(member['httpobj'], list)
            for httpobj in member['httpobj']:
                self.assertIn(httpobj['keepAlive'], ('true', 'false'))
                self.assertIsInstance(int(httpobj['keepAliveTimeout']), int)
                self.assertIsInstance(int(httpobj['maxClients']), int)
                self.assertIsInstance(int(httpobj['ports']), int)
                self.assertIsInstance(httpobj['profileName'], str)
                self.assertIsInstance(int(httpobj['rBlockSize']), int)
                self.assertIsInstance(int(httpobj['sslPorts']), int)
                self.assertIsInstance(int(httpobj['wBlockSize']), int)

            self.assertEqual([], member['ldap'])

            self.assertEqual(4, len(member['node']))
            for node in member['node']:
                self.assertIn(node['activeNode'], ('Yes', 'No'))
                self.assertIn(node['bondMode'], ('1', '6', '-'))
                self.assertIn(node['fsvcList'], ('Yes', 'No'))
                self.assertIn(node['fsvcState'], ('running', 'Unknown'))
                self.assertIn(node['inCluster'], ('Yes', 'No'))
                self.assertIsInstance(node['mtu'], str)
                self.assertIn(node['nodeId'], ('0', '1', '2', '3'))
                self.assertIsInstance(node['nodeName'], str)
                self.assertIn(node['nspList'],
                              ('0:2:1,0:2:2', '1:2:1,1:2:2', '-'))
                self.assertIsInstance(node['version'], str)

            for node_ip in member['nodeIp']:
                self.assertIsInstance(node_ip['address'], str)
                self.assertIsInstance(int(node_ip['nodeId']), int)
                self.assertIsInstance(node_ip['nsCuid'], str)
                self.assertIsInstance(node_ip['subnet'], str)
                self.assertIsInstance(node_ip['vlantag'], str)

    def validate_getfpg_members(self, members):
        for member in members:
            self.assertIsNotNone(member['CompId'])
            self.assertIsInstance(int(member['alternateNode']), int)
            self.assertIsInstance(int(member['availCapacityKiB']), int)
            self.assertIsInstance(int(member['capacityKiB']), int)
            self.assertIsInstance(member['comment'], str)
            self.assertIsInstance(int(member['createTime']), int)
            self.assertIsInstance(int(member['currentNode']), int)
            self.assertIn('defaultCpg', member)

            self.assertIsInstance(member['domains'], list)
            for domain in member['domains']:
                self.assertIsInstance(domain['filesets'], str)
                self.assertIsInstance(domain['fsname'], str)

                # Domain hosts typically look like ['node1fs', 'node0fs']
                self.assertIsInstance(domain['hosts'], list)
                for host in domain['hosts']:
                    self.assertIsInstance(host, str)
                self.assertIsInstance(domain['ipfsType'], str)
                self.assertIsInstance(domain['name'], str)
                self.assertIsInstance(int(domain['owner']), int)

                # volumes is ID or list of IDs
                if isinstance(domain['volumes'], list):
                    for vol_id in domain['volumes']:
                        self.assertIsInstance(int(vol_id), int)
                else:
                    self.assertIsInstance(int(domain['volumes']), int)

            self.assertIsInstance(int(member['fFree']), int)
            self.assertIsInstance(int(member['filesUsed']), int)
            self.assertIsInstance(int(member['freeCapacityKiB']), int)
            self.assertIn(member['freezeState'], ['NOT_FROZEN', 'UNKNOWN'])
            fpgname = member['fsname']
            self.assertIsInstance(fpgname, str)
            self.assertIsInstance(int(member['generation']), int)
            self.assertIsInstance(member['hosts'], list)
            self.assertIn(member['isolationState'],
                          ['ACCESSIBLE', 'UNKNOWN'])
            self.assertIn(member['mountStates'],
                          ['ACTIVATED',
                           'DEACTIVATED',
                           'MOUNTING',
                           'UNMOUNTING',
                           ])
            self.assertIsInstance(member['mountpath'], str)
            self.assertTrue(member['mountpath'].startswith('/'))
            self.assertIsInstance(int(member['number']), int)
            self.assertIsInstance(int(member['overallStateInt']), int)
            self.assertIsInstance(int(member['primaryNode']), int)

            self.assertIsInstance(member['segments'], list)
            for segment in member['segments']:
                self.assertIsInstance(int(segment['availCapacityKiB']), int)
                self.assertIsInstance(int(segment['capacityKiB']), int)
                self.assertIsInstance(segment['domain'], str)
                self.assertIsInstance(int(segment['fFree']), int)
                self.assertIsInstance(int(segment['files']), int)
                self.assertIsInstance(segment['fileset'], str)
                self.assertIsInstance(int(segment['freeCapacityKiB']), int)
                self.assertIsInstance(segment['fsname'], str)
                self.assertIsInstance(segment['ipfsType'], str)
                self.assertIsInstance(int(segment['number']), int)
                self.assertIn(segment['readOnly'], ['true', 'false'])
                self.assertIn(segment['unavailable'], ['true', 'false'])

            self.assertIsInstance(int(member['usedCapacityKiB']), int)
            self.assertIsInstance(member['uuid'], str)

            self.assertIsInstance(member['volumes'], list)
            for volume in member['volumes']:
                self.assertIsInstance(int(volume['capacityInMb']), int)

                # Volume hosts should be something like ['0', '1']
                self.assertIsInstance(volume['hosts'], list)
                for host in volume['hosts']:
                    self.assertIsInstance(int(host), int)

                self.assertIsInstance(int(volume['lunUuid']), int)
                self.assertFalse(volume['name'])  # Name is always empty

            def validate_vv_name(fpg_name, vv_name):
                """Expect vv name to look like 'fpg_name.#'."""
                self.assertIsInstance(vv_name, str)
                vv_split = vv_name.split('.')
                self.assertEqual(fpg_name, vv_split[0])
                self.assertIsInstance(int(vv_split[1]), int)

            if isinstance(member['vvs'], list):
                for vv in member['vvs']:
                    validate_vv_name(fpgname, vv)
            else:
                vv = member['vvs']
                self.assertIsInstance(vv, str)
                validate_vv_name(fpgname, vv)

    def validate_getvfs_members(self, members):
        for member in members:
            self.assertIsInstance(member['CompId'], str)
            self.assertIsInstance(int(member['bgrace']), int)
            self.assertIsInstance(member['certs'], str)
            self.assertIsInstance(member['comment'], str)
            self.assertIsInstance(member['fspname'], str)
            self.assertIsInstance(int(member['igrace']), int)
            self.assertIsInstance(int(member['overallStateInt']), int)
            self.assertIsInstance(member['uuid'], str)
            self.assertIsInstance(member['vfsip'], str)
            self.assertIsInstance(member['vfsname'], str)

    def validate_fs(self, expected_count=None):

        result = self.cl.getfs()
        self.debug_print("DEBUG: getfs result...")
        self.debug_print(result)

        total = result['total']
        message = result['message']
        members = result['members']

        # Validate contents
        if total == 0:
            self.assertEqual([], members)
        else:
            self.assertIsNone(message)
            self.validate_getfs_members(members)

        # Compare against expected count
        if expected_count is not None:
            self.assertEqual(expected_count, total)

    def validate_fpg(self, fpgname=None, no_fpgname=None, expected_count=None):

        result = self.cl.getfpg()
        self.debug_print("DEBUG: getfpg result...")
        self.debug_print(result)

        total = result['total']
        message = result['message']
        members = result['members']

        # Validate contents
        if total == 0:
            self.assertEqual([], members)
            self.assertIn(message, ('No File Provisioning Groups found.',
                                    None))
        else:
            self.assertIsNone(message)
            self.validate_getfpg_members(members)

        # Compare against expected count
        if expected_count is not None:
            self.assertEqual(expected_count, total)

        # Look for expected
        if fpgname:
            for member in result['members']:
                if member['fsname'] == fpgname:
                    break
            else:
                self.fail('Did NOT find expected FPG %s' % fpgname)

        # Look for expected _not_existing_
        if no_fpgname:
            for member in result['members']:
                if member['fsname'] == no_fpgname:
                    self.fail('Found unexpected FPG %s.' % fpgname)

    def validate_vfs(self, fpgname=None, vfsname=None, no_vfsname=None,
                     expected_count=None):

        result = self.cl.getvfs(fpg=fpgname)
        self.debug_print("DEBUG: getvfs result...")
        self.debug_print(result)

        total = result['total']
        message = result['message']

        # Validate contents
        if fpgname is not None:
            success_message = None
            not_found_message = 'Invalid VFS %s\r' % vfsname
            self.assertIn(message, (success_message, not_found_message))
        elif total == 0:
            self.assertEqual('', message)
        else:
            self.assertIsNone(message)

        # Compare against expected count
        if expected_count is not None:
            self.assertEqual(expected_count, total)

        # Look for expected
        if vfsname:
            for member in result['members']:
                if member['vfsname'] == vfsname and (
                   fpgname is None or member['fspname'] == fpgname):
                    break
            else:
                self.fail('Did NOT find expected VFS %s' % vfsname)

        # Look for expected _not_existing_
        if no_vfsname:
            for member in result['members']:
                if member['vfsname'] == no_vfsname and (
                   fpgname is None or member['fspname'] == fpgname):
                    self.fail('Found unexpected VFS %s.' % no_vfsname)

    @unittest.skipIf(is_live_test(),
                     "Skip on real array which may have exiting VFSs.")
    @print_header_and_footer
    def test_getvfs_empty(self):
        self.validate_vfs(expected_count=0)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_getfs(self):
        self.validate_fs(expected_count=1)

    @unittest.skipIf(is_live_test(),
                     "Skip on real array which may have exiting VFSs.")
    @print_header_and_footer
    def test_getfpg_empty(self):
        self.validate_fpg(expected_count=0)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_getfpg_bogus(self):
        result = self.cl.getfpg('bogus1', 'bogus2', 'bogus3')
        expected_message = 'File Provisioning Group: bogus1 not found\r'
        self.assertEqual(expected_message, result['message'])
        self.assertEqual(0, result['total'])
        self.assertEqual([], result['members'])

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createfpg_bogus_cpg(self):

        fpg_count = self.get_fpg_count()

        test_prefix = 'UT1_'
        fpgname = test_prefix + "FPG_" + hpe3parbase.TIME
        fpgs_to_delete.append(fpgname)

        bogus_cpgname = 'thiscpgdoesnotexist'
        result = self.cl.createfpg(bogus_cpgname, fpgname, '1X')
        self.assertEqual(
            'Error: Invalid CPG name: %s\r' % bogus_cpgname,
            result[0])

        self.validate_fpg(expected_count=fpg_count)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createfpg_bad_size(self):
        test_prefix = 'UT2_'

        fpg_count = self.get_fpg_count()

        fpgname = test_prefix + "FPG_" + hpe3parbase.TIME
        fpgs_to_delete.append(fpgname)

        # Create a CPG for the test
        cpgname = test_prefix + "CPG_" + hpe3parbase.TIME
        cpgs_to_delete.append(cpgname)
        optional = self.CPG_OPTIONS.copy()
        optional.pop('domain', None)  # File Persona doesn't allow a domain
        self.cl.createCPG(cpgname, optional)

        result = self.cl.createfpg(cpgname, fpgname, '1X')
        self.assertEqual(
            'The suffix, X, for size is invalid.\r', result[0])

        self.validate_fpg(expected_count=fpg_count)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createfpg_in_domain_err(self):

        fpg_count = self.get_fpg_count()

        test_prefix = 'UT3_'
        fpgname = test_prefix + "FPG_" + hpe3parbase.TIME
        fpgs_to_delete.append(fpgname)

        # Create a CPG for the test
        cpgname = test_prefix + "CPG_" + hpe3parbase.TIME
        cpgs_to_delete.append(cpgname)
        optional = self.CPG_OPTIONS
        self.cl.createCPG(cpgname, optional)

        result = self.cl.createfpg(cpgname, fpgname, '1T', wait=True)

        expected = 'belongs to domain.*which cannot be used for File Services.'
        self.find_expected_in_result(expected, result)

        self.validate_fpg(expected_count=fpg_count)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createfpg_twice_and_remove(self):

        fpg_count = self.get_fpg_count()

        test_prefix = 'UT4_'
        fpgname = test_prefix + "FPG_" + hpe3parbase.TIME
        fpgs_to_delete.append(fpgname)

        # Create a CPG for the test
        cpgname = test_prefix + "CPG_" + hpe3parbase.TIME
        cpgs_to_delete.append(cpgname)
        optional = self.CPG_OPTIONS.copy()
        optional.pop('domain', None)  # File Persona doesn't allow domain
        self.cl.createCPG(cpgname, optional)

        # Create FPG once to test createfpg
        result = self.cl.createfpg(cpgname, fpgname, '1T', wait=True)
        expected = 'File Provisioning Group *%s created.' % fpgname
        self.find_expected_in_result(expected, result)
        expected = 'File Provisioning Group *%s activated.' % fpgname
        self.find_expected_in_result(expected, result)
        self.validate_fpg(fpgname=fpgname, expected_count=fpg_count + 1)

        # Create same FPG again to test createfpg already exists error
        result = self.cl.createfpg(cpgname, fpgname, '1T', wait=True)
        expected = ('Error: FPG %s already exists\r' %
                    fpgname)
        self.assertEqual(expected, result[0])
        self.validate_fpg(fpgname=fpgname, expected_count=fpg_count + 1)

        # Test removefpg
        self.cl.removefpg(fpgname, wait=True)
        self.validate_fpg(no_fpgname=fpgname, expected_count=fpg_count)

    def get_or_create_fpg(self, test_prefix):

        fpgname = config['TEST'].get('fpg')
        if fpgname is not None:
            return fpgname

        fpgname = test_prefix + "FPG_" + hpe3parbase.TIME
        fpgs_to_delete.append(fpgname)
        # Create a CPG for the test
        cpgname = test_prefix + "CPG_" + hpe3parbase.TIME
        cpgs_to_delete.append(cpgname)
        optional = self.CPG_OPTIONS.copy()
        optional.pop('domain', None)  # File Persona doesn't allow a domain
        self.cl.createCPG(cpgname, optional)
        # Create FPG
        result = self.cl.createfpg(cpgname, fpgname, '1T', wait=True)
        expected = 'File Provisioning Group *%s created.' % fpgname
        self.find_expected_in_result(expected, result)
        expected = 'File Provisioning Group *%s activated.' % fpgname
        self.find_expected_in_result(expected, result)
        self.validate_fpg(fpgname=fpgname)
        return fpgname

    def get_or_create_vfs(self, test_prefix, fpgname):

        vfsname = config['TEST'].get('vfs')
        if vfsname is not None:
            return vfsname
        vfsname = test_prefix + "VFS_" + hpe3parbase.TIME
        bgrace = '11'
        igrace = '22'
        comment = 'this is a test comment'
        vfss_to_delete.append((fpgname, vfsname))
        result = self.cl.createvfs('127.0.0.2', '255.255.0.0', vfsname,
                                   fpg=fpgname,
                                   bgrace=bgrace, igrace=igrace,
                                   comment=comment,
                                   wait=True)
        expected = 'Created VFS "%s" on FPG %s.' % (vfsname, fpgname)
        self.find_expected_in_result(expected, result)
        self.validate_vfs(fpgname=fpgname, vfsname=vfsname)
        return vfsname

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createvfs_bogus_bgrace(self):
        test_prefix = 'UT6_'
        fpgname = self.get_or_create_fpg(test_prefix)
        vfsname = self.get_or_create_vfs(test_prefix, fpgname)
        result = self.cl.createvfs('127.0.0.2', '255.255.255.0', vfsname,
                                   fpg=fpgname,
                                   bgrace='bogus', igrace='60',
                                   wait=True)
        self.assertEqual('bgrace value should be between 1 and 2147483647\r',
                         result[0])

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_createvfs_bogus_igrace(self):
        test_prefix = 'UT6_'
        fpgname = self.get_or_create_fpg(test_prefix)
        vfsname = self.get_or_create_vfs(test_prefix, fpgname)
        result = self.cl.createvfs('127.0.0.2', '255.255.255.0', vfsname,
                                   fpg=fpgname,
                                   bgrace='60', igrace='bogus',
                                   wait=True)
        self.assertEqual('igrace value should be between 1 and 2147483647\r',
                         result[0])

    def get_fsips(self, fpgname, vfsname):
        """Test FSIPS after VFS is created."""

        result = self.cl.getfsip(vfsname, fpg=fpgname)
        self.debug_print(result)
        self.assertEqual(None, result['message'])
        self.assertEqual(1, result['total'])
        member = result['members'][0]
        self.assertEqual(fpgname, member['fspool'])
        self.assertEqual(vfsname, member['vfs'])
        self.assertEqual('user', member['networkName'])
        self.assertEqual('0', member['vlanTag'])
        uid_match = '^[0-f]*$'
        self.assertIsNotNone(re.match(uid_match, member['policyID']))
        ip_addr_ish = r'[0-9.]*$'
        self.assertIsNotNone(re.match(ip_addr_ish, member['address']),
                             '%s does not look like an IP Addr.' %
                             member['address'])
        self.assertIsNotNone(re.match(ip_addr_ish, member['prefixLen']),
                             '%s does not look like an IP Addr.' %
                             member['prefixLen'])
        result = self.cl.getfsip(vfsname, fpg='bogus')
        self.debug_print(result)
        expected = {
            'message': 'File Provisioning Group: bogus not found\r',
            'total': 0,
            'members': []
        }
        self.assertEqual(expected, result)
        result = self.cl.getfsip('bogus', fpg=fpgname)
        self.debug_print(result)
        expected = {
            'message': 'Invalid VFS bogus\r',
            'total': 0,
            'members': []
        }
        self.assertEqual(expected, result)

    def validate_fstores(self, result):
        self.assertIsNone(result['message'])
        self.assertEqual(len(result['members']), result['total'])
        for member in result['members']:
            self.assertTrue(member['CompId'].isdigit())
            self.assertIsInstance(member['comment'], str)
            self.assertIsInstance(member['fspoolName'], str)
            self.assertIsInstance(member['fstoreName'], str)
            self.assertTrue(member['overallStateInt'].isdigit())
            uid_match = '^[\-0-f]*$'
            self.assertIsNotNone(re.match(uid_match, member['uuid']))
            self.assertIsInstance(member['vfsName'], str)

    def validate_fstore(self, result, fpgname, vfsname, fstore, comment):
        self.assertIsNone(result['message'])
        self.assertEqual(1, result['total'])
        member = result['members'][0]
        self.assertTrue(member['CompId'].isdigit())
        self.assertEqual(comment, member['comment'])
        self.assertEqual(fpgname, member['fspoolName'])
        self.assertEqual(fstore, member['fstoreName'])
        self.assertTrue(member['overallStateInt'].isdigit())
        uid_match = '^[\-0-f]*$'
        self.assertIsNotNone(re.match(uid_match, member['uuid']))
        self.assertEqual(vfsname, member['vfsName'])

    def crud_fstore(self, fpgname, vfsname, fstore):
        fstores_to_delete.append((fpgname, vfsname, fstore))
        comment = "This is the CRUD test fstore."

        result = self.cl.createfstore(vfsname, fstore, fpg=fpgname,
                                      comment=comment)
        self.assertEqual([], result)

        result = self.cl.getfstore(fpg=fpgname, vfs=vfsname, fstore=fstore)
        self.validate_fstore(result, fpgname, vfsname, fstore, comment)

        new_comment = "new comment"
        result = self.cl.setfstore(vfsname, fstore, fpg=fpgname,
                                   comment=new_comment)
        self.assertEqual([], result)

        result = self.cl.getfstore(fpg=fpgname, vfs=vfsname, fstore=fstore)
        self.validate_fstore(result, fpgname, vfsname, fstore, new_comment)

        result = self.cl.getfstore()
        self.validate_fstores(result)
        pre_remove_total = result['total']

        result = self.cl.removefstore(vfsname, fstore, fpg=fpgname)
        self.assertEqual(['%s removed' % fstore], result)

        result = self.cl.getfstore(fpg=fpgname, vfs=vfsname, fstore=fstore)
        self.assertGreater(pre_remove_total, result['total'])

    def create_share(self, protocol, fpgname, vfsname, share_name, comment):
        fstores_to_delete.append((fpgname, vfsname, share_name))
        fshares_to_delete.append((fpgname, vfsname, share_name, share_name,
                                  protocol))
        result = self.cl.createfshare(protocol, vfsname, share_name,
                                      fpg=fpgname, fstore=share_name,
                                      comment=comment)
        self.assertEqual([], result)

    def create_fsnap(self, fpgname, vfsname, fstore, tag):

        # Test error messages with bogus names
        result = self.cl.createfsnap('bogus', fstore, tag, fpg=fpgname)
        self.assertEqual(['Virtual Server bogus does not exist on FPG %s\r' %
                          fpgname], result)
        result = self.cl.createfsnap(vfsname, 'bogus', tag, fpg=fpgname)
        self.assertEqual(['File Store bogus does not exist on FPG %s\r' %
                          fpgname], result)
        result = self.cl.createfsnap(vfsname, fstore, tag, fpg='bogus')
        self.assertEqual(['FPG bogus not found\r'], result)

        result = self.cl.getfsnap('bogus',
                                  fpg=fpgname, vfs=vfsname, fstore=fstore,
                                  pat=True)
        self.assertEqual({'members': [], 'message': None, 'total': 0},
                         result)
        result = self.cl.getfsnap('bogus',
                                  fpg=fpgname, vfs=vfsname, fstore=fstore)
        expected = {
            'members': [],
            'message': 'SnapShot bogus does not exist on FPG %s path '
                       '%s/%s\r' % (fpgname, vfsname, fstore),
            'total': 0}
        self.assertEqual(expected, result)

        result = self.cl.createfsnap(vfsname, fstore, tag, fpg=fpgname,
                                     retain=0)
        self.assertTrue(result[0].endswith('_%s' % tag))

        result = self.cl.getfsnap('*%s' % tag,
                                  fpg=fpgname, vfs=vfsname, fstore=fstore,
                                  pat=True)
        member = result['members'][0]
        self.assertTrue(member['CompId'].isdigit())
        self.assertTrue(member['createTime'].isdigit())
        self.assertEqual(fpgname, member['fspName'])
        self.assertEqual(fstore, member['fstoreName'])
        snapname = member['snapName']
        self.assertTrue(snapname.endswith('_%s' % tag))
        self.assertEqual(vfsname, member['vfsName'])

        self.assertEqual(1, result['total'])
        self.assertIsNone(result['message'])

        # Test get by name instead of pattern
        result2 = self.cl.getfsnap(snapname,
                                   fpg=fpgname, vfs=vfsname, fstore=fstore)
        # For some reason, when -pat is not used the result does not include
        # a CompId.  Otherwise the results should be identical (same fsnap).
        self.debug_print(result)
        self.debug_print(result2)
        del member['CompId']  # For some reason this is not in result2.
        self.assertEqual(result, result2)  # Should be same result

        result = self.cl.createfsnap(vfsname, fstore, tag, fpg=fpgname)
        self.assertTrue(result[0].endswith('_%s' % tag))

        result = self.cl.removefsnap(vfsname, fstore, fpg=fpgname,
                                     snapname=snapname)
        self.assertEqual([], result)
        result = self.cl.removefsnap(vfsname, fstore, fpg=fpgname)
        self.assertEqual([], result)

        success = []
        running = ['Reclamation already running on %s\r' % fpgname]
        expected_in = (success, running)
        # After first one expect 'running', but to avoid timing issues in
        # the test results accept either success or running.
        result = self.cl.startfsnapclean(fpgname, reclaimStrategy='maxspeed')
        self.assertIn(result, expected_in)
        result = self.cl.startfsnapclean(fpgname, reclaimStrategy='maxspeed')
        self.assertIn(result, expected_in)

        result = self.cl.getfsnapclean(fpgname)
        self.debug_print('GETFSNAPCLEAN:')
        self.debug_print(result)
        self.assertIsNone(result['message'])
        self.assertLess(0, result['total'])
        for member in result['members']:
            self.assertTrue(member['avgFileSizeKb'].isdigit())
            self.assertTrue(member['endTime'].isdigit())
            self.assertIn(member['exitStatus'], ['OK', 'N/A'])
            self.assertIn(member['logLevel'], ['INFO', 'N/A'])
            self.assertTrue(member['numDentriesReclaimed'].isdigit())
            self.assertTrue(member['numDentriesScanned'].isdigit())
            self.assertTrue(member['numErrors'].isdigit())
            self.assertTrue(member['numInodesSkipped'].isdigit())
            self.assertTrue(member['spaceRecoveredCumulative'].isdigit())
            self.assertTrue(member['startTime'].isdigit())
            self.assertIn(member['strategy'].upper(), ('MAXSPACE', 'MAXSPEED'))
            uid_match = '^[0-f]*$'
            self.assertIsNotNone(re.match(uid_match, member['taskId']))
            self.assertIn(member['taskState'],
                          ('RUNNING', 'COMPLETED', 'STOPPED', 'UNKNOWN'))
            self.assertIn(member['verboseMode'], ['false', 'NA'])

        result = self.cl.stopfsnapclean(fpgname)
        self.assertEqual([], result)

        result = self.cl.startfsnapclean(fpgname, resume=True)
        self.assertEqual(['No reclamation task running on FPG %s\r' % fpgname],
                         result)

    def remove_fstore(self, fpgname, vfsname, fstore):
        self.cl.removefsnap(vfsname, fstore, fpg=fpgname)
        result = self.cl.startfsnapclean(fpgname, reclaimStrategy='maxspeed')
        success = []
        running = ['Reclamation already running on %s\r' % fpgname]
        expected_in = (success, running)
        self.assertIn(result, expected_in)

        result = self.cl.removefstore(vfsname, fstore, fpg=fpgname)
        self.assertEqual(['%s removed' % fstore], result)

    def remove_share(self, protocol, fpgname, vfsname, share_name):
        result = self.cl.removefshare(protocol, vfsname, share_name,
                                      fpg=fpgname, fstore=share_name)
        self.assertEqual([], result)
        result = self.cl.removefshare(protocol, vfsname, share_name,
                                      fpg=fpgname, fstore=share_name)
        if protocol == 'nfs':
            expected = ['%s Delete Export failed with error: '
                        'share %s does not exist\r' %
                        (protocol.upper(), share_name)]
            self.assertEqual(expected, result)
        else:
            expected_prefix = 'Failure on Delete Share: %s:' % share_name
            len_prefix = len(expected_prefix)
            self.assertEqual(expected_prefix, result[0][0:len_prefix])

        # Remove with bogus filestore
        result = self.cl.removefshare(protocol, vfsname, share_name,
                                      fpg=fpgname, fstore='bogus')
        if protocol == 'nfs':
            expected = [
                '%s Delete Export failed with error: '
                'File Store bogus was not found\r' % protocol.upper()]
        else:
            expected = ['Could not find Store=bogus\r']
        self.assertEqual(expected, result)

    @unittest.skipIf(skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_create_and_remove_shares(self):

        test_prefix = 'UT5_'
        fpgname = config['TEST'].get('fpg', None)
        if fpgname is None:
            fpgname = self.get_or_create_fpg(test_prefix)

        # Create VFS
        vfsname = self.get_or_create_vfs(test_prefix, fpgname)

        # Try creating it again
        result = self.cl.createvfs('127.0.0.2', '255.255.255.0', vfsname,
                                   fpg=fpgname,
                                   wait=True)
        expected = ('VFS "%s" already exists within FPG %s\r' %
                    (vfsname, fpgname))
        self.assertEqual(expected, result[0])
        self.validate_vfs(vfsname=vfsname, fpgname=fpgname,
                          expected_count=1)

        # Get the VFS and validate the original settings.
        result = self.cl.getvfs(fpg=fpgname, vfs=vfsname)
        self.assertIn('bgrace', result['members'][0])
        self.assertIn('igrace', result['members'][0])
        self.assertIn('comment', result['members'][0])

        # Test FSIPS while we have a VFS
        # (unfortunately FSIPS might not be ready yet)
        if result['members'][0]['overallStateInt'] == '1':
            self.get_fsips(fpgname, vfsname)

        # CRUD test fstore using this VFS
        fstore = test_prefix + "CRUD_FSTORE_" + hpe3parbase.TIME
        self.crud_fstore(fpgname, vfsname, fstore)

        # NFS SHARES and FSTORE
        protocol = 'nfs'
        share_name = "UT_test_share_%s" % protocol
        comment = 'OpenStack Manila fshare %s' % share_name
        self.create_share(protocol, fpgname, vfsname, share_name, comment)

        result = self.cl.getfshare(protocol, share_name,
                                   fpg=fpgname, vfs=vfsname,
                                   fstore=share_name)
        self.debug_print(result)
        self.assertEqual(None, result['message'])
        self.assertEqual(1, result['total'])

        member = result['members'][0]
        self.assertEqual(share_name, member['fstoreName'])
        self.assertEqual(fpgname, member['fspName'])
        self.assertEqual(comment, member['comment'])
        self.assertIsInstance(int(member['overallStateInt']), int)
        self.assertIsInstance(member['options'], list)
        self.assertEqual('*', member['clients'])
        self.assertTrue(member['CompId'].isdigit())

        self.remove_share(protocol, fpgname, vfsname, share_name)

        # SMB SHARES and FSTORE
        protocol = 'smb'
        share_name = "UT_test_share_%s" % protocol
        fstore = share_name
        comment = 'OpenStack Manila fshare %s' % share_name
        self.create_share(protocol, fpgname, vfsname, share_name, comment)

        result = self.cl.getfshare(protocol, share_name,
                                   fpg=fpgname, vfs=vfsname,
                                   fstore=share_name)
        self.debug_print(result)
        self.assertEqual(None, result['message'])
        self.assertEqual(1, result['total'])

        member = result['members'][0]
        self.assertEqual(fstore, member['fstoreName'])
        self.assertEqual(fpgname, member['fspName'])
        self.assertEqual(vfsname, member['vfsName'])
        self.assertEqual(comment, member['comment'])
        self.assertIsInstance(int(member['overallStateInt']), int)
        self.assertTrue(member['CompId'].isdigit())
        self.assertEqual('false', member['abe'])
        self.assertIsInstance(member['allowIP'], list)
        self.assertIsInstance(member['denyIP'], list)
        self.assertEqual([], member['allowPerm'])
        self.assertEqual([], member['denyPerm'])
        self.assertEqual('true', member['ca'])
        self.assertEqual('manual', member['cache'])
        self.assertEqual([], member['shareDir'])
        self.assertEqual(share_name, member['shareName'])
        self.assertEqual('---', member['uuid'])

        # SNAPSHOTS (need a share to use)

        # test creates and cleans
        tag = test_prefix + "TAG_" + hpe3parbase.TIME
        self.create_fsnap(fpgname, vfsname, fstore, tag)

        # SHARE REMOVAL -- includes tests/asserts
        self.remove_share(protocol, fpgname, vfsname, share_name)

        # FSTORE REMOVAL -- includes tests/asserts and fsnap remove/clean
        self.remove_fstore(fpgname, vfsname, fstore)

    @unittest.skipIf(is_live_test() and skip_file_persona(), SKIP_MSG)
    @print_header_and_footer
    def test_removevfs_bogus(self):
        self.assertRaises(AttributeError, self.cl.removevfs, None)
        result = self.cl.removevfs('bogus')
        vfs_not_found = ('Virtual file server bogus was not found in any '
                         'existing file provisioning group.\r')
        self.assertEqual(vfs_not_found, result[0])
        self.assertRaises(AttributeError, self.cl.removevfs, None, fpg='bogus')

        result = self.cl.removevfs('bogus', fpg='bogus')
        fpg_not_found = 'File Provisioning Group: bogus not found\r'
        self.assertEqual(fpg_not_found, result[0])

# testing
# suite = unittest.TestLoader().
#     loadTestsFromTestCase(HPE3ParFilePersonaClientTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
