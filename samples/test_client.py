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


cl = client.HP3ParClient("http://10.10.22.241:8008/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)


def test_login():
    #this will fail
    print "Test Logout"
    try: 
       cl.login("username", "hp")
       pprint.pprint("Login worked")
    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("Login Failed")

def test_logout():
    print "Test Logout"
    #this will work
    try: 
       cl.login("user", "hp")
       pprint.pprint("Login worked")
    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("Login Failed")

    try: 
       cl.logout()
       pprint.pprint("Logout worked")
    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("Logout Failed")

def test_get_volumes():
    print "Get Volumes"
    try:
       cl.login("user", "hp")
       volumes = cl.getVolumes()
       pprint.pprint(volumes)
    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex


def test_create_volume():
    print "Create Volumes"
    try:
       cl.login("user", "hp")
       cl.createVolume("Volume1", "someCPG", "300")
       cl.createVolume("Volume2", "anotherCPG", 1024, 
                                {'comment': 'something', 'snapCPG':'somesnapcpg'})

    except exceptions.HTTPUnauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex

    try:
       cl.createVolume("Volume3", "testCPG", 2048, "foo")
    except Exception as ex:
       pass

    try:
	volume = cl.createVolume("VolumeBad", "testCPG", 2048, {'bogus':'break'})
    except exceptions.HTTPBadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeExists", "testCPG", 2048)
    except exceptions.HTTPConflict as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeTooLarge", "testCPG", 10241024)
    except exceptions.HTTPBadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	volume = cl.createVolume("VolumeNotEnoughSpace", "testCPG", 9999)
    except exceptions.HTTPBadRequest as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"

def test_delete_volume():
    print "Test Delete Volume"

    try:
	cl.deleteVolume("foo")
    except exceptions.HTTPNotFound as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("forbidden")
    except exceptions.HTTPForbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("retained")
    except exceptions.HTTPForbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("readonlychild")
    except exceptions.HTTPForbidden as ex:
	print "Got Expected Exception %s" % ex
        pass

    try:
	cl.deleteVolume("works")
    except exceptions.HTTPNotFound as ex:
	print "Got Expected Exception %s" % ex
        pass

    print "Complete\n"


def test_error():
    print "test Error"
    try:
       resp, body = cl.http.get('/throwerror')
       pprint.pprint(resp)
       pprint.pprint(body)
    except Exception as ex:
       print ex


#test_create_volume()
test_delete_volume()
#test_error()
#test_get_volumes()
