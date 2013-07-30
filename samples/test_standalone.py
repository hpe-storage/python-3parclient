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
testSNAPName = testVolName+"SNAP"
testCPGName = "WALTTESTCPG"

#cl = client.HP3ParClient("https://localhost:8080/api/v1")
cl = client.HP3ParClient("https://10.10.22.241:8080/api/v1")
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

def get_hosts():
    print "Get Hosts"
    try:
       hosts = cl.getHosts()
       if hosts:
           for host in hosts['members']:
               pprint.pprint(host)
#               print "Found '%s'" % host['name']
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex

def get_host(hostname):
    try:
        host = cl.getHost(hostname)
        pprint.pprint(host)
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex

def get_vluns():
    print "Get VLUNs"
    try:
        vluns = cl.getVLUNs()
        if vluns:
            pprint.pprint(vluns)
            for vlun in vluns['members']:
                print "Found CPG '%s'" % vlun['volumeName']
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex

def get_vlun(vlunname):
    try:
        vlun = cl.getVLUN(vlunname)
        pprint.pprint(vlun)
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex


def get_cpgs():
    print "Get CPGs"
    try:
        cpgs = cl.getCPGs()
        if cpgs:
            for cpg in cpgs['members']:
                print "Found CPG '%s'" % cpg['name']
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex

def create_test_host():
    hostname = "WALT_TEST_HOST2"
    try:
        host = cl.getHost(hostname)
        print "host already exists"
    except exceptions.HTTPNotFound as ex:
        cl.createHost(hostname, {'domain':'WALT_TEST'})
        pass
    except exceptions.HTTPUnauthorized as ex:
        print "You must login"
    except Exception as ex:
        print ex

def delete_test_host():
    try:
        cl.deleteHost("WALT_TEST_HOST2")
    except exceptions.HTTPUnauthorized as ex:
        print "You must login"
    except Exception as ex:
        print ex

def create_test_cpg():
    try:
       cl.createCPG(testCPGName, {'domain':'WALT_TEST', 'LDLayout' : {'RAIDType' : 1}})
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except exceptions.HTTPConflict as ex:
       # the cpg already exists.
       pass
    except Exception as ex:
       pprint.pprint(ex)
       return

def delete_test_cpg():
    try:
       cl.deleteCPG(testCPGName)
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except exceptions.HTTPConflict as ex:
       # the cpg already exists.
       pass
    except Exception as ex:
       pprint.pprint(ex)
       return




def create_volumes():
    print "Create Volumes"
    try:
       volName = "%s1" % testVolName
       print "Creating Volume '%s'" % volName
       cl.createVolume(volName, testCPGName, 300)
       volName = "%s2" % testVolName
       print "Creating Volume '%s'" % volName
       cl.createVolume(volName, testCPGName, 1024, 
                       {'comment': 'something', 'tpvv': True})

    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex

    try:
	volume = cl.createVolume("%s1" % testVolName, testCPGName, 2048)
    except exceptions.HTTPConflict as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"

def create_snapshots():
    print "Create Snapshots"
    try:
        volName = "%s11" % testVolName
        print "Creating Volume '%s'" % volName
        cl.createVolume(volName, testCPGName, 100, {'snapCPG': testCPGName})
        volume = cl.getVolume(volName)

        snapName = "%s1" % testSNAPName
        print "Creating Snapshot '%s'" % snapName
        cl.createSnapshot(snapName, volName, 
                          {'readOnly' : True, 'comment': "Some comment",
#                          {'comment': "Some comment",
                           'retentionHours' : 1,
                           'expirationHours' : 2})
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex
    print "Complete\n"


def delete_snapshots():
    print "Delete Snapshots"
    try:
       volumes = cl.getVolumes()
       if volumes:
           for volume in volumes['members']:
               if volume['name'].startswith(testSNAPName):
                   print "Deleting volume '%s'" % volume['name']
                   cl.deleteVolume(volume['name'])
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       print ex

    print "Complete\n"


def delete_volumes():
    print "Delete Volumes"
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

    print "Complete\n"


cl.login(username, password, {'InServ':'10.10.22.241'})
#get_cpgs()
#create_test_host()
get_hosts()
#get_host('manualkvmtest')
#get_vluns()
#get_vlun('WALTTESTVOL11')
#delete_test_host()
#get_hosts()
#get_volumes()
#create_test_cpg()
#create_volumes()
#delete_volumes()
#create_snapshots()
#delete_snapshots()
#delete_test_cpg()
