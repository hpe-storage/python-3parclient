# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2009-2012 10gen, Inc.
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

"""Test base class of 3Par Client."""

import os
import sys
sys.path.insert(0, os.path.realpath(os.path.abspath('../')))

from hp3parclient import client
import unittest
import subprocess
import time
import inspect
from testconfig import config
try:
    # For Python 3.0 and later
    from urllib.parse import urlparse
except ImportError:
    # Fall back to Python 2's urllib2
    from urlparse import urlparse

# pip install nose-testconfig

# e.g.
# nosetests test_HP3ParClient_host.py -v --tc-file config.ini


class HP3ParClientBaseTestCase(unittest.TestCase):

    user = config['TEST']['user']
    password = config['TEST']['pass']
    flask_url = config['TEST']['flask_url']
    url_3par = config['TEST']['3par_url']
    debug = config['TEST']['debug'].lower() == 'true'
    unitTest = config['TEST']['unit'].lower() == 'true'

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

    def setUp(self, withSSH=False):

        cwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        if self.unitTest:
            self.printHeader('Using flask ' + self.flask_url)
            parsed_url = urlparse(self.flask_url)
            userArg = '-user=%s' % self.user
            passwordArg = '-password=%s' % self.password
            portArg = '-port=%s' % parsed_url.port

            script = 'HP3ParMockServer_flask.py'
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
            self.cl = client.HP3ParClient(self.flask_url)
            # SSH is not supported in flask, so not initializing
            # those tests are expected to fail
        else:
            self.printHeader('Using 3PAR ' + self.url_3par)
            self.cl = client.HP3ParClient(self.url_3par)
            if withSSH:
                # This seems to slow down the test cases, so only use this when
                # requested
                parsed_3par_url = urlparse(self.url_3par)
                ip = parsed_3par_url.hostname.split(':').pop()
                try:
                    # Set the conn_timeout to None so that the ssh connections
                    # will use the default transport values which will allow
                    # the test case process to terminate after completing
                    self.cl.setSSHOptions(ip, self.user, self.password,
                                          conn_timeout=None)
                except Exception as ex:
                    print ex
                    self.fail("failed to start ssh client")

        if self.debug:
            self.cl.debug_rest(True)

        self.cl.login(self.user, self.password)

    def tearDown(self):
        self.cl.logout()
        if self.unitTest:
            self.mockServer.kill()

    def printHeader(self, name):
        print("\n##Start testing '%s'" % name)

    def printFooter(self, name):
        print("##Completed testing '%s\n" % name)

    def findInDict(self, dic, key, value):
        for i in dic:
            if key in i and i[key] == value:
                return True
