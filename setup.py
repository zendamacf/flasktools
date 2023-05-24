import setuptools

with open('README.md', 'r') as fh:
	long_description = fh.read()

setuptools.setup(
	name='flasktools',
	version='2.0.0',
	author='Zachary Lang',
	author_email='zach.d.lang@gmail.com',
	description='Utilities for Flask websites',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/zendamacf/flasktools',
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.9',
	setup_requires=[
		'wheel'
	],
	install_requires=[
		'flask>=2.3.2',
		'Pillow>=9.5.0',
		'passlib>=1.7.4',
		'celery>=5.2.7',
		'psycopg2>=2.9.6',
		'pyjwt>=2.7.0'
	]
)
