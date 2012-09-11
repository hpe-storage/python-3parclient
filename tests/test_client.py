import argparse
from os import sys
import random
from sys import path
from os import getcwd
import os, sys, inspect, pprint

# this is a hack to get the hp driver module
# and it's utils module on the search path.
cmd_folder = os.path.realpath(os.path.abspath("..") )
if cmd_folder not in sys.path:
     sys.path.insert(0, cmd_folder)

from hp3parclient import client


def get_client():
    cl = client.HP3ParClient("http://localhost:5000/api/v1")
    return cl



cl = get_client()
cl.debug_rest(True)
#this will fail
try: 
   cl.login("username", "hp")
   pprint.pprint("Login worked")
except exceptions.Unauthorized, ex:
   pprint.pprint("Login Failed")


#this will work
try: 
   cl.login("user", "hp")
   pprint.pprint("Login worked")
except exceptions.Unauthorized, ex:
   pprint.pprint("Login Failed")


