HP3PARClient |release| Documentation
========================================

Overview
--------
**HP3PARClient** is a Python package containing a class that uses
HTTP REST and SSH calls to talk with an 
`HP 3PAR Storage Array <http://www.3par.com>`_. This documentation
attempts to explain everything you need to know to use **HP3PARClient**.
Some of the API calls use SSH to talk to a 3PAR. This is done only in the case
where the REST API on the 3PAR doesn't exist.

:doc:`installation`
  Instructions on how to get the distribution.

:doc:`tutorial`
  Start here for a quick overview.

:doc:`api/index`
  The complete API documentation, organized by module.

Issues
------
.. todo:: create the open source website 
.. todo:: create the bug tracker

All issues should be reported (and can be tracked / voted for /
commented on) at the main `github issues
<https://github.com/WaltHP/python-3parclient/issues>`_, in the "3PAR Python Driver"
project.

Changes
-------
See the :doc:`changelog` for a full list of changes to **HP3PARClient**.


About This Documentation
------------------------
This documentation is generated using the `Sphinx
<http://sphinx.pocoo.org/>`_ documentation generator. The source files
for the documentation are located in the *doc/* directory of the
**HP3PARClient** distribution. To generate the docs locally run the
following command from the root directory of the **HP3PARClient** source.

.. code-block:: bash

   $ python setup.py doc


.. toctree::
   :hidden:

   installation
   tutorial
   changelog
   api/index


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

