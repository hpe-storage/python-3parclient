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

username = "SOMEVALUE"
password = "SOMEVALUE"

cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)


def test_logout():
    print "Test Logout"
    try: 
       cl.login(username, password)
       pprint.pprint("Login worked")
    except exceptions.Unauthorized as ex:
       pprint.pprint("Login Failed")

    try: 
       cl.logout()
       pprint.pprint("Logout worked")
    except exceptions.Unauthorized as ex:
       pprint.pprint("Logout Failed")

def get_volumes():
    print "Get Volumes"
    try:
       volumes = cl.getVolumes()
       pprint.pprint(volumes)
    except exceptions.Unauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex
    print "Complete\n"


def test_create_volume():
    print "Create Volumes"
    try:
       cl.login(username, password)
       cl.createVolume("Volume1", "someCPG", "300")
       cl.createVolume("Volume2", "anotherCPG", 1024, 
                                {'comment': 'something', 'snapCPG':'somesnapcpg'})

    except exceptions.Unauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex

    try:
       cl.createVolume("Volume3", "testCPG", 2048, "foo")
    except Exception as ex:
       pass

    try:
	volume = cl.createVolume("VolumeBad", "testCPG", 2048, {'bogus':'break'})
    except exceptions.BadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeExists", "testCPG", 2048)
    except exceptions.Conflict as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeTooLarge", "testCPG", 10241024)
    except exceptions.BadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeNotEnoughSpace", "testCPG", 9999)
    except exceptions.BadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"

def test_delete_volume():
    print "Test Delete Volume"

    try:
	cl.deleteVolume("foo")
    except exceptions.NotFound as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("forbidden")
    except exceptions.Forbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("retained")
    except exceptions.Forbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("readonlychild")
    except exceptions.Forbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("works")
    except exceptions.NotFound as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"


def get_CPGs():
    print "Get CPGs"
    try:
       cpgs = cl.getCPGs()
       pprint.pprint(cpgs)
    except Exception as ex:
       print ex
    print "Complete\n"

def get_VLUNs():
    print "Get VLUNs"
    try:
       vluns = cl.getVLUNs()
       pprint.pprint(vluns)
    except Exception as ex:
       print ex


def create_CPG():
    print "Create CPGs"
    try:
        optional = {}
        cl.createCPG("WaltTestCPG", optional)
        cl.createCPG("WaltTestCPGi2", {'LDLayout': {'RAIDType' : 1}})
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


#test_create_volume()
#test_delete_volume()
#test_error()
cl.login(username, password)
#get_volumes()
#get_VLUNs()
#get_CPGs()
delete_CPG()
create_CPG()
