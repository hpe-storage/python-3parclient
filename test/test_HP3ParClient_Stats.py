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

"""Test class of 3Par Client handling Stats."""

import mock
from test import HP3ParClient_base
from hp3parclient import exceptions


class HP3ParClientStatsTestCase(HP3ParClient_base.HP3ParClientBaseTestCase):

    def setUp(self):
        super(HP3ParClientStatsTestCase, self).setUp(withSSH=True)

    def tearDown(self):
        # very last, tear down base class
        super(HP3ParClientStatsTestCase, self).tearDown()

    def test_getCPGStatData(self):
        self.printHeader('getCPGStatData')

        # Find a cpg name
        cpgs = self.cl.getCPGs()
        cpg = cpgs['members'][0]
        name = cpg['name']
        self.assertTrue(self.findInDict(cpgs['members'], 'name', name))
        # Make srstatld give valid output
        self.cl._run = mock.Mock(return_value=[
            ',,---IO/s----,,,-KBytes/s--,,,---Svct ms----,,,-IOSz KBytes-,,,,',
            'Time,Secs,Rd,Wr,Tot,Rd,Wr,Tot,Rd,Wr,Tot,Rd,Wr,Tot,QLen,AvgBusy%',
            '2015-07-02 01:45:00 PDT,1435826700,1.3,6.2,7.5,4.6,89.3,93.9,'
            '0.63,10.18,8.54,3.6,14.3,12.5,0,0.0',
            '2015-07-02 13:40:00 PDT,1435869600,1.3,6.2,7.5,4.6,88.6,93.1,'
            '0.34,10.34,8.63,3.6,14.3,12.4,0,0.0',
            '----------------------------------------------------------------'
            '-----------------------------------------',
            ',144,1.3,6.7,8.0,4.7,95.6,100.4,0.59,10.24,8.69,3.7,14.2,12.5,'
            '0.9,0.1',
        ])
        # Get result
        interval = 'daily'
        history = '7d'
        result = self.cl.getCPGStatData(name, interval, history)
        # Check result
        self.assertIsNotNone(result)
        self.assertTrue(type(result) is dict)
        # Make srstatld give invalid output
        self.cl._run = mock.Mock(return_value=[''])
        # Expect exception
        self.assertRaises(exceptions.SrstatldException,
                          self.cl.getCPGStatData,
                          name, interval, history)
        self.printFooter('getCPGStatData')

# testing
# suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientCPGTestCase)
# unittest.TextTestRunner(verbosity=2).run(suite)
