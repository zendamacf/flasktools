# Standard library imports
import os
import json
from urllib.request import urlretrieve

# Third party imports
from flask import (
	jsonify, Response, url_for, current_app as app
)
from werkzeug.datastructures import ImmutableMultiDict
from PIL import Image


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
		'\u2014': '-',
		'\u2605': '',
		'\u201c': '"',
		'\u201d': '"',
		'\u2022': '-',
		'\u00a0': ' ',
		'\u2013': '-',
		'\u2026': '...'
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
