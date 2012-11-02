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

class HP3ParClientVLUNTestCase(test_HP3ParClient_base.HP3ParClientBaseTestCase):

    def test_1_create_VLUN(self):
        self.printHeader('create_VLUN')

        try:
            #add one
            lun = 1 
            volumeName = 'UnitTestVolume'
            hostname = 'UnitTestHost'
            noVcn =  False
            overrideLowerPriority = True
            portPos = {'node':1, 'cardPort':1, 'slot':2}
            self.cl.createVLUN(volumeName, lun, hostname,portPos,noVcn,overrideLowerPriority)

            #assert
            vlun1 = self.cl.getVLUN(volumeName)
            self.assertIsNotNone(vlun1)
            volName = vlun1['volumeName']
            self.assertEqual(volumeName, volName)

            #add another
	    volumeName = 'UnitTestVolume2'
            lun = 2
            optional = {'host':'UnitTestHost', 'noVcn': True, 'overrideLowerPriority': True}
            self.cl.createVolume(volumeName, lun, optional)

            #assert
            vlun2 = self.cl.getVLUN(volumeName)
            self.assertIsNotNone(vlun2)
            volName = vlun2['volumeName']
            self.assertEqual(volumeName, volName)
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_VLUN')
    
    def test_1_create_VLUN_toolarge(self):
        self.printHeader('create_VLUN_badTooLarge')

        #add one
        try:
            volumeName = 'UnitTestLunTooLarge'
            lun = 100
            hostname = 'UnitTestHost'
            noVcn =  False
            overrideLowerPriority = True
            portPos = {'node':1, 'cardPort':1, 'slot':2}
            self.cl.createVLUN(volumeName, lun, hostname,portPos,noVcn,overrideLowerPriority)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_VLUN_badTooLarge')

  
    def test_1_create_VLUN_volulmenonexist(self):
        self.printHeader('create_VLUN_volnonexist')

        #add one
        try:
            volumeName = 'UnitTestNonExistVolume'
            lun = 100
            hostname = 'UnitTestHost'
            noVcn =  False
            overrideLowerPriority = True
            portPos = {'node':1, 'cardPort':1, 'slot':2}
            self.cl.createVLUN(volumeName, lun, hostname,portPos,noVcn,overrideLowerPriority)
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_VLUN_volnonexist')
       
    def test_1_create_VLUN_badParams(self):
        self.printHeader('create_VLUN_badParams')

        #add one
        try:
            volumeName = 'UnitTestNonExistVolume'
            lun = 100
            hostname = 'UnitTestHost'
            noVcn =  False
            overrideLowerPriority = True
            portPos = {'bad node':1, 'cardPort':1, 'slot':2}
            self.cl.createVLUN(volumeName, lun, hostname,portPos,noVcn,overrideLowerPriority)
        except exceptions.HTTPBadRequest:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('create_VLUN_badParams')
  
    """ client.py bug comment out for now 
    def test_2_get_VLUN_bad(self):
        self.printHeader('get_VLUN_bad')

        try:
            name = 'badName'
            vlun = self.cl.getVLUN(name)
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_VLUN_bad')
    """ 

    def test_2_get_VLUNs(self):
        self.printHeader('get_VLUNs')

        try:
            vluns = self.cl.getVLUNs()

            #assert
            volumeName = 'UnitTestVolume'
            v1 = self.cl.getVLUN(volumeName)
	    name = 'UnitTestVolume2'
            v2 = self.cl.getVLUN(volumeName)
            self.assertIn(v1, vluns['members'])
            self.assertIn(v2, vluns['members'])
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('get_VLUN')

    
    def test_3_delete_VLUN_volumenonxist(self):
        self.printHeader('delete_VLUN_volumenonexist')

        try:
            name = 'NonExistVolume'
            lun = 1
            host = 'UnitTestHost'
            self.cl.deleteVLUN(name,lun,host)
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('delete_VLUN_volumenonexist')

    def test_3_delete_VLUN_hostnonxist(self):
        self.printHeader('delete_VLUN_hostnonexist')

        try:
            name = 'UnitTestVolume'
            lun = 1
            host = 'NonExistHost'
            self.cl.deleteVLUN(name,lun,host)
        except exceptions.HTTPNotFound:
            print "Expected exception"
        except Exception as ex:
            print ex
            self.fail("Failed with unexpected exception")

        self.printFooter('delete_VLUN_hostnonexist')
  
    def test_3_delete_VLUN_portnonxist(self):
      self.printHeader('delete_VLUN_portnonexist')

      try:
	  name = 'UnitTestVolume'
	  lun = 1
	  host = 'UnitTestHost'
          port = {'node':8, 'cardPort':8,'slot':8}
	  self.cl.deleteVLUN(name,lun,host,port)
      except exceptions.HTTPNotFound:
	  print "Expected exception"
      except Exception as ex:
	  print ex
	  self.fail("Failed with unexpected exception")

      self.printFooter('delete_VLUN_portnonexist')
  
    def test_3_delete_VLUNs(self):
        self.printHeader('delete_VLUNs')

        try:
            vluns = self.cl.getVLUNs()
            if vluns and vluns['total'] > 0:
                for vl in vluns['members']:
                    if vl['volumeName'].startswith('UnitTestVolume'):
                        self.cl.deleteVLUN(vl['volumeName'],vl['lun'], vl['hostname'])
            #assert
            try:
                name = 'UnitTestVolume'
                vl = self.cl.getVLUN(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail("Failed with unexpected exception")

            try:
                name = 'UnitTestVolume2'
                vl = self.cl.getVLUN(name)
            except exceptions.HTTPNotFound:
                print "Expected exception"
            except Exception as ex:
                print ex
                self.fail ("Failed with unexpected exception")

        except Exception as ex:
            print ex
            self.fail ("Failed with unexpected exception")

        self.printFooter('delete_VLUNs')
   
#testing
suite = unittest.TestLoader().loadTestsFromTestCase(HP3ParClientVLUNTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
