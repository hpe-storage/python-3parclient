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


cl = client.HP3ParClient("http://localhost:5000/api/v1")
if "debug" in args and args.debug == True:
    cl.debug_rest(True)


def test_login():
    #this will fail
    print "Test Logout"
    try: 
       cl.login("username", "hp")
       pprint.pprint("Login worked")
    except exceptions.Unauthorized as ex:
       pprint.pprint("Login Failed")

def test_logout():
    print "Test Logout"
    #this will work
    try: 
       cl.login("user", "hp")
       pprint.pprint("Login worked")
    except exceptions.Unauthorized as ex:
       pprint.pprint("Login Failed")

    try: 
       cl.logout()
       pprint.pprint("Logout worked")
    except exceptions.Unauthorized as ex:
       pprint.pprint("Logout Failed")


def test_create_volume():
    print "Create Volumes"
    try:
       cl.login("user", "hp")
       cl.createVolume("Foo", "someCPG", "300")
    except exceptions.Unauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex


def test_get_volumes():
    print "Get Volumes"
    try:
       cl.login("user", "hp")
       cl.getVolumes()
    except exceptions.Unauthorized as ex:
       pprint.pprint("You must login first")
    except Exception as ex:
       print ex


def test_error():
    print "test Error"
    try:
       resp, body = cl.http.get('/throwerror')
       pprint.pprint(resp)
       pprint.pprint(body)
    except Exception as ex:
       print ex



#test_create_volume()
test_get_volumes()
test_error()
