import hp3parclient

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


setup(
  name='hp3parclient',
  version=hp3parclient.version,
  description="HP 3PAR HTTP REST Client",
  author="Walter A. Boring IV",
  author_email="walter.boring@hp.com",
  maintainer="Walter A. Boring IV",
  keywords=["hp", "3par", "rest"],
  requires=['paramiko', 'eventlet', 'requests'],
  install_requires=['paramiko', 'eventlet', 'requests'],
  tests_require=["nose", "werkzeug", "nose-testconfig", "requests"],
  license="Apache License, Version 2.0",
  packages=find_packages(),
  provides=['hp3parclient'],
  url="http://packages.python.org/hp3parclient",
  classifiers=[
     'Development Status :: 5 - Production/Stable',
     'Intended Audience :: Developers',
     'License :: OSI Approved :: Apache Software License',
     'Environment :: Web Environment',
     'Programming Language :: Python',
     'Programming Language :: Python :: 2.6',
     'Programming Language :: Python :: 2.7',
     'Programming Language :: Python :: 3.4',
     'Topic :: Internet :: WWW/HTTP',

     ]
  )
