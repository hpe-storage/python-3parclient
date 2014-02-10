Changelog
=========

Changes in Version 3.0.0
------------------------
- Requires the 3.1.3 3PAR Firmware or greater.
- Added new 3.1.3 firmware APIs.
- Added support for QOS and Virtual Volume sets
- Added query host by wwns or iqns
- Added APIs for getTasks, stopOfflinePhysicalCopy, modifyVolume

Changes in Version 2.9.2
------------------------
- Removed the ssh pooling to fix an issue with timeouts

Changes in Version 2.9.1
------------------------
- Renamed stopPhysicalCopy to stopOnlinePhysicalCopy

Changes in Version 2.9.0
------------------------
- Added SSH interface
- Added stopPhysicalCopy
- updated doc string to fix some pylint

Changes in Version 1.1.0
------------------------

- Added support for hosts and ports

Changes in Version 1.0.1
------------------------

- The unit tests now work when running nosetest from the top level dir 
  and from the test dir

Changes in Version 1.0.0
------------------------

- First implementation of the REST API Client
