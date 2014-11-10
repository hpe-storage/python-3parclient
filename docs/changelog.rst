Changelog
=========

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
