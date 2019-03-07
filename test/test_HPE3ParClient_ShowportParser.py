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

"""Test class of 3PAR Client handling parsing of showport commands."""

from test import HPE3ParClient_base as hp3parbase
# from hpe3parclient import client
# from hpe3parclient.client import ShowportParser
from hpe3parclient import showport_parser


class HP3ParClientShowportTestCase(hp3parbase.HPE3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientShowportTestCase, self).setUp()

    def tearDown(self):
        super(HP3ParClientShowportTestCase, self).tearDown()

    def test_parse_showport_iscsivlans(self):

        parsed_ports = showport_parser.\
            ShowportParser().parseShowport(ports_iscsivlan)

        if parsed_ports != parsed_ports_key:
            err_msg = 'parsed ports does not match key output: {}'
            return self.fail(err_msg.format(parsed_ports))

        return

    def test_parse_showport_empty(self):
        ports = \
            ['N:S:P,VLAN,IPAddr,Netmask/PrefixLen,Gateway,'
             'MTU,TPGT,STGT,iSNS_Addr,iSNS_Port',
             '-----------------------------------------'
             '----------------------------------------------',
             '0,,,,,,,,,']

        parsed_ports = showport_parser.ShowportParser().parseShowport(ports)

        if len(parsed_ports) != 0:
            err_msg = 'Parsed ports should be empty but contains data: {}'
            return self.fail(err_msg.format(parsed_ports))

        return

    def test_clone_ports(self):
        parsed_ports = showport_parser.\
            ShowportParser().parseShowport(ports_iscsivlan)

        expanded_ports = self.cl._cloneISCSIPorts(real_ports, parsed_ports)

        if expanded_ports != expanded_ports_key:
            err_msg = 'combined ports output does not match test key: {}'
            return self.fail(err_msg.format(expanded_ports))

        return

    global ports_iscsivlan
    ports_iscsivlan = \
        ['N:S:P,VLAN,IPAddr,Netmask/PrefixLen,Gateway,MTU,'
         'TPGT,STGT,iSNS_Addr,iSNS_Port',
         '0:2:1,101,172.20.0.150,255.255.255.0,'
         '172.20.0.1,9000,1024,1024,0.0.0.0,3205',
         '0:2:2,102,172.20.1.150,255.255.255.0,'
         '172.20.1.1,9000,1025,1025,0.0.0.0,3205',
         '1:2:1,101,172.20.0.151,255.255.255.0,'
         '172.20.0.1,9000,1026,1026,0.0.0.0,3205',
         '1:2:2,102,172.20.1.151,255.255.255.0,'
         '172.20.1.1,9000,1027,1027,0.0.0.0,3205',
         '---------------------------------------'
         '------------------------------------------------',
         '4,,,,,,,,,']

    global real_ports
    real_ports = {
        u'total': 14,
        u'members': [
            {
                u'portWWN': u'20010002AC01C533',
                u'protocol': 1,
                u'partnerPos': {
                    u'node': 1,
                    u'slot': 0,
                    u'cardPort': 1
                },
                u'linkState': 5,
                u'failoverState': 1,
                u'mode': 2,
                u'device': [
                ],
                u'nodeWWN': u'2FF70002AC01C533',
                u'type': 3,
                u'portPos': {
                    u'node': 0,
                    u'slot': 0,
                    u'cardPort': 1
                }
            },
            {
                u'portWWN': u'20020002AC01C533',
                u'protocol': 1,
                u'partnerPos': {
                    u'node': 1,
                    u'slot': 0,
                    u'cardPort': 2
                },
                u'linkState': 5,
                u'failoverState': 1,
                u'mode': 2,
                u'device': [
                ],
                u'nodeWWN': u'2FF70002AC01C533',
                u'type': 3,
                u'portPos': {
                    u'node': 0,
                    u'slot': 0,
                    u'cardPort': 2
                }
            },
            {
                u'portWWN': u'50002AC01101C533',
                u'protocol': 5,
                u'linkState': 4,
                u'label': u'DP-1',
                u'mode': 3,
                u'device': [
                    u'cage0',
                    u'cage1',
                    u'cage2'
                ],
                u'nodeWWN': u'50002ACFF701C533',
                u'type': 2,
                u'portPos': {
                    u'node': 0,
                    u'slot': 1,
                    u'cardPort': 1
                }
            },
            {
                u'portWWN': u'50002AC01201C533',
                u'protocol': 5,
                u'linkState': 4,
                u'label': u'DP-2',
                u'mode': 3,
                u'device': [
                    u'cage3',
                    u'cage4',
                    u'cage5'
                ],
                u'nodeWWN': u'50002ACFF701C533',
                u'type': 2,
                u'portPos': {
                    u'node': 0,
                    u'slot': 1,
                    u'cardPort': 2
                }
            },
            {
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
                    u'mtu': 9000,
                    u'stgt': 21,
                    u'netmask': u'0.0.0.0',
                    u'iSCSIName': u'iqn.2000-05.com.3pardata:20210002ac01c533',
                    u'tpgt': 21,
                    u'iSNSPort': 3205,
                    u'gateway': u'172.20.0.1'
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
                u'iSCSIName': u'iqn.2000-05.com.3pardata:20210002ac01c533',
                u'failoverState': 1,
                u'mode': 2,
                u'HWAddr': u'1402EC613AFA',
                u'type': 8
            },
            {
                u'portPos': {
                    u'node': 0,
                    u'slot': 2,
                    u'cardPort': 2
                },
                u'protocol': 2,
                u'iSCSIPortInfo': {
                    u'iSNSAddr': u'0.0.0.0',
                    u'vlan': 1,
                    u'IPAddr': u'0.0.0.0',
                    u'rate': u'10Gbps',
                    u'mtu': 1500,
                    u'stgt': 22,
                    u'netmask': u'0.0.0.0',
                    u'iSCSIName': u'iqn.2000-05.com.3pardata:20220002ac01c533',
                    u'tpgt': 22,
                    u'iSNSPort': 3205,
                    u'gateway': u'0.0.0.0'
                },
                u'partnerPos': {
                    u'node': 1,
                    u'slot': 2,
                    u'cardPort': 2
                },
                u'IPAddr': u'0.0.0.0',
                u'linkState': 4,
                u'device': [

                ],
                u'iSCSIName': u'iqn.2000-05.com.3pardata:20220002ac01c533',
                u'failoverState': 1,
                u'mode': 2,
                u'HWAddr': u'1402EC613AF2',
                u'type': 8
            },
            {
                u'portPos': {
                    u'node': 0,
                    u'slot': 3,
                    u'cardPort': 1
                },
                u'protocol': 4,
                u'linkState': 10,
                u'label': u'IP0',
                u'device': [

                ],
                u'mode': 4,
                u'HWAddr': u'941882447BDD',
                u'type': 3
            },
            {
                u'portWWN': u'21010002AC01C533',
                u'protocol': 1,
                u'partnerPos': {
                    u'node': 0,
                    u'slot': 0,
                    u'cardPort': 1
                },
                u'linkState': 5,
                u'failoverState': 1,
                u'mode': 2,
                u'device': [

                ],
                u'nodeWWN': u'2FF70002AC01C533',
                u'type': 3,
                u'portPos': {
                    u'node': 1,
                    u'slot': 0,
                    u'cardPort': 1
                }
            },
            {
                u'portWWN': u'21020002AC01C533',
                u'protocol': 1,
                u'partnerPos': {
                    u'node': 0,
                    u'slot': 0,
                    u'cardPort': 2
                },
                u'linkState': 5,
                u'failoverState': 1,
                u'mode': 2,
                u'device': [

                ],
                u'nodeWWN': u'2FF70002AC01C533',
                u'type': 3,
                u'portPos': {
                    u'node': 1,
                    u'slot': 0,
                    u'cardPort': 2
                }
            },
            {
                u'portWWN': u'50002AC11101C533',
                u'protocol': 5,
                u'linkState': 4,
                u'label': u'DP-1',
                u'mode': 3,
                u'device': [
                    u'cage0',
                    u'cage1',
                    u'cage2'
                ],
                u'nodeWWN': u'50002ACFF701C533',
                u'type': 2,
                u'portPos': {
                    u'node': 1,
                    u'slot': 1,
                    u'cardPort': 1
                }
            },
            {
                u'portWWN': u'50002AC11201C533',
                u'protocol': 5,
                u'linkState': 4,
                u'label': u'DP-2',
                u'mode': 3,
                u'device': [
                    u'cage3',
                    u'cage4',
                    u'cage5'
                ],
                u'nodeWWN': u'50002ACFF701C533',
                u'type': 2,
                u'portPos': {
                    u'node': 1,
                    u'slot': 1,
                    u'cardPort': 2
                }
            },
            {
                u'portPos': {
                    u'node': 1,
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
                    u'stgt': 121,
                    u'netmask': u'0.0.0.0',
                    u'iSCSIName': u'iqn.2000-05.com.3pardata:21210002ac01c533',
                    u'tpgt': 121,
                    u'iSNSPort': 3205,
                    u'gateway': u'0.0.0.0'
                },
                u'partnerPos': {
                    u'node': 0,
                    u'slot': 2,
                    u'cardPort': 1
                },
                u'IPAddr': u'0.0.0.0',
                u'linkState': 4,
                u'device': [

                ],
                u'iSCSIName': u'iqn.2000-05.com.3pardata:21210002ac01c533',
                u'failoverState': 1,
                u'mode': 2,
                u'HWAddr': u'1402EC613B0A',
                u'type': 8
            },
            {
                u'portPos': {
                    u'node': 1,
                    u'slot': 2,
                    u'cardPort': 2
                },
                u'protocol': 2,
                u'iSCSIPortInfo': {
                    u'iSNSAddr': u'0.0.0.0',
                    u'vlan': 1,
                    u'IPAddr': u'0.0.0.0',
                    u'rate': u'10Gbps',
                    u'mtu': 1500,
                    u'stgt': 122,
                    u'netmask': u'0.0.0.0',
                    u'iSCSIName': u'iqn.2000-05.com.3pardata:21220002ac01c533',
                    u'tpgt': 122,
                    u'iSNSPort': 3205,
                    u'gateway': u'0.0.0.0'
                },
                u'partnerPos': {
                    u'node': 0,
                    u'slot': 2,
                    u'cardPort': 2
                },
                u'IPAddr': u'0.0.0.0',
                u'linkState': 4,
                u'device': [

                ],
                u'iSCSIName': u'iqn.2000-05.com.3pardata:21220002ac01c533',
                u'failoverState': 1,
                u'mode': 2,
                u'HWAddr': u'1402EC613B02',
                u'type': 8
            },
            {
                u'portPos': {
                    u'node': 1,
                    u'slot': 3,
                    u'cardPort': 1
                },
                u'protocol': 4,
                u'linkState': 10,
                u'label': u'IP1',
                u'device': [

                ],
                u'mode': 4,
                u'HWAddr': u'941882447CED',
                u'type': 3
            }
        ]
    }

    global parsed_ports_key

    parsed_ports_key = [
        {
            'IPAddr': '172.20.0.150',
            'portPos': {
                'node': 0,
                'slot': 2,
                'cardPort': 1
            },
            'iSCSIPortInfo': {
                'iSNSAddr': '0.0.0.0',
                'vlan': '101',
                'IPAddr': '172.20.0.150',
                'mtu': 9000,
                'stgt': 1024,
                'netmask': '255.255.255.0',
                'tpgt': 1024,
                'iSNSPort': 3205,
                'gateway': '172.20.0.1'
            }
        },
        {
            'IPAddr': '172.20.1.150',
            'portPos': {
                'node': 0,
                'slot': 2,
                'cardPort': 2
            },
            'iSCSIPortInfo': {
                'iSNSAddr': '0.0.0.0',
                'vlan': '102',
                'IPAddr': '172.20.1.150',
                'mtu': 9000,
                'stgt': 1025,
                'netmask': '255.255.255.0',
                'tpgt': 1025,
                'iSNSPort': 3205,
                'gateway': '172.20.1.1'
            }
        },
        {
            'IPAddr': '172.20.0.151',
            'portPos': {
                'node': 1,
                'slot': 2,
                'cardPort': 1
            },
            'iSCSIPortInfo': {
                'iSNSAddr': '0.0.0.0',
                'vlan': '101',
                'IPAddr': '172.20.0.151',
                'mtu': 9000,
                'stgt': 1026,
                'netmask': '255.255.255.0',
                'tpgt': 1026,
                'iSNSPort': 3205,
                'gateway': '172.20.0.1'
            }
        },
        {
            'IPAddr': '172.20.1.151',
            'portPos': {
                'node': 1,
                'slot': 2,
                'cardPort': 2
            },
            'iSCSIPortInfo': {
                'iSNSAddr': '0.0.0.0',
                'vlan': '102',
                'IPAddr': '172.20.1.151',
                'mtu': 9000,
                'stgt': 1027,
                'netmask': '255.255.255.0',
                'tpgt': 1027,
                'iSNSPort': 3205,
                'gateway': '172.20.1.1'
            }
        }
    ]

    global expanded_ports_key
    expanded_ports_key = [
        {
            u'portPos': {
                'node': 0,
                'cardPort': 1,
                'slot': 2
            },
            u'device': [

            ],
            u'linkState': 4,
            u'partnerPos': {
                u'node': 1,
                u'cardPort': 1,
                u'slot': 2
            },
            u'iSCSIPortInfo': {
                'vlan': '101',
                'gateway': '172.20.0.1',
                'iSNSPort': 3205,
                'mtu': 9000,
                'IPAddr': '172.20.0.150',
                'stgt': 1024,
                'netmask': '255.255.255.0',
                'tpgt': 1024,
                'iSNSAddr': '0.0.0.0'
            },
            u'type': 8,
            u'protocol': 2,
            u'failoverState': 1,
            u'IPAddr': '172.20.0.150',
            u'iSCSIName': u'iqn.2000-05.com.3pardata:20210002ac01c533',
            u'HWAddr': u'1402EC613AFA',
            u'mode': 2
        },
        {
            u'portPos': {
                'node': 0,
                'cardPort': 2,
                'slot': 2
            },
            u'device': [

            ],
            u'linkState': 4,
            u'partnerPos': {
                u'node': 1,
                u'cardPort': 2,
                u'slot': 2
            },
            u'iSCSIPortInfo': {
                'vlan': '102',
                'gateway': '172.20.1.1',
                'iSNSPort': 3205,
                'mtu': 9000,
                'IPAddr': '172.20.1.150',
                'stgt': 1025,
                'netmask': '255.255.255.0',
                'tpgt': 1025,
                'iSNSAddr': '0.0.0.0'
            },
            u'type': 8,
            u'protocol': 2,
            u'failoverState': 1,
            u'IPAddr': '172.20.1.150',
            u'iSCSIName': u'iqn.2000-05.com.3pardata:20220002ac01c533',
            u'HWAddr': u'1402EC613AF2',
            u'mode': 2
        },
        {
            u'portPos': {
                'node': 1,
                'cardPort': 1,
                'slot': 2
            },
            u'device': [

            ],
            u'linkState': 4,
            u'partnerPos': {
                u'node': 0,
                u'cardPort': 1,
                u'slot': 2
            },
            u'iSCSIPortInfo': {
                'vlan': '101',
                'gateway': '172.20.0.1',
                'iSNSPort': 3205,
                'mtu': 9000,
                'IPAddr': '172.20.0.151',
                'stgt': 1026,
                'netmask': '255.255.255.0',
                'tpgt': 1026,
                'iSNSAddr': '0.0.0.0'
            },
            u'type': 8,
            u'protocol': 2,
            u'failoverState': 1,
            u'IPAddr': '172.20.0.151',
            u'iSCSIName': u'iqn.2000-05.com.3pardata:21210002ac01c533',
            u'HWAddr': u'1402EC613B0A',
            u'mode': 2
        },
        {
            u'portPos': {
                'node': 1,
                'cardPort': 2,
                'slot': 2
            },
            u'device': [

            ],
            u'linkState': 4,
            u'partnerPos': {
                u'node': 0,
                u'cardPort': 2,
                u'slot': 2
            },
            u'iSCSIPortInfo': {
                'vlan': '102',
                'gateway': '172.20.1.1',
                'iSNSPort': 3205,
                'mtu': 9000,
                'IPAddr': '172.20.1.151',
                'stgt': 1027,
                'netmask': '255.255.255.0',
                'tpgt': 1027,
                'iSNSAddr': '0.0.0.0'
            },
            u'type': 8,
            u'protocol': 2,
            u'failoverState': 1,
            u'IPAddr': '172.20.1.151',
            u'iSCSIName': u'iqn.2000-05.com.3pardata:21220002ac01c533',
            u'HWAddr': u'1402EC613B02',
            u'mode': 2
        }
    ]
