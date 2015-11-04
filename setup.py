#!/usr/bin/env python

from setuptools import setup


install_requires = filter(lambda d: not d.startswith('-e'), open("requirements.txt", "r").readlines())

setup(
    name='plait',
    version='0.1.0',
    description='execute ssh commands against hosts in parallel',
    author='Dustin Lacewell',
    author_email='dlacewell@gmail.com',
    url='https://github.com/dustinlacewell/plait',
    packages=['plait', 'plait.app'],
    install_requires=install_requires + ['twisted'],
    dependency_links = ['https://github.com/twisted/twisted/tarball/trunk#egg=twisted'],
    entry_points={
        'console_scripts': [
            'plait = plait.cli:main',
        ],
    }
)
