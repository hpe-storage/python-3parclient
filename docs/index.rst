HP3PARClient |release| Documentation
========================================

Overview
--------
**HP3PARClient** is a Python package containing a class that uses 
HTTP REST calls to talk with an HP 3PAR drive array.
distribution containing tools for working with
`3PAR Storage Arrays <http://www.3par.com>`_. 
work with MongoDB from Python. This documentation attempts to explain
everything you need to know to use **HP3PARClient**.

Issues
------
The Client currently doesn't support host creation/management.  This is due
to the 3PAR WSAPI not supporting hosts in the REST API.

.. todo:: create the open source website 
.. todo:: create the bug tracker

All issues should be reported (and can be tracked / voted for /
commented on) at the main `HP3PARClient  JIRA bug tracker
<http://jira.mongodb.org/browse/PYTHON>`_, in the "3PAR Python Driver"
project.

Changes
-------
See the :doc:`changelog` for a full list of changes to HP3PARClient.


About This Documentation
------------------------
This documentation is generated using the `Sphinx
<http://sphinx.pocoo.org/>`_ documentation generator. The source files
for the documentation are located in the *doc/* directory of the
**PyMongo** distribution. To generate the docs locally run the
following command from the root directory of the **PyMongo** source:

.. toctree::
   :maxdepth: 4

   hp3parclient
   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

