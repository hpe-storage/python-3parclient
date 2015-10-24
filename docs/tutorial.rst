Tutorial
========

This tutorial is intended as an introduction to working with
**HPE3PARClient**.

Prerequisites
-------------
Before we start, make sure that you have the **HPE3PARClient** distribution
:doc:`installed <installation>`. In the Python shell, the following
should run without raising an exception:

.. code-block:: bash

  >>> import hpe3parclient

This tutorial also assumes that a 3PAR array is up and running and the
WSAPI service is enabled and running.

Create the Client and login
---------------------------
The first step when working with **HPE3PARClient** is to create a
:class:`~hpe3parclient.client.HPE3ParClient` to the 3PAR drive array
and logging in to create the session.   You must :meth:`~hpe3parclient.client.HPE3ParClient.login` prior to calling the other APIs to do work on the 3PAR.
Doing so is easy:

.. code-block:: python

  from hpe3parclient import client, exceptions
  # this creates the client object and sets the url to the
  # 3PAR server with IP 10.10.10.10 on port 8008.
  cl = client.HPE3ParClient("http://10.10.10.10:8008/api/v1")

  # SSL certification verification is defaulted to False. In order to
  # override this, set secure=True. or secure='/path/to/cert.crt'
  # cl = client.HPE3ParClient("https://10.10.10.10:8080/api/v1",
  #                          secure=True)
  # Or, to use ca certificates as documented by Python Requests,
  # pass in the ca-certificates.crt file
  # http://docs.python-requests.org/en/v1.0.4/user/advanced/
  # cl = client.HPE3ParClient("https://10.10.10.10:8080/api/v1",
  #                          secure='/etc/ssl/certs/ca-certificates.crt')

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
a call to :meth:`~hpe3parclient.client.HPE3ParClient.getVolumes`.

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

Using the File Persona Client
-----------------------------
The **HPE3PARFilePersonaClient** extends the **HPE3PARClient** adding File
Persona capabilities.  When you need File Persona capabilities, create a
:class:`~hpe3parclient.file_client.HPE3ParFilePersonaClient` instead of the
:class:`~hpe3parclient.client.HPE3ParClient`.
For example, the following code shows how to use this client to get volumes
like above and also get File Provisioning Groups with the extended client
making a call to :meth:`~hpe3parclient.file_client.HPE3ParFilePersonaClient.getfpg`.

.. code-block:: python

    import pprint

    from hpe3parclient import file_client

    username = 'your-3PAR-user-name'
    password = 'your-3PAR-password'
    ip = '10.10.10.10'

    cl = file_client.HPE3ParFilePersonaClient("https://%s:8080/api/v1" % ip)
    # to override SSL certificate verification pass secure=True
    # cl = file_client.HPE3ParFilePersonaClient("https://%s:8080/api/v1" % ip,
    #                                          secure=True)
    # Or, to use ca certificates as documented by Python Requests,
    # pass in the ca-certificates.crt file
    # http://docs.python-requests.org/en/v1.0.4/user/advanced/
    # cl = client.HPE3ParClient("https://10.10.10.10:8080/api/v1",
    #                          secure='/etc/ssl/certs/ca-certificates.crt')
    cl.setSSHOptions(ip, username, password)
    cl.login(username, password)

    volumes = cl.getVolumes()
    pprint.pprint(volumes)

    fpgs = cl.getfpg()
    pprint.pprint(fpgs)

    cl.logout()
