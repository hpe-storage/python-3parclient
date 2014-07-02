Changelog
=========

Changes in Version 3.0.1
------------------------
- Added APIs
  - setVolumeMetaData
  - getVolumeMetaData
  - getAllVolumeMetaData
  - removeVolumeMetaData
  - findVolumeMetaData
- Added two new enumerations for CHAP initiator and target.
- Converted existing metadata functions to use REST API calls
  instead of SSH.
- Updated the minimum requierd HP 3PAR build version to be 3.1.3.230.
- Added support for volume metadata REST API calls in the flask server.

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
