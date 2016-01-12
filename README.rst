.. image:: https://img.shields.io/pypi/v/python-3parclient.svg
    :target: https://pypi.python.org/pypi/python-3parclient
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/python-3parclient.svg
    :target: https://pypi.python.org/pypi/python-3parclient
    :alt: Downloads

HPE 3PAR REST Client
====================
This is a Client library that can talk to the HPE 3PAR Storage array.  The 3PAR
storage array has a REST web service interface and a command line interface.
This client library implements a simple interface for talking with either
interface, as needed.  The python Requests library is used to communicate
with the REST interface.  The python paramiko library is used to communicate
with the command line interface over an SSH connection.

This is the new location for the rebranded HP 3PAR Rest Client and will be
where all future releases are made. It was previously located on PyPi at:
https://pypi.python.org/pypi/hp3parclient

The GitHub repository for the old HP 3PAR Rest Client is located at:
https://github.com/hpe-storage/python-3parclient/tree/3.x

The HP 3PAR Rest Client (hp3parclient) is now considered deprecated.

Requirements
============
This branch requires 3.1.3 version MU1 or later of the 3PAR firmware.
File Persona capabilities require 3PAR firmware 3.2.1 Build 46 or later.

Capabilities
============
* Create Volume
* Delete Volume
* Get all Volumes
* Get a Volume
* Modify a Volume
* Copy a Volume
* Create a Volume Snapshot

* Create CPG
* Delete CPG
* Get all CPGs
* Get a CPG
* Get a CPG's Available Space

* Create a VLUN
* Delete a VLUN
* Get all VLUNs
* Get a VLUN

* Create a Host
* Delete a Host
* Get all Hosts
* Get a Host
* Get VLUNs for a Host
* Find a Host

* Find a Host Set for a Host
* Get all Host Sets
* Get a Host Set
* Create a Host Set
* Delete a Host Set
* Modify a Host Set

* Get all Ports
* Get iSCSI Ports
* Get FC Ports
* Get IP Ports

* Set Volume Metadata
* Get Volume Metadata
* Get All Volume Metadata
* Find Volume Metadata
* Remove Volume Metadata

* Create a Volume Set
* Delete a Volume Set
* Modify a Volume Set
* Get a Volume Set
* Get all Volume Sets
* Find one Volume Set containing a specified Volume
* Find all Volume Sets containing a specified Volume

* Create a QOS Rule
* Modify a QOS Rule
* Delete a QOS Rule
* Set a QOS Rule
* Query a QOS Rule
* Query all QOS Rules

* Get a Task
* Get all Tasks

* Get a Patch
* Get all Patches

* Get WSAPI Version
* Get WSAPI Configuration Info
* Get Storage System Info
* Get Overall System Capacity

* Stop Online Physical Copy
* Query Online Physical Copy Status
* Stop Offline Physical Copy

* Query Remote Copy Info
* Query a Remote Copy Group
* Query all Remote Copy Groups
* Create a Remote Copy Group
* Delete a Remote Copy Group
* Modify a Remote Copy Group
* Add a Volume to a Remote Copy Group
* Remove a Volume from a Remote Copy Group
* Start Remote Copy on a Remote Copy Group
* Stop Remote Copy on a Remote Copy Group
* Synchronize a Remote Copy Group
* Recover a Remote Copy Group from a Disaster
* Enable/Disable Config Mirroring on a Remote Copy Target

File Persona Capabilities
=========================
* Get File Services Info

* Create a File Provisioning Group
* Grow a File Provisioning Group
* Get File Provisioning Group Info
* Modify a File Provisioning Group
* Remove a File Provisioning Group

* Create a Virtual File Server
* Get Virtual File Server Info
* Modify a Virtual File Server
* Remove a Virtual File Server

* Assign an IP Address to a Virtual File Server
* Get the Network Config of a Virtual File Server
* Modify the Network Config of a Virtual File Server
* Remove the Network Config of a Virtual File Server

* Create a File Services User Group
* Modify a File Services User Group
* Remove a File Services User Group

* Create a File Services User
* Modify a File Services User
* Remove a File Services User

* Create a File Store
* Get File Store Info
* Modify a File Store
* Remove a File Store

* Create a File Share
* Get File Share Info
* Modify a File Share
* Remove a File Share

* Create a File Store Snapshot
* Get File Store Snapshot Info
* Remove a File Store Snapshot

* Reclaim Space from Deleted File Store Snapshots
* Get File Store Snapshot Reclamation Info
* Stop or Pause a File Store Snapshot Reclamation Task

* Set File Services Quotas
* Get Files Services Quota Info

Installation
============

To install::

 $ sudo pip install .

Unit Tests
==========

To run all unit tests::

 $ tox -e py27

To run a specific test::

 $ tox -e py27 -- test/file.py:class_name.test_method_name

To run all unit tests with code coverage::

 $ tox -e cover

The output of the coverage tests will be placed into the ``coverage`` dir.


Folders
=======

* docs -- contains the documentation.
* hpe3parclient -- the actual client.py library
* test -- unit tests
* samples -- some sample uses

Documentation
=============

To build the documentation::

 $ tox -e docs

To view the built documentation point your browser to::

 docs/html/index.html


Running Simulators
==================

The unit tests should automatically start/stop the simulators.  To start them
manually use the following commands.  To stop them, use 'kill'.  Starting them
manually before running unit tests also allows you to watch the debug output.

* WSAPI::

  $ python test/HPE3ParMockServer_flask.py -port 5001 -user <USERNAME> -password <PASSWORD> -debug

* SSH::

  $ python test/HPE3ParMockServer_ssh.py [port]

