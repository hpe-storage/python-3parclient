Tutorial
========

This tutorial is intended as an introduction to working with
**HP3ParClient**.

Prerequisites
-------------
Before we start, make sure that you have the **HP3ParClient** distribution
:doc:`installed <installation>`. In the Python shell, the following
should run without raising an exception:

.. code-block:: bash

  >>> import hp3parclient

This tutorial also assumes that a 3PAR array is up and running and the
WSAPI service is enabled and running.

Create the Client and login
---------------------------
The first step when working with **HP3ParClient** is to create a
:class:`~hp3parclient.client.HP3ParClient` to the 3PAR drive array 
and logging in to create the session.   You must :meth:`~hp3parclient.client.HP3ParClient.login` prior to calling the other APIs to do work on the 3PAR.
Doing so is easy:

.. code-block:: python

  from hp3parclient import client, exceptions
  #this creates the client object and sets the url to the
  #3PAR server with IP 10.10.10.10 on port 8008.
  cl = client.HP3ParClient("http://10.10.10.10:8008/api/v1")
  # Set the SSH authentication options for the SSH based calls.
  cl.setSSHOptions(ip_address, username, password)

  try:
      cl.login(username, password)
      print "Login worked!"
  except exceptions.HTTPUnauthorized as ex:
      print "Login failed."

When you are done with the the client, it's a good idea to logout from
the 3PAR so there isn't a stale session sitting around.

.. code-block:: python

   cl.logout()
   print "logout worked"

Getting a list of Volumes
-------------------------
After you have logged in, you can start making calls to the 3PAR APIs.
A simple example is getting a list of existing volumes on the array with
a call to :meth:`~hp3parclient.client.HP3ParClient.getVolumes`.

.. code-block:: python

    import pprint
    try:
       volumes = cl.getVolumes()
       pprint.pprint(volumes)
    except exceptions.HTTPUnauthorized as ex:
       print "You must login first"
    except Exception as ex:
       #something unexpected happened
       print ex


.. note:: volumes is an array of volumes in the above call
