Installing / Upgrading
======================
.. highlight:: bash


**HP3PARClient** is in the `Python Package Index
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
bleeding edge), then check out the latest source from github and 
install the driver from the resulting tree::

  $ git clone https://github.com/hp-storage/python-3parclient.git
  $ cd python-3parclient
  $ pip install .

