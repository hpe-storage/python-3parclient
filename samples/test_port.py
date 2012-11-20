import argparse
from os import sys
import random
from sys import path
from os import getcwd
import os, sys, inspect, pprint
import time

# this is a hack to get the hp driver module
# and it's utils module on the search path.
cmd_folder = os.path.realpath(os.path.abspath("..") )
if cmd_folder not in sys.path:
     sys.path.insert(0, cmd_folder)

from hp3parclient import client, exceptions
from utils import *

parser = argparse.ArgumentParser()
parser.add_argument("-debug", help="Turn on http debugging", default=False, action="store_true")
args = parser.parse_args()

username = "3paradm"
password = "3pardata"

testVolName = "WALTTESTVOL6969"
testSNAPName = testVolName+"SNAP"
testCPGName = "WALTTESTCPG"
TESTHOST = 'WALTOpenStackHost'
DOMAIN = 'WALT_TEST'
PORT = {'node': 1, 'slot' : 8, 'cardPort':1}

#cl = client.HP3ParClient("https://localhost:8080/api/v1")
cl = client.HP3ParClient("https://10.10.22.132:8080/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)
cl.login(username, password, {'InServ':'10.10.22.241'})


ports = cl.getPorts()
pprint.pprint(ports)
ports = cl.getFCPorts()
pprint.pprint(ports)
ports = cl.getiSCSIPorts(cl.PORT_STATE_READY)
pprint.pprint(ports)
