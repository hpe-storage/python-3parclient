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

"""Test class of 3Par Client handling VLUN"""

import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import test_HP3ParClient_base

CPG_NAME1 = 'CPG1_VLUN_UNIT_TEST'
CPG_NAME2 = 'CPG2_VLUN_UNIT_TEST'
VOLUME_NAME1 = 'VOLUME1_VLUN_UNIT_TEST'
VOLUME_NAME2 = 'VOLUME2_VLUN_UNIT_TEST'
DOMAIN = 'UNIT_TEST_DOMAIN'
HOST_NAME1 = 'HOST1_VLUN_UNIT_TEST'
HOST_NAME2 = 'HOST2_VLUN_UNIT_TEST'
LUN_1 = 1
LUN_2 = 2
PORT_1 = {'node':1, 'cardPort':1, 'slot':1}


class HP3ParClientVLUNTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):
    
    def setUp(self):
        super(HP3ParClientVLUNTestCase, self).setUp()        
       
        try :
            optional = {'domain': DOMAIN}
            self.cl.createCPG(CPG_NAME1, optional)
        except :
            pass
        try :
            optional = {'domain': DOMAIN}
            self.cl.createCPG(CPG_NAME2, optional)
        except :
            pass
        try :
            self.cl.createVolume(VOLUME_NAME1, CPG_NAME1, 1024)
        except :
            pass
        try :
            self.cl.createVolume(VOLUME_NAME2, CPG_NAME2, 1024)
        except :
            pass  
        try :
            optional = {'domain': DOMAIN}
            self.cl.createHost(HOST_NAME1, None, None, optional)
        except :
            pass
        try :
            optional = {'domain': DOMAIN}
            self.cl.createHost(HOST_NAME2, None, None, optional)
        except :
            pass                
        
    def tearDown(self):

        try:
            self.cl.deleteVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1)
        except Exception:
            pass
        try:
            self.cl.deleteVLUN(VOLUME_NAME2, LUN_2, HOST_NAME2)
        except:
            pass
        try:
            self.cl.deleteVolume(VOLUME_NAME1)
        except:
            pass
        try:
            self.cl.deleteVolume(VOLUME_NAME2)
        except:
            pass
        try:
            self.cl.deleteCPG(CPG_NAME1)
        except:
            pass
        try:
            self.cl.deleteCPG(CPG_NAME2)
        except:
            pass
        try:
            self.cl.deleteHost(HOST_NAME1)
        except:
            pass
        try:
            self.cl.deleteHost(HOST_NAME2)
        except:
            pass

        # very last, tear down base class
        super(HP3ParClientVLUNTestCase, self).tearDown()

    def test_1_create_VLUN(self):
        self.printHeader('create_VLUN')
        #add one
        noVcn = False
        overrideObjectivePriority = True
        self.cl.createVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1, noVcn, overrideObjectivePriority)
        #check
        vlun1 = self.cl.getVLUN(VOLUME_NAME1)
        self.assertIsNotNone(vlun1)
        volName = vlun1['volumeName']
        self.assertEqual(VOLUME_NAME1, volName)
        #add another
        self.cl.createVLUN(VOLUME_NAME2, LUN_2, HOST_NAME2)
        #check
        vlun2 = self.cl.getVLUN(VOLUME_NAME2)
        self.assertIsNotNone(vlun2)
        volName = vlun2['volumeName']
        self.assertEqual(VOLUME_NAME2, volName)
        self.printFooter('create_VLUN')

    def test_1_create_VLUN_tooLarge(self):
        self.printHeader('create_VLUN_tooLarge')

        lun = 100000
        self.assertRaises(exceptions.HTTPBadRequest, self.cl.createVLUN, VOLUME_NAME1, lun, HOST_NAME1, PORT_1)

        self.printFooter('create_VLUN_tooLarge')
   
    def test_1_create_VLUN_volulmeNonExist(self):
        self.printHeader('create_VLUN_volumeNonExist')

        self.assertRaises(exceptions.HTTPNotFound, self.cl.createVLUN, 'Some_Volume', LUN_1, HOST_NAME1, PORT_1)

        self.printFooter('create_VLUN_volumeNonExist')

    def test_1_create_VLUN_badParams(self):
        self.printHeader('create_VLUN_badParams')

        portPos = {'badNode':1, 'cardPort':1, 'slot':2}
        self.assertRaises(exceptions.HTTPBadRequest, self.cl.createVLUN, VOLUME_NAME1, LUN_1, HOST_NAME1, portPos)

        self.printFooter('create_VLUN_badParams')

    def test_2_get_VLUN_bad(self):
        self.printHeader('get_VLUN_bad')
        self.assertRaises(exceptions.HTTPNotFound, self.cl.getVLUN, 'badName')
        self.printFooter('get_VLUN_bad')

    def test_2_get_VLUNs(self):
        self.printHeader('get_VLUNs')
        # add 2
        noVcn = False
        overrideLowerPriority = True
        self.cl.createVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1,
                           PORT_1, noVcn, overrideLowerPriority)
        self.cl.createVLUN(VOLUME_NAME2, LUN_2, HOST_NAME2)
        # get all
        vluns = self.cl.getVLUNs()

        v1 = self.cl.getVLUN(VOLUME_NAME1)
        v2 = self.cl.getVLUN(VOLUME_NAME2)

        self.assertTrue(self.findInDict(vluns['members'], 'lun', v1['lun']))
        self.assertTrue(self.findInDict(vluns['members'], 'volumeName', v1['volumeName']))
        self.assertTrue(self.findInDict(vluns['members'], 'lun', v2['lun']))
        self.assertTrue(self.findInDict(vluns['members'], 'volumeName', v2['volumeName']))

        self.printFooter('get_VLUNs')

    def test_3_delete_VLUN_volumeNonExist(self):
        self.printHeader('delete_VLUN_volumeNonExist')

        self.cl.createVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1)
        self.cl.getVLUN(VOLUME_NAME1)

        self.assertRaises(exceptions.HTTPNotFound, self.cl.deleteVLUN,
                          'UnitTestVolume', LUN_1, HOST_NAME1, PORT_1)

        self.printFooter('delete_VLUN_volumeNonExist')

    def test_3_delete_VLUN_hostNonExist(self):
        self.printHeader('delete_VLUN_hostNonExist')

        self.cl.createVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1)
        self.cl.getVLUN(VOLUME_NAME1)

        self.assertRaises(exceptions.HTTPNotFound, self.cl.deleteVLUN,
                          VOLUME_NAME1, LUN_1, 'BoggusHost', PORT_1)

        self.printFooter('delete_VLUN_hostNonExist')

    def test_3_delete_VLUN_portNonExist(self):
        self.printHeader('delete_VLUN_portNonExist')

        self.cl.createVLUN(VOLUME_NAME2, LUN_2, HOST_NAME2)
        self.cl.getVLUN(VOLUME_NAME2)

        port = {'node': 8, 'cardPort': 8, 'slot': 8}
        try:
            self.cl.deleteVLUN(VOLUME_NAME2, LUN_2, HOST_NAME2, port)
        except exceptions.HTTPBadRequest:
            print 'Expected exception'
            self.printFooter('delete_VLUN_portNonExist')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

        self.fail('No exception occurred.')

    def test_3_delete_VLUNs(self):
        self.printHeader('delete_VLUNs')

        self.cl.createVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1)
        self.cl.getVLUN(VOLUME_NAME1)
        self.cl.deleteVLUN(VOLUME_NAME1 ,LUN_1, HOST_NAME1, PORT_1)
        try:
            self.cl.deleteVLUN(VOLUME_NAME1, LUN_1, HOST_NAME1, PORT_1)
        except exceptions.HTTPNotFound:
            print 'Expected exception'
            self.printFooter('delete_VLUNs')
            return
        except Exception as ex:
            print ex
            self.fail('Failed with unexpected exception')

        self.fail('No exception occurred.')

#testing
#suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientVLUNTestCase)
#unittest.TextTestRunner(verbosity=2).run(suite)
