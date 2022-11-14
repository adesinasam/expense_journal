# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in expense_journal/__init__.py
from expense_journal import __version__ as version

setup(
	name='expense_journal',
	version=version,
	description='ERPNext Expenses',
	author='Glistercp',
	author_email='support@glistercp.com.ng',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
