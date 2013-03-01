#!/usr/bin/env python

from distutils.core import setup, Extension
import os

DISTUTILS_DEBUG=True

setup(name='pidaqif',
	version='1.0',
	ext_modules=[Extension('pidaqif', [os.path.join('pidaqif','pidaqif.c')])],
)
