Installing / Upgrading
======================
.. highlight:: bash

DO NOT FOLLOW THIS RIGHT NOW.....IT IS NOT ACURATE.
This document is a placeholder for when we get the driver opensourced.
DO NOT FOLLOW THIS RIGHT NOW.....IT IS NOT ACURATE.

**HP3ParClient** is in the `Python Package Index
<http://pypi.python.org/pypi/hp3parclient/>`_.

Installing with pip
-------------------

We prefer `pip <http://pypi.python.org/pypi/pip>`_
to install pymongo on platforms other than Windows::

  $ pip install hp3parclient

To upgrade using pip::

  $ pip install --upgrade hp3parclient

Installing with easy_install
----------------------------

If you must install hp3parclient using
`setuptools <http://pypi.python.org/pypi/setuptools>`_ do::

  $ easy_install hp3parclient

To upgrade do::

  $ easy_install -U hp3parclient


Installing from source
----------------------

If you'd rather install directly from the source (i.e. to stay on the
bleeding edge), install the C extension dependencies then check out the
latest source from github and install the driver from the resulting tree::

  $ git clone git://github.com/mongodb/mongo-python-driver.git pymongo
  $ cd pymongo/
  $ python setup.py install

