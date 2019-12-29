import setuptools

with open('README.md', 'r') as fh:
	long_description = fh.read()

setuptools.setup(
	name='flasktools',
	version='1.0.8',
	author='Zachary Lang',
	author_email='zach.d.lang@gmail.com',
	description='Utilities for Flask websites',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/zachdlang/flasktools',
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.6',
	setup_requires=[
		'wheel'
	],
	install_requires=[
		'flask',
		'Pillow',
		'passlib',
		'celery',
		'psycopg2'
	]
)
