# Standard library imports
import os
import json
from urllib.request import urlretrieve
from functools import wraps

# Third party imports
from flask import (
	Flask, jsonify, Response, url_for, current_app as app
)
from werkzeug.datastructures import ImmutableMultiDict
from PIL import Image
from celery import Celery
from celery.bin.celery import CeleryCommand
from celery.bin.base import Error as CeleryException


def params_to_dict(d: ImmutableMultiDict, bool_keys: list = []) -> dict:
	if isinstance(d, ImmutableMultiDict):
		# Convert Flask request dict to normal dict
		d = d.to_dict()
	for key, value in d.items():
		if isinstance(value, str):
			value = value.strip()
		if key in bool_keys:
			d[key] = json.loads(value)
		if value == '':
			d[key] = None
	return d


def handle_exception() -> Response:
	return jsonify(error='Internal error occurred. Please try again later.'), 500


def get_static_file(filename: str) -> str:
	return app.static_folder + filename


def serve_static_file(filename: str, **kwargs) -> str:
	fullpath = os.path.join(app.static_folder, filename)
	try:
		kwargs['v'] = str(os.path.getmtime(fullpath))
	except OSError:
		pass

	return url_for(
		'static',
		filename=filename,
		**kwargs,
		_external=True
	)


def strip_unicode_characters(s: str) -> str:
	replacements = {
		'’': "'",
		'\u00a0': ' ',
		'\u00c4': 'A',
		'\u00c6': 'Ae',
		'\u00e1': 'a',
		'\u00fa': 'u',
		'\u00fb': 'u',
		'\u00fc': 'u',
		'\u00f6': 'o',
		'\u2013': '-',
		'\u2014': '-',
		'\u2018': "'",
		'\u2019': "'",
		'\u2022': '-',
		'\u2026': '...',
		'\u201c': '"',
		'\u201d': '"',
		'\u2605': ''
	}
	for key, value in replacements.items():
		s = s.replace(key, value)
	return s


def fetch_image(filename: str, url: str) -> None:
	urlretrieve(url, filename)
	if not filename.endswith('.svg'):
		try:
			img = Image.open(filename)
			img_scaled = img.resize((int(img.size[0] / 2), int(img.size[1] / 2)), Image.ANTIALIAS)
			img_scaled.save(filename, optimize=True, quality=95)
		except IOError:
			pass
	print('Fetched {}'.format(url))


def check_celery_running(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		# Initialise Celery app in library internals
		init_celery(app)
		status = CeleryCommand.commands['status']()
		status.app = status.get_app()
		try:
			status.run()
		except CeleryException:
			raise Exception('No Celery service running.')
		return f(*args, **kwargs)

	return decorated_function


def init_celery(app: Flask) -> Celery:
	celery = Celery(
		app.import_name,
		backend='redis://',
		broker='redis://localhost:6379/0'
	)
	return celery


def setup_celery(app: Flask) -> Celery:
	celery = init_celery(app)

	class ContextTask(celery.Task):
		def __call__(self, *args, **kwargs):
			with app.app_context():
				return self.run(*args, **kwargs)

	celery.Task = ContextTask
	return celery
