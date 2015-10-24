Installing / Upgrading
======================
.. highlight:: bash


**HPE3PARClient** is in the `Python Package Index
<http://pypi.python.org/pypi/hpe3parclient/>`_.

Installing with pip
-------------------

We prefer `pip <http://pypi.python.org/pypi/pip>`_
to install pymongo on platforms other than Windows::

  $ pip install hpe3parclient

To upgrade using pip::

  $ pip install --upgrade hpe3parclient

Installing with easy_install
----------------------------

If you must install hpe3parclient using
`setuptools <http://pypi.python.org/pypi/setuptools>`_ do::

  $ easy_install hpe3parclient

To upgrade do::

  $ easy_install -U hpe3parclient


Installing from source
----------------------

If you'd rather install directly from the source (i.e. to stay on the
bleeding edge), then check out the latest source from github and 
install the driver from the resulting tree::

  $ git clone https://github.com/hpe-storage/python-3parclient.git
  $ cd python-3parclient
  $ pip install .

