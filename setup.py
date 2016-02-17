#!/usr/bin/python3

from distutils.core import setup

setup(                                                                                                                                         
	name='pyalfred',
	version='0.0.2',
	license='GPL',
	description='Python client library for alfred mesh monitoring',
	author='Dominik Heidler',
	author_email='dominik@heidler.eu',
	url='http://github.com/asdil12/pyalfred',
	packages=['pyalfred'],
	scripts=['bin/pyalfred'],
)

