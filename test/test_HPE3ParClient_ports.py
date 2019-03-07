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

"""Test class of 3PAR Client handling Ports."""

from test import HPE3ParClient_base as hpe3parbase

iscsi_ports = [{
    'IPAddr': '192.168.1.1',
    'portPos': {
        'node': 0,
        'slot': 2,
        'cardPort': 1
    },
    'iSCSIPortInfo': {
        'iSNSAddr': '0.0.0.0',
        'vlan': '100',
        'IPAddr': '192.168.1.1',
        'mtu': 1500,
        'stgt': 21,
        'netmask': '255.255.192.0',
        'tpgt': 1024,
        'iSNSPort': 3205,
        'gateway': '0.0.0.0'
    }
}]

body = {
    u'total': 14,
    u'members': [{
        u'portPos': {
            u'node': 0,
            u'slot': 2,
            u'cardPort': 1
        },
        u'protocol': 2,
        u'iSCSIPortInfo': {
            u'iSNSAddr': u'0.0.0.0',
            u'vlan': 1,
            u'IPAddr': u'0.0.0.0',
            u'rate': u'10Gbps',
            u'mtu': 1500,
            u'stgt': 21,
            u'netmask': u'0.0.0.0',
            u'iSCSIName': u'iqn.2000-05.com.3pardata:20210002ac01db31',
            u'tpgt': 21,
            u'iSNSPort': 3205,
            u'gateway': u'0.0.0.0'
        },
        u'partnerPos': {
            u'node': 1,
            u'slot': 2,
            u'cardPort': 1
        },
        u'IPAddr': u'0.0.0.0',
        u'linkState': 4,
        u'device': [

        ],
        u'iSCSIName': u'iqn.2000-05.com.3pardata:20210002ac01db31',
        u'failoverState': 1,
        u'mode': 2,
        u'HWAddr': u'70106FCE921A',
        u'type': 8,
        u'iSCSIVlans': [
            {
                u'iSNSAddr': u'0.0.0.0',
                u'IPAddr': u'192.168.1.1',
                u'mtu': 1500,
                u'stgt': 21,
                u'netmask': u'255.255.192.0',
                u'tpgt': 1024,
                u'iSNSPort': 3205,
                u'gateway': u'0.0.0.0',
                u'vlanTag': 100
            }
        ]
    }]
}

user = "u"
password = "p"
ip = "10.10.22.241"


class HPE3ParClientPortTestCase(hpe3parbase.HPE3ParClientBaseTestCase):

    def setUp(self):
        super(HPE3ParClientPortTestCase, self).setUp()

    def tearDown(self):
        super(HPE3ParClientPortTestCase, self).tearDown()

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

    def test_cloned_iscsi_ports(self):
        self.printHeader('get_vlan_tagged_iscsi_port_info')
        iscsi_port = self.cl._cloneISCSIPorts(body, iscsi_ports)
        if iscsi_port:
            if iscsi_port[0]['iSCSIPortInfo']['IPAddr'] ==\
                    iscsi_ports[0]['IPAddr']:
                self.printFooter('get_vlan_tagged_iscsi_port_info')
                return
            else:
                self.fail('iSCSIVlan IPAddr is not found')
        else:
            self.fail('Cannot retrieve ports')

    def test_get_ports_ssh(self):
        self.printHeader('get_ports_cli')
        self.cl.setSSHOptions(ip,
                              user,
                              password)
        ports = self.cl.getPorts()
        if ports:
            if len(ports['members']) == ports['total']:
                self.printFooter('get_ports_cli')
                return
            else:
                self.fail('Number of ports is invalid.')
        else:
            self.fail('Cannot retrieve ports.')

    def test_get_ports_fc(self):
        self.printHeader('get_ports_fc')
        fc_ports = self.cl.getFCPorts(4)
        print(fc_ports)
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

    def test_get_ports_ip(self):
        self.printHeader('get_ports_ip')

        ip = self.cl.getIPPorts()
        if ip:
            for port in ip:
                if port['protocol'] != 4:
                    self.fail('non-ip ports detected.')
            self.printFooter('get_ports_ip')
        else:
            self.fail('cannot retrieve ip ports.')
