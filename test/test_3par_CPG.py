import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import pprint
import test_3par_base

class TestCPG(test_3par_base.Test3PARBase):

    def test_1_create_CPG(self):
        print "Start testing create_CPG"
        try:
            optional = {'domain': 'WALT_TEST'}
            name = 'UnitTestCPG'
            cl.createCPG(name, optional)
            print "Created %s " % name

            cpg1 = cl.getCPG(name)
            self.assertIsNotNone(cpg1) 

            name = 'UnitTestCPG2'
            optional2 = optional.copy()
            more_optional = {'LDLayout':{'RAIDType':1}}
            optional2.update(more_optional)
            cl.createCPG(name, optional2)
            print "Created %s " % name

            cpg2 = cl.getCPG(name)
            self.assertIsNotNone(cpg2) 
      
        except Exception as ex:
            print ex
    
        print "Completed testing create_CPG"
    
    def test_2_get_CPG(self):
        print "Start testing get_CPG"
        try:
            cpgs = cl.getCPGs()
            pprint.pprint(cpgs)
        except Exception as ex:
            print ex
      
        print "Completed testing get_CPG"

    def test_3_delete_CPG(self):
        print "Start testing delete_CPG"
        try:
            cpgs = cl.getCPGs()
            if cpgs and cpgs['total'] > 0:
                for cpg in cpgs['members']:
                    if cpg['name'].startswith('UnitTestCPG'):
                        pprint.pprint("Deleting CPG %s " % cpg['name'])
                        cl.deleteCPG(cpg['name'])
        except Exception as ex:
            print ex

        print "Completed testing delete_CPG"
   
if __name__ == '__main__':
	unittest.main()
