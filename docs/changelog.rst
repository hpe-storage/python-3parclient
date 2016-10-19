Changelog
=========

Changes in Version 4.2.3
------------------------
* Fixed exceptions invocation order.

Changes in Version 4.2.2
------------------------
* Fixed online physical copy logic.
* Fixed setQOSRule doesn't work if max_bw is not defined
* Fixed bug with ssh client creation with privatekey argument passed explicitly
* Fixed bug where get_description() needs to be invoked on exceptions instead of Exception. Refer bug 1586266
* Fixed getvfs in Manila client to return multiple VFS entries and not just 1

Changes in Version 4.2.1
------------------------
* Add retries for certain exceptions.
    - exceptions.HTTPServiceUnavailable
    - requests.exceptions.ConnectionError

Changes in Version 4.2.0
------------------------
* Remove the destCPG during copyVolume operations when it's not an online
  copy.  3PAR will throw an error if we don't
* Added valid key checks in the flask unit test server for the
  createPhysicalVolume action

Changes in Version 4.1.0
------------------------
* Adds the ability to retrieve all snapshots associated with a given volume
* Fixes passing in the flag to the client object in order to suppressing
  SSL warnings

Changes in Version 4.0.2
------------------------
* Fixed documentation and README errors

Changes in Version 4.0.1
------------------------
* Fixed error where you could not create a LUN with the ID of 0. (issue #17)
* Allows suppressing of InsecureRequestWarning messages (Issue #18)
* Changes the exception isinstance check to look for basestring/str instead of
  bytes in order to properly store the error description.
* Allows changing timeouts for requests
* Added remote copy support
   - getRemoteCopyInfo
   - getRemoteCopyGroups
   - getRemoteCopyGroup
   - createRemoteCopyGroup
   - removeRemoteCopyGroup
   - modifyRemoteCopyGroup
   - addVolumeToRemoteCopyGroup
   - removeVolumeFromRemoteCopyGroup
   - startRemoteCopy
   - stopRemoteCopy
   - synchronizeRemoteCopyGroup
   - recoverRemoteCopyGroupFromDisaster
   - toggleRemoteCopyConfigMirror
* Testing remote copy against two live arrays is now supported through
  config.ini

Changes in Version 4.0.0
------------------------
* Rebranded the client from HP to HPE.
* Updated documentation to use the new PyPi project name for the
  client, 'python-3parclient'.

Changes in Version 3.3.0
------------------------
* Replaced all httplib2 calls with Python Request calls
* SSL certificate verification can be enabled by passing secure=True
* SSL certificate verification can be done against a self provided .crt file
  with secure='/path/to/ca-certificates.crt'

Changes in Version 3.2.2
------------------------
* Python3.4+ compliant
* Added requirements-py3.txt and test-requirements-py3.txt for Python3.4 to
  pull and install from
* Updated tox to run py34 tests
* Modified basic Python calls to work with both Python2 and Python3.4
* Added optional 'ca' parameter to createfshare and setfshare (for SMB
  Continuous Availability)
* Improved handling of nested and optional lists in File Persona get methods
* Volume Set snapshot capabilities have been added
* Adds tests for volume set snapshots
* Fixed error that was happening during client initialization when an error
  was missing a description. (issue #15)
* Add support for VLUN queries in getVLUN and getHostVLUNs when a backend
  with WSAPI 1.4.2 or greater is being used.
* Added support for calling srstatld with a given interval and history
* Added unit tests for the Exception class.

Changes in Version 3.2.1
------------------------
* Improved debug capabilities during initialization of the client.
* Reworked findHost to use a random hostname to fix collisions
* Fix cross-protocol share hang by using non-interactive flag
* Require 3.2.1 (MU3) for File Persona client
* Improved file client test coverage
* Renew SSH session if lost and increase retry attempts to 2 (issue #5)
* Added missing exceptions to API docs for deleteVolume.
* Fix JSON parsing using Python3
* Be safe accessing 'hostname' key in getHostVLUNs (issue #14)

Changes in Version 3.2.0
------------------------
* Added File Persona Client:
   - getfs
   - createfpg
   - growfpg
   - getfpg
   - setfpg
   - removefpg
   - createvfs
   - getvfs
   - setvfs
   - removevfs
   - createfsip
   - setfsip
   - getfsip
   - removefsip
   - createfsgroup
   - setfsgroup
   - removefsgroup
   - createfsuser
   - setfsuser
   - removefsuser
   - createfstore
   - getfstore
   - setfstore
   - removefstore
   - createfshare
   - setfshare
   - getfshare
   - removefshare
   - createfsnap
   - getfsnap
   - removefsnap
   - startfsnapclean
   - getfsnapclean
   - stopfsnapclean
   - setfsquota
   - getfsquota
   - gettpdinterface

* Added paramiko SSH simulator initially supporting just a few test cases.
* Fixed PEP8 violations.
* Change GitHub account reference from WaltHP to hp-storage.
* Modify the steps in the Installing from Source section to ensure correct
  installation of dependencies and ordering.
* Added support for flash cache policy set on a virtual volume set.
* Added tox environments to run tests with code coverage and to generate the documentation
* Consolidated the test/README.rst into the top level README.rst and added clarifications

Changes in Version 3.1.3
------------------------
* Added 'paramiko' and 'eventlet' requirements to setup.py.  Running a standard
  python setup.py install should install these modules now if they are
  missing.
* Use static loggers to fix duplicate logging problem.
* Update unit tests to better support more backend configurations and versions.
* Made corrections to the API documentation.

Changes in Version 3.1.2
------------------------
* Added API
   - findAllVolumeSets
   - getCPGAvailableSpace
   - getOverallSystemCapacity
* Revised unit tests to use asserts instead of try/catch/except blocks.
* Removed SSH call from the findVolumeSet method and replaced it with REST.
* Improved findVolumeSet documentation.
* Changed SSH connections to now only get created when an SSH command needs
  to be executed.
* Added closing of an SSH connection during logout if one is active.
* Changed SSH connections to no longer use keep-alive packets to stay active.
* Removed an unneeded print statement output that was occuring when an SSH
  connection was closed.

Changes in Version 3.1.1
------------------------
* Added known_host_file and missing_key_policy parameters to:
  - HP3ParClient.setSSHOptions
  - HP3PARSSHClient
* Fixed an issue with building the ClientException when body of the response
  was empty.
* Fixed spelling error in urllib import for Python 3.0 or greater
  environments.

Changes in Version 3.1.0
------------------------

* Added APIs
   - setVolumeMetaData
   - getVolumeMetaData
   - getAllVolumeMetaData
   - removeVolumeMetaData
   - findVolumeMetaData
* Added two new enumerations for CHAP initiator and target.
* Converted existing metadata functions to use REST API calls instead of SSH.
* Updated the minimum required HP 3PAR build version to be 3.1.3.230.  This
  corresponds to 3.1.3 MU1 firmware.
* Added support for volume metadata REST API calls in the flask server.
* Numerous API documentation improvements
* Fixed 2 enumerations
   - PORT_TYPE_RCIP changed to 7
   - PORT_TYPE_ISCSI changed to 8
* Numerous Enumerations added
   - Port Type
   - Port Protocol
   - Task Type
   - VLUN Type
   - CPG RAID
   - CPG HA
   - CPG Chunklet
   - CPG Disk Type
   - Host Persona
* Added host set API:
   - findHostSet
   - getHostSets
   - getHostSet
   - createHostSet
   - deleteHostSet
   - modifyHostSet
   - addHostToHostSet
   - removeHostFromHostSet
   - removeHostFromItsHostSet
* Added showpatch API:
   - getPatch
   - getPatches
* Unit tests and flask server
   - Fixed missing tearDown() to improve flask server shutdown.
   - Added VLUN and host set check before allowing deleteHost.
   - Fixed some flask error codes and error messages to match array.
   - Removed the 'test\_' prefix from classes that don't contain tests.
   - Reduced volume sizes used in tests.
   - Made domain and cpg_ldlayout_ha configurable.
   - Added more tests.
* Bug fixes
   - Fixed an incorrect exception message for getHostVLUNs.

Changes in Version 3.0.0
------------------------
* Requires the 3.1.3 3PAR Firmware or greater.
* Added new 3.1.3 firmware APIs.
* Added support for QOS and Virtual Volume sets
* Added query host by wwns or iqns
* Added APIs for getTasks, stopOfflinePhysicalCopy, modifyVolume

Changes in Version 2.9.2
------------------------
* Removed the ssh pooling to fix an issue with timeouts

Changes in Version 2.9.1
------------------------
* Renamed stopPhysicalCopy to stopOnlinePhysicalCopy

Changes in Version 2.9.0
------------------------
* Added SSH interface
* Added stopPhysicalCopy
* updated doc string to fix some pylint

Changes in Version 1.1.0
------------------------

* Added support for hosts and ports

Changes in Version 1.0.1
------------------------

* The unit tests now work when running nosetest from the top level dir
  and from the test dir

Changes in Version 1.0.0
------------------------
* First implementation of the REST API Client
