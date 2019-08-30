# (c) Copyright 2015 Hewlett Packard Development Company, L.P.
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
import collections

""" Parser for 3PAR showport commands.

:Author: Derek Chadwell

:Description: Parser to create port objects similar to the json
objects return by WSAPI commands. This functionality fills gaps
in iscsi port data reported by WSAPI commands, namely iSCSI
ports with vlan tags.

"""


class ShowportParser:
    """ Parses the following showport commands on an HP 3par array
        showport
        showport -iscsi
        showport -iscsivlan
    """

    def __init__(self):
        self.parser_methods_by_header = {
            'N:S:P': self._parsePortLocation,
            'VLAN': self._parseVlan,
            'IPAddr': self._parseIPAddr,
            'Gateway': self._parseGateway,
            'MTU': self._parseMtu,
            'TPGT': self._parseTpgt,
            'STGT': self._parseSTGT,
            'iSNS_Addr': self._parseIsnsAddr,
            'iSNS_Port': self._parseIsnsPort,
            'Netmask/PrefixLen': self._parseNetmask,
        }

    def parseShowport(self, port_show_output):
        """Parses the showports output from HP3Parclient.ssh.run([cmd])
            Returns: an array of port-like dictionaries similar to what you
                     get from the wsapi GET /ports endpoint.

                NOTE: There are several pieces that showports doesn't
                      give you that don't exist in this output.
        """
        new_ports = []

        # the last two lines are just a dashed line
        # and the number of entries returned.  We don't want those
        port_show_output = port_show_output[0:-2]

        if not port_show_output:
            return new_ports

        # The first array in the
        # ports output list is the headers
        headers = port_show_output.pop(0).split(',')

        # then parse each line and create a port-like
        # dictionary from it
        for line in port_show_output:
            new_port = {}
            entries = line.split(',')
            for i, entry in enumerate(entries):
                parser = self.parser_methods_by_header[headers[i]]
                self._merge_dict(new_port, parser(entry))

            new_ports.append(new_port)

        return new_ports

    def _parsePortLocation(self, nps):
        """Parse N:S:P data into a dictionary with key "portPost"
            "portPos":{
                "node":0,
                "slot":0,
                "cardPort":1
            },
        """

        nps_array = nps.split(':')

        port_pos = {'portPos': {
            'node': int(nps_array[0]),
            'slot': int(nps_array[1]),
            'cardPort': int(nps_array[2])
        }
        }

        return port_pos

    def _parseVlan(self, vlan):
        """the vlan key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'vlan': vlan}}

    def _parseIPAddr(self, address):
        """the IP key/value pair as part of the iSCSIPortInfo dict"""
        return {'IPAddr': address,
                'iSCSIPortInfo': {'IPAddr': address}}

    def _parseGateway(self, gw):
        """the gw key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'gateway': gw}}

    def _parseMtu(self, mtu):
        """the mtu key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'mtu': int(mtu)}}

    def _parseTpgt(self, tpgt):
        """the tpgt key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'tpgt': int(tpgt)}}

    def _parseSTGT(self, stgt):
        """the stgt key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'stgt': int(stgt)}}

    def _parseIsnsAddr(self, addr):
        """the isns key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'iSNSAddr': addr}}

    def _parseIsnsPort(self, port):
        """the isns key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'iSNSPort': int(port)}}

    def _parseNetmask(self, mask):
        """the network key/value pair as part of the iSCSIPortInfo dict"""
        return {'iSCSIPortInfo': {'netmask': mask}}

    def _merge_dict(self, d1, d2):
        """
        Modifies d1 in-place to contain values from d2.  If any value
        in d1 is a dictionary (or dict-like), *and* the corresponding
        value in d2 is also a dictionary, then merge them in-place.
        """
        for k, v2 in d2.items():
            v1 = d1.get(k)  # returns None if v1 has no value for this key
            if (isinstance(v1, collections.Mapping) and
                    isinstance(v2, collections.Mapping)):
                self._merge_dict(v1, v2)
            else:
                d1[k] = v2
