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

import mock
import paramiko
import unittest

from test import HPE3ParClient_base
from hpe3parclient import exceptions
from hpe3parclient import ssh

# Python 3+ override
try:
    basestring
except NameError:
    basestring = str

user = "u"
password = "p"
ip = "10.10.22.241"
api_url = "http://10.10.22.241:8008/api/v1"


class HPE3ParClientMockSSHTestCase(HPE3ParClient_base
                                   .HPE3ParClientBaseTestCase):

    def mock_paramiko(self, known_hosts_file, missing_key_policy):
        """Verify that these params get into paramiko."""

        mock_lhk = mock.Mock()
        mock_lshk = mock.Mock()
        mock_smhkp = mock.Mock()
        mock_smhkp.side_effect = Exception("Let's end this here")

        with mock.patch('paramiko.client.SSHClient.load_system_host_keys',
                        mock_lshk, create=True):
            with mock.patch('paramiko.client.SSHClient.load_host_keys',
                            mock_lhk, create=True):
                with mock.patch('paramiko.client.SSHClient.'
                                'set_missing_host_key_policy',
                                mock_smhkp, create=True):
                    try:
                        self.cl.setSSHOptions(
                            ip, user, password,
                            known_hosts_file=known_hosts_file,
                            missing_key_policy=missing_key_policy)
                    except paramiko.SSHException as e:
                        if 'Invalid missing_key_policy' in str(e):
                            raise e
                    except Exception:
                        pass

                    if known_hosts_file is None:
                        mock_lhk.assert_not_called()
                        mock_lshk.assert_called_with()
                    else:
                        mock_lhk.assert_called_with(known_hosts_file)
                        mock_lshk.assert_not_called()

                    actual = mock_smhkp.call_args[0][0].__class__.__name__
                    if missing_key_policy is None:
                        # If missing, it should be called with our
                        # default which is an AutoAddPolicy
                        expected = paramiko.AutoAddPolicy().__class__.__name__
                    elif isinstance(missing_key_policy, basestring):
                        expected = missing_key_policy
                    else:
                        expected = missing_key_policy.__class__.__name__
                    self.assertEqual(actual, expected)

    def do_mock_create_ssh(self, known_hosts_file, missing_key_policy):
        """Verify that params are getting forwarded to _create_ssh()."""

        mock_ssh = mock.Mock()
        with mock.patch('hpe3parclient.ssh.HPE3PARSSHClient._create_ssh',
                        mock_ssh, create=True):

            self.cl.setSSHOptions(ip, user, password,
                                  known_hosts_file=known_hosts_file,
                                  missing_key_policy=missing_key_policy)

            mock_ssh.assert_called_with(missing_key_policy=missing_key_policy,
                                        known_hosts_file=known_hosts_file)

        # Create a mocked ssh object for the client so that it can be
        # "closed" during a logout.
        self.cl.ssh = mock.MagicMock()

    @mock.patch('hpe3parclient.ssh.HPE3PARSSHClient')
    def do_mock_ssh(self, known_hosts_file, missing_key_policy,
                    mock_ssh_client):
        """Verify that params are getting forwarded to HPE3PARSSHClient."""

        self.cl.setSSHOptions(ip, user, password,
                              known_hosts_file=known_hosts_file,
                              missing_key_policy=missing_key_policy)

        mock_ssh_client.assert_called_with(
            ip, user, password, 22, None, None,
            missing_key_policy=missing_key_policy,
            known_hosts_file=known_hosts_file)

    def base(self, known_hosts_file, missing_key_policy):
        self.printHeader("%s : known_hosts_file=%s missing_key_policy=%s" %
                         (unittest.TestCase.id(self),
                          known_hosts_file, missing_key_policy))
        self.do_mock_ssh(known_hosts_file, missing_key_policy)
        self.do_mock_create_ssh(known_hosts_file, missing_key_policy)
        self.mock_paramiko(known_hosts_file, missing_key_policy)
        self.printFooter(unittest.TestCase.id(self))

    def test_auto_add_policy(self):
        known_hosts_file = "test_bogus_known_hosts_file"
        missing_key_policy = "AutoAddPolicy"
        self.base(known_hosts_file, missing_key_policy)

    def test_warning_policy(self):
        known_hosts_file = "test_bogus_known_hosts_file"
        missing_key_policy = "WarningPolicy"
        self.base(known_hosts_file, missing_key_policy)

    def test_reject_policy(self):
        known_hosts_file = "test_bogus_known_hosts_file"
        missing_key_policy = "RejectPolicy"
        self.base(known_hosts_file, missing_key_policy)

    def test_known_hosts_file_is_none(self):
        known_hosts_file = None
        missing_key_policy = paramiko.RejectPolicy()
        self.base(known_hosts_file, missing_key_policy)

    def test_both_settings_are_none(self):
        known_hosts_file = None
        missing_key_policy = None
        self.base(known_hosts_file, missing_key_policy)

    def test_bogus_missing_key_policy(self):
        known_hosts_file = None
        missing_key_policy = "bogus"
        self.assertRaises(paramiko.SSHException,
                          self.base,
                          known_hosts_file,
                          missing_key_policy)

    def test_create_ssh_except(self):
        """Make sure that SSH exceptions are not quietly eaten."""

        self.cl.setSSHOptions(ip,
                              user,
                              password,
                              known_hosts_file=None,
                              missing_key_policy=paramiko.AutoAddPolicy)

        self.cl.ssh.ssh = mock.Mock()
        self.cl.ssh.ssh.invoke_shell.side_effect = Exception('boom')

        cmd = ['fake']
        self.assertRaises(exceptions.SSHException, self.cl.ssh._run_ssh, cmd)

        self.cl.ssh.ssh.assert_has_calls(
            [
                mock.call.get_transport(),
                mock.call.get_transport().is_alive(),
                mock.call.invoke_shell(),
                mock.call.get_transport(),
                mock.call.get_transport().is_alive(),
            ]
        )

    def test_sanitize_cert(self):
        # no begin cert
        input = 'foo -END CERTIFICATE- no begin'
        expected = input
        out = ssh.HPE3PARSSHClient.sanitize_cert(input)
        self.assertEqual(expected, out)
        # pre, begin, middle, end, post
        input = 'head -BEGIN CERTIFICATE-1234-END CERTIFICATE- tail'
        expected = 'head -BEGIN CERTIFICATE-sanitized-END CERTIFICATE- tail'
        out = ssh.HPE3PARSSHClient.sanitize_cert(input)
        self.assertEqual(expected, out)
        # end before begin
        input = 'head -END CERTIFICATE-1234-BEGIN CERTIFICATE- tail'
        expected = 'head -END CERTIFICATE-1234-BEGIN CERTIFICATE-sanitized'
        out = ssh.HPE3PARSSHClient.sanitize_cert(input)
        self.assertEqual(expected, out)
        # no end
        input = 'head -BEGIN CERTIFICATE-1234-END CEXXXXXXXTE- tail'
        expected = 'head -BEGIN CERTIFICATE-sanitized'
        out = ssh.HPE3PARSSHClient.sanitize_cert(input)
        self.assertEqual(expected, out)
        # test with a list
        input = ['head -BEGIN CERTIFICATE-----1234',
                 'ss09f87sdf987sf97sfsds0f7sf97s89',
                 '6789-----END CERTIFICATE- tail']
        expected = 'head -BEGIN CERTIFICATE-sanitized-END CERTIFICATE- tail'
        out = ssh.HPE3PARSSHClient.sanitize_cert(input)
        self.assertEqual(expected, out)

    def test_strip_input_from_output(self):
        cmd = ['foo', '-v']
        # nothing after exit
        output = ['exit']
        self.assertRaises(exceptions.SSHException,
                          ssh.HPE3PARSSHClient.strip_input_from_output,
                          cmd,
                          output)
        # no exit
        output = ['line1', 'line2', 'line3']
        self.assertRaises(exceptions.SSHException,
                          ssh.HPE3PARSSHClient.strip_input_from_output,
                          cmd,
                          output)
        # no setclienv csv
        output = [cmd, 'exit', 'out']
        self.assertRaises(exceptions.SSHException,
                          ssh.HPE3PARSSHClient.strip_input_from_output,
                          cmd,
                          output)
        # command not in output after exit
        output = [cmd, 'exit', 'PROMPT% setclienv csvtable 1']
        self.assertRaises(exceptions.SSHException,
                          ssh.HPE3PARSSHClient.strip_input_from_output,
                          cmd,
                          output)
        # success
        output = [cmd,
                  'setclienv csvtable 1',
                  'exit',
                  'PROMPT% setclienv csvtable 1',
                  'PROMPT% foo -v',
                  'out1',
                  'out2',
                  'out3',
                  '------',
                  'totals']
        result = ssh.HPE3PARSSHClient.strip_input_from_output(cmd, output)
        self.assertEqual(['out1', 'out2', 'out3'], result)
