Unit tests
==========

1. pip install nose
2. pip install nose-testconfig
3. use config.ini to configure unit tests
4. run tests with: nosetests --tc-file config.ini
5. run tests with coverage: nosetests --with-coverage --cover-package=hp3parclient --cover-html  --tc-file config.ini   
