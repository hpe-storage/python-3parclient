Installing / Upgrading
======================
.. highlight:: bash


**HPE3PARClient** is in the `Python Package Index
<http://pypi.python.org/pypi/python-3parclient/>`_.

Installing with pip
-------------------

We prefer `pip <http://pypi.python.org/pypi/pip>`_
to install pymongo on platforms other than Windows::

  $ pip install python-3parclient

To upgrade using pip::

  $ pip install --upgrade python-3parclient

Installing with easy_install
----------------------------

If you must install hpe3parclient using
`setuptools <http://pypi.python.org/pypi/setuptools>`_ do::

  $ easy_install python-3parclient

To upgrade do::

  $ easy_install -U python-3parclient


Installing from source
----------------------

If you'd rather install directly from the source (i.e. to stay on the
bleeding edge), then check out the latest source from github and 
install the driver from the resulting tree::

  $ git clone https://github.com/hpe-storage/python-3parclient.git
  $ cd python-3parclient
  $ pip install .

Uninstalling an old client
--------------------------

If the older **HP3PARClient** was installed on the system already it
will need to be removed. Run the following command to remove it::

  $ sudo pip uninstall hp3parclient
