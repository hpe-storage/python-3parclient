import sys, os
sys.path.insert(0,os.path.realpath(os.path.abspath('../')))

from hp3parclient import client, exceptions
import nose.tools

def setup():
    #we need to start flask
    :x


def teardown():

cl = client.HP3ParClient("http://localhost:5000/api/v1")


def test_Login():
    cl.login("foo", "bar")
    assert False
