HP 3PAR REST Client
===================
This is a Client library that can talk to the HP 3PAR Storage array.  The 3PAR
storage array has a REST web service interface.
This client library implements a simple interface to talking with that REST
interface using the python httplib2 http library.

Requirements
============
This branch requires 3.1.3 version MU1 of the 3PAR firmware.

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

Installation
============

::

 $ python setup.py install


Unit Tests
==========

::

 $ pip install nose
 $ pip install nose-testconfig
 $ cd test
 $ nosetests --tc-file config.ini


Folders
=======
* docs -- contains the documentation.
* hp3parclient -- the actual client.py library
* test -- unit tests
* samples -- some sample uses


Documentation
=============

To view the built documentation point your browser to

::

  python-3parclient/docs/_build/html/index.html



