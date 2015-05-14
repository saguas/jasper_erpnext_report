from setuptools import setup, find_packages
import os

version = '1.1.0'

#with open("requirements.txt", "r") as f:
#	install_requires = f.readlines()

setup(
	name='jasper_erpnext_report',
	version=version,
	description='Make your own reports in other formats.',
	author='Luis Fernandes',
	author_email='luisfmfernandes@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	#install_requires=install_requires
	install_requires=[
		"frappe",
		"semantic_version",
		"lxml",
		"PyPDF2",
		"cython"
	]
)
