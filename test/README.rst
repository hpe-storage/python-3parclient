Unit tests
==========

1. pip install nose
2. pip install nose-testconfig
3. use config.ini to configure unit tests
4. run tests with: nosetests --tc-file config.ini

Optional Alternatives
1. Run tests with code and branch coverage:
   nosetests --with-coverage --cover-package=hp3parclient --cover-html  --tc-file config.ini
2. Run a specific test
   nosetests --tc-file config.ini file.py:class_name.test_method_name

Running Simulators

The unit tests should automatically start/stop the simulators.  To start them
manually use the following commands.  To stop them, use 'kill'.  Starting them
manually before running unit tests also allows you to watch the debug output.

    WSAPI: python HP3ParMockServer_flask.py -port 5001 -user <USERNAME> -password <PASSWORD> -debug
    SSH:   python HP3ParMockServer_ssh.py [port]
