HP 3PAR REST Client
===================
This is a Client library that can talk to the HP 3PAR Storage array.  The 3PAR
storage array has a REST web service interface as of 3.1.2 of the firmware.
This client library implements a simple interface to talking with that REST
interface using the python httplib2 http library.

Capabilities
============
* Create Volume
* Delete Volume
* Get all volumes
* Get a volume

* Create CPG
* Delete CPG
* Get all CPGs
* Get a CPG

* Create a VLUN
* Delete a VLUN
* Get all VLUNs
* Get a VLUN


Installation
============

::

 $ python setup.py install


Unit Tests
==========

::

 $ pip install nose
 $ cd test
 $ nosetests


Folders
=======
* docs -- contains the documentation.
* hp3parclient -- the actual client.py library
* test -- unit tests


Documentation
=============

To view the built documentation point your browser to

::

  python-3parclient/docs/_build/html/index.html



