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
    cl = client.HP3ParRESTClient("username", "some password",
                           "http://localhost:5000/api/v1", False, None, False, False, True)
    return cl



cl = get_client()
pprint.pprint(cl)
cl.authenticate()
