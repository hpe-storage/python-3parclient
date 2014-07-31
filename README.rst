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

* Create CPG
* Delete CPG
* Get all CPGs
* Get a CPG

* Create a VLUN
* Delete a VLUN
* Get all VLUNs
* Get a VLUN

* Create a Host
* Delete a Host
* Get all Hosts
* Get a Host

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



