#!/usr/bin/env python

from setuptools import setup

setup(name='plait',
    version='0.1.0',
    description='execute ssh commands against hosts in parallel',
    author='Dustin Lacewell',
    author_email='dlacewell@gmail.com',
    url='https://github.com/dustinlacewell/plait',
    packages=['plait'],
    entry_points={
        'console_scripts': [
            'plait = plait.cli:main',
        ],
    }
)
