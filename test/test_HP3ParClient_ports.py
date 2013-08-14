
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

"""Test class of 3Par Client handling Ports"""
import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

class HP3ParClientPortTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientPortTestCase, self).setUp()

    def tearDown(self):
        pass

    def test_get_ports_all(self):
        self.printHeader('get_ports_all')
        ports = self.cl.getPorts()
        if ports:
            if len(ports['members']) == ports['total']:
                self.printFooter('get_ports_all')
                return
            else:
                self.fail('Number of ports in invalid.')
        else:
            self.fail('Cannot retrieve ports.')

    def test_get_ports_fc(self):
        self.printHeader('get_ports_fc')
        fc_ports = self.cl.getFCPorts(4)
        print fc_ports
        if fc_ports:
            for port in fc_ports:
                if port['protocol'] != 1:
                    self.fail('Non-FC ports detected.')
            self.printFooter('get_ports_fc')
            return
        else:
            self.fail('Cannot retrieve FC ports.')

    def test_get_ports_iscsi(self):
        self.printHeader('get_ports_iscsi')
        iscsi = self.cl.getiSCSIPorts(4)
        if iscsi:
            for port in iscsi:
                if port['protocol'] != 2:
                    self.fail('Non-iSCSI ports detected.')
            self.printFooter('get_ports_iscsi')
            return
        else:
            self.fail('Cannot retrieve iSCSI Ports.')