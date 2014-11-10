tpdinterface.tcl
================

For the Mock SSH server, we need to save a copy of the tpdinterface TCL.
It also has to be limited to the interfaces that we care about because the
paramiko server seems to fail if this gets bigger than 4K.

The tpdinterface.tcl is saved (committed) in this dir and read in by the Mock
SSH server.

Instructions for how to rebuild (e.g., expand) this file will be added here
later (next time that change is needed... coming soon).