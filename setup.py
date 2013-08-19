import hp3parclient

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages
import sys


setup(
  name='hp3parclient',
  version=hp3parclient.version,
  description="HP 3PAR HTTP REST Client",
  author="Walter A. Boring IV",
  author_email="walter.boring@hp.com",
  maintainer="Walter A. Boring IV",
  keywords=["hp", "3par", "rest"],
  requires=['httplib2(>=0.6.0)'],
  install_requires=['httplib2 >= 0.6.0'],
  tests_require=["nose", "werkzeug", "nose-testconfig"],
  license="Apache License, Version 2.0",
  packages=find_packages(),
  provides=['hp3parclient'],
  classifiers=[
     'Development Status :: 3 - Alpha',
     'Intended Audience :: Developers',
     'License :: OSI Approved :: Apache Software License',
     'Environment :: Web Environment',
     'Programming Language :: Python',
     'Programming Language :: Python :: 2.6',
     'Programming Language :: Python :: 2.7',
     'Topic :: Internet :: WWW/HTTP',
     
     ]
  )
