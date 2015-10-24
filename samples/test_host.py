import argparse
from os import sys
import random
from sys import path
from os import getcwd
import os, sys, inspect, pprint
import time

# this is a hack to get the hpe driver module
# and it's utils module on the search path.
cmd_folder = os.path.realpath(os.path.abspath("..") )
if cmd_folder not in sys.path:
     sys.path.insert(0, cmd_folder)

from hpe3parclient import client, exceptions
from utils import *

parser = argparse.ArgumentParser()
parser.add_argument("-debug", help="Turn on http debugging", default=False, action="store_true")
args = parser.parse_args()

username = "admin"
password = "hpe"

testVolName = "WALTTESTVOL6969"
testSNAPName = testVolName+"SNAP"
testCPGName = "WALTTESTCPG"
TESTHOST = 'WALTOpenStackHost'
DOMAIN = 'WALT_TEST'
PORT = {'node': 1, 'slot' : 8, 'cardPort':1}

#cl = client.HPE3ParClient("https://localhost:8080/api/v1")
cl = client.HPE3ParClient("https://10.10.22.241:8080/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)
cl.login(username, password)


def create_test_host():
    try:
        host = cl.getHost(TESTHOST)
        print("host already exists")
    except exceptions.HTTPNotFound as ex:
        iscsi = ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000']
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        extra = {
#                 'iSCSINames': ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000'],
#                 'FCWwns': ['00:00:00:00:00:00:00:00',
#                            '11:11:11:11:11:11:11:11'],
                 'domain' : DOMAIN,
                 'descriptors': {
                     'IPAddr' : '10.10.22.132',
                     'os' : 'Ubuntu Linux 12.04',
                     'location' : 'death star',
                     'model' : 'episode IV',
                     'contact' : 'Vader',
                     'comment' : 'Use the force luke'
                 },
#                 'portPos': {'cardPort': 1, 'node': 1, 'slot': 8}
                }
        #cl.createHost(TESTHOST, iscsi, None, extra)
        #cl.createHost(TESTHOST, None, fc, extra)
        cl.createHost(TESTHOST, None, None, extra)
        pass
    except exceptions.HTTPUnauthorized as ex:
        print("You must login")
    except Exception as ex:
        print(ex)

def delete_test_host():
    try:
        cl.deleteHost(TESTHOST)
    except exceptions.HTTPUnauthorized as ex:
        print("You must login")
    except Exception as ex:
        print(ex)

def modify_test_host():
    try:
        host = cl.getHost(TESTHOST)
        print("host already exists")
        iscsi = ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000']
        fc = ['00:00:00:00:00:00:00:00', '11:11:11:11:11:11:11:11']
        extra = {
#                 'iSCSINames': ['iqn.1993-08.org.debian:01:00000000000', 'iqn.bogus.org.debian:01:0000000000'],
#                 'FCWwns': ['00:00:00:00:00:00:00:00',
#                            '11:11:11:11:11:11:11:11'],
                 'domain' : DOMAIN,
                 'descriptors': {
                     'IPAddr' : '10.10.22.132',
                     'os' : 'Ubuntu Linux 12.04',
                     'location' : 'death star',
                     'model' : 'episode IV',
                     'contact' : 'Vader',
                     'comment' : 'Use the force luke'
                 },
#                 'portPos': {'cardPort': 1, 'node': 1, 'slot': 8}
                }

        mod_request = {
                'pathOperation' : 1,
                'iSCSINames' : iscsi, # One or more WWN to set for the host.
        }

        cl.modifyHost(TESTHOST, mod_request)
        #cl.createHost(TESTHOST, None, fc, extra)
        #cl.createHost(TESTHOST, None, None, extra)
        pass
    except exceptions.HTTPUnauthorized as ex:
        print("You must login")
    except Exception as ex:
        print(ex)

def get_hosts():
    try:
        hosts = cl.getHosts()
        print(hosts)
    except exceptions.HTTPNotFound as ex:
        print(ex)

#create_test_host()
#get_host(cl, TESTHOST)
#delete_test_host()

get_hosts()
#create_test_host()
#modify_test_host()
#delete_test_host()
