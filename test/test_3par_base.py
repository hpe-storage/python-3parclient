import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import pprint

class Test3PARBase(unittest.TestCase):

    def setUp(self):
        username = "3paradm"
        password = "3pardata"
        self.cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
        self.cl.login(username, password)

    def tearDown(self):
        self.cl.logout()

    def printHeader(self, name):
        print "Start testing '%s'" % name

    def printFooter(self, name):
        print "Compeleted testing '%s'" % name
