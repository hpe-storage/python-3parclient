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

"""Test base class of 3PAR Client."""

import os
import sys
import unittest
import subprocess
import time
import inspect
from testconfig import config
import datetime
from functools import wraps
from hpe3parclient import client, file_client

TIME = datetime.datetime.now().strftime('%H%M%S')

try:
    # For Python 3.0 and later
    from urllib.parse import urlparse
except ImportError:
    # Fall back to Python 2's urllib2
    from urlparse import urlparse


class HPE3ParClientBaseTestCase(unittest.TestCase):

    user = config['TEST']['user']
    password = config['TEST']['pass']
    flask_url = config['TEST']['flask_url']
    url_3par = config['TEST']['3par_url']
    debug = config['TEST']['debug'].lower() == 'true'
    unitTest = config['TEST']['unit'].lower() == 'true'
    port = None

    remote_copy = config['TEST']['run_remote_copy'].lower() == 'true'
    run_remote_copy = remote_copy and not unitTest
    if run_remote_copy:
        secondary_user = config['TEST_REMOTE_COPY']['user']
        secondary_password = config['TEST_REMOTE_COPY']['pass']
        secondary_url_3par = config['TEST_REMOTE_COPY']['3par_url']
        secondary_target_name = config['TEST_REMOTE_COPY']['target_name']

    ssh_port = None
    if 'ssh_port' in config['TEST']:
        ssh_port = int(config['TEST']['ssh_port'])
    elif unitTest:
        ssh_port = 2200
    else:
        ssh_port = 22

    # Don't setup SSH unless needed.  It slows things down.
    withSSH = False

    if 'domain' in config['TEST']:
        DOMAIN = config['TEST']['domain']
    else:
        DOMAIN = 'UNIT_TEST_DOMAIN'

    if 'cpg_ldlayout_ha' in config['TEST']:
        CPG_LDLAYOUT_HA = int(config['TEST']['cpg_ldlayout_ha'])
        CPG_OPTIONS = {'domain': DOMAIN, 'LDLayout': {'HA': CPG_LDLAYOUT_HA}}
    else:
        CPG_LDLAYOUT_HA = None
        CPG_OPTIONS = {'domain': DOMAIN}

    if 'known_hosts_file' in config['TEST']:
        known_hosts_file = config['TEST']['known_hosts_file']
    else:
        known_hosts_file = None

    if 'missing_key_policy' in config['TEST']:
        missing_key_policy = config['TEST']['missing_key_policy']
    else:
        missing_key_policy = None

    def setUp(self, withSSH=False, withFilePersona=False):

        self.withSSH = withSSH
        self.withFilePersona = withFilePersona

        cwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        if self.unitTest:
            self.printHeader('Using flask ' + self.flask_url)
            parsed_url = urlparse(self.flask_url)
            userArg = '-user=%s' % self.user
            passwordArg = '-password=%s' % self.password
            portArg = '-port=%s' % parsed_url.port

            script = 'HPE3ParMockServer_flask.py'
            path = "%s/%s" % (cwd, script)
            try:
                self.mockServer = subprocess.Popen([sys.executable,
                                                    path,
                                                    userArg,
                                                    passwordArg,
                                                    portArg],
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE,
                                                   stdin=subprocess.PIPE
                                                   )
            except Exception:
                pass

            time.sleep(1)
            if self.withFilePersona:
                self.cl = file_client.HPE3ParFilePersonaClient(self.flask_url)
            else:
                self.cl = client.HPE3ParClient(self.flask_url)

            if self.withSSH:

                self.printHeader('Using paramiko SSH server on port %s' %
                                 self.ssh_port)

                ssh_script = 'HPE3ParMockServer_ssh.py'
                ssh_path = "%s/%s" % (cwd, ssh_script)

                self.mockSshServer = subprocess.Popen([sys.executable,
                                                       ssh_path,
                                                       str(self.ssh_port)],
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.PIPE,
                                                      stdin=subprocess.PIPE)
                time.sleep(1)

        else:
            if withFilePersona:
                self.printHeader('Using 3PAR %s with File Persona' %
                                 self.url_3par)
                self.cl = file_client.HPE3ParFilePersonaClient(self.url_3par)
            else:
                self.printHeader('Using 3PAR ' + self.url_3par)
                self.cl = client.HPE3ParClient(self.url_3par)

        if self.withSSH:
            # This seems to slow down the test cases, so only use this when
            # requested
            if self.unitTest:
                # The mock SSH server can be accessed at 0.0.0.0.
                ip = '0.0.0.0'
            else:
                parsed_3par_url = urlparse(self.url_3par)
                ip = parsed_3par_url.hostname.split(':').pop()
            try:
                # Now that we don't do keep-alive, the conn_timeout needs to
                # be set high enough to avoid sometimes slow response in
                # the File Persona tests.
                self.cl.setSSHOptions(
                    ip,
                    self.user,
                    self.password,
                    port=self.ssh_port,
                    conn_timeout=500,
                    known_hosts_file=self.known_hosts_file,
                    missing_key_policy=self.missing_key_policy)
            except Exception as ex:
                print(ex)
                self.fail("failed to start ssh client")

        # Setup remote copy target
        if self.run_remote_copy:
            parsed_3par_url = urlparse(self.secondary_url_3par)
            ip = parsed_3par_url.hostname.split(':').pop()
            self.secondary_cl = client.HPE3ParClient(self.secondary_url_3par)
            try:
                self.secondary_cl.setSSHOptions(
                    ip,
                    self.secondary_user,
                    self.secondary_password,
                    port=self.ssh_port,
                    conn_timeout=500,
                    known_hosts_file=self.known_hosts_file,
                    missing_key_policy=self.missing_key_policy)
            except Exception as ex:
                print(ex)
                self.fail("failed to start ssh client")
            self.secondary_cl.login(self.secondary_user,
                                    self.secondary_password)

        if self.debug:
            self.cl.debug_rest(True)

        self.cl.login(self.user, self.password)

        if not self.port:
            ports = self.cl.getPorts()
            ports = [p for p in ports['members']
                     if p['linkState'] == 4 and  # Ready
                     ('device' not in p or not p['device']) and
                     p['mode'] == self.cl.PORT_MODE_TARGET]
            self.port = ports[0]['portPos']

    def tearDown(self):
        self.cl.logout()
        if self.run_remote_copy:
            self.secondary_cl.logout()
        if self.unitTest:
            self.mockServer.kill()
            if self.withSSH:
                self.mockSshServer.kill()

    def print_header_and_footer(func):
        """Decorator to print header and footer for unit tests."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            test = args[0]
            test.printHeader(unittest.TestCase.id(test))
            result = func(*args, **kwargs)
            test.printFooter(unittest.TestCase.id(test))
            return result
        return wrapper

    def printHeader(self, name):
        print("\n##Start testing '%s'" % name)

    def printFooter(self, name):
        print("##Completed testing '%s\n" % name)

    def findInDict(self, dic, key, value):
        for i in dic:
            if key in i and i[key] == value:
                return True
