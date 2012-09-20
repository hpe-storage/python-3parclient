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

def get_VLUNs():
    print "Get VLUNs"
    try:
       vluns = cl.getVLUNs()
       pprint.pprint(vluns)
    except Exception as ex:
       print ex


def create_VLUNs():
    """ creates 3 VLUNs.  
        assumes Volumes already exist
    """
    print "Create VLUNs"
    try:
        optional = {}
        name = "WaltTestVOL"
        cl.createVLUN(name, 1, 'walt-workstation.americas.hpqcorp.net')
        print "Created '%s'" % name
        name = "WaltTestVOL2"
        cl.createVLUN(name, 2, 'walt-workstation.americas.hpqcorp.net')
        print "Created '%s'" % name
        name = "WaltTestVOL3"
        cl.createVLUN(name, 3, 'walt-workstation.americas.hpqcorp.net', 
                      {'node': 1, 'slot' : 2, 'cardPort' : 3 },
                      True, True)
        print "Created '%s'" % name
        get_VLUNs()
    except Exception as ex:
        print ex
    print "Complete\n"

def delete_VLUNs():
    print "Delete VLUNs"
    try:
        cpgs = cl.getVLUNs()
        if cpgs and cpgs['total'] > 0:
            for cpg in cpgs['members']:
                if cpg['name'].startswith('WaltTestVLUN'):
                    pprint.pprint("Deleteing VLUN '%s'" % cpg['name'])
                    cl.deleteCPG(cpg['name'])

    except Exception as ex:
        print ex
    print "Complete\n"


cl.login(username, password)
get_VLUNs()
create_VLUNs()
#delete_VLUNs()
