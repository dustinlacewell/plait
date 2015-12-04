#!/usr/bin/env python

from setuptools import setup

setup(
    name='plait',
    version='0.2.0',
    description='execute ssh commands against hosts in parallel',
    author='Dustin Lacewell',
    author_email='dlacewell@gmail.com',
    url='https://github.com/dustinlacewell/plait',
    packages=['plait', 'plait.app'],
    install_requires=[
        'structlog',
        'click',
        'twisted',
        'pycrypto',
        'pyasn1',
        'blessings',
        'blinker',
        'urwid',
    ],
    dependency_links = ['https://github.com/twisted/twisted/tarball/trunk#egg=twisted'],
    entry_points={
        'console_scripts': [
            'plait = plait.cli:main',
        ],
    }
)
