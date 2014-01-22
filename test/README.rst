Unit tests
==========

1. pip install nose
2. pip install nose-testconfig
3. use config.ini to configure unit tests
4. run tests with: nosetests --tc-file config.ini

Optional alternatives
1. Run tests with code and branch coverage: 
   nosetests --with-coverage --cover-package=hp3parclient --cover-html  --tc-file config.ini   
2. Manually run flask server (when config.ini unit=true):
    python test_HP3ParMockServer_flask.py -port 5001 -user 3paradm -password 3pardata -debug
3. Run a specific test
   nosetests --tc-file config.ini file.py:class_name.test_method_name
