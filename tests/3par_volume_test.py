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

testVolName = "WALTTESTVOL"

cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)


def get_volumes():
    print "Get Volumes"
    try:
       volumes = cl.getVolumes()
       if volumes:
           for volume in volumes['members']:
               print "Found '%s'" % volume['name']
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex
    print "Complete\n"


def create_volumes():
    print "Create Volumes"
    cpgName = "WALTTESTCPG"

    try:
       cl.createCPG(cpgName, {'LDLayout' : {'RAIDType' : 1}})
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except exceptions.HTTPConflict as ex:
       # the cpg already exists.
       pass
    except Exceptions as ex:
       pprint.pprint(ex)
       return


    try:
       volName = "%s1" % testVolName
       print "Creating '%s'" % volName
       cl.createVolume(volName, cpgName, 300)
       volName = "%s2" % testVolName
       print "Creating '%s'" % volName
       cl.createVolume(volName, cpgName, 1024, 
                       {'comment': 'something', 'tpvv': True})

    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex

    try:
	volume = cl.createVolume("%s1" % testVolName, cpgName, 2048)
    except exceptions.HTTPConflict as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"

def delete_volumes():
    try:
       volumes = cl.getVolumes()
       if volumes:
           for volume in volumes['members']:
               if volume['name'].startswith(testVolName):
                   print "Deleting volume '%s'" % volume['name']
                   cl.deleteVolume(volume['name'])
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex


cl.login(username, password)
get_volumes()
create_volumes()
delete_volumes()
