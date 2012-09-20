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

from hp3parclient import client, exceptions

parser = argparse.ArgumentParser()
parser.add_argument("-debug", help="Turn on http debugging", default=False, action="store_true")
args = parser.parse_args()

username = "3paradm"
password = "3pardata"

cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)

def get_CPGs():
    print "Get CPGs"
    try:
       cpgs = cl.getCPGs()
       pprint.pprint(cpgs)
    except Exception as ex:
       print ex
    print "Complete\n"

def create_CPG():
    print "Create CPGs"
    try:
        optional = {}
        name = "WaltTestCPG"
        cl.createCPG(name, optional)
        print "Created '%s'" % name
        name = "WaltTestCPG2"
        cl.createCPG(name, {'LDLayout': {'RAIDType' : 1}})
        print "Created '%s'" % name
        name = "WaltTestCPG3"
        cl.createCPG(name, {'LDLayout': {'RAIDType' : 2}})
        print "Created '%s'" % name
        get_CPGs()
    except Exception as ex:
        print ex
    print "Complete\n"

def delete_CPG():
    print "Delete CPGs"
    try:
        cpgs = cl.getCPGs()
        if cpgs and cpgs['total'] > 0:
            for cpg in cpgs['members']:
                if cpg['name'].startswith('WaltTestCPG'):
                    pprint.pprint("Deleteing CPG '%s'" % cpg['name'])
                    cl.deleteCPG(cpg['name'])

    except Exception as ex:
        print ex
    print "Complete\n"


cl.login(username, password)
create_CPG()
delete_CPG()
