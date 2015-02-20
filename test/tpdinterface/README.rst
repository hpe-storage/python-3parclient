tpdinterface.tcl
================

For the Mock SSH server, we need to save a copy of the tpdinterface TCL.
It also has to be limited to the interfaces that we care about because the
paramiko server seems to fail if this gets bigger than 4K.

The tpdinterface.tcl is saved (committed) in this dir and read in by the Mock
SSH server.

When the tpdinterface.tcl needs updating (for example to add more interfaces),
run the unit tests against a live array.  This will create a file called
interface.save.  Copy the interface.save over tpdinterface.tcl file and then
validate by running the tests with unit=true.  When the unit tests pass using
the new tpdinterface.tcl, commit it.
