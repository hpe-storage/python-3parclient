import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import unittest
import pprint

class Test3PARBase(unittest.TestCase):

    def setUp(self):
        username = "3paradm"
        password = "3pardata"
        global cl
        cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
        cl.login(username, password)

    def tearDown(self):
        cl.logout()
