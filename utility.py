# Standard library imports
import os
import requests
from functools import wraps
from collections import OrderedDict
import json
from urllib.request import urlretrieve

# Third party imports
from flask import (
	Flask, g, redirect, url_for, session, request,
	jsonify, Response, current_app as app
)
from werkzeug import ImmutableMultiDict
from passlib.context import CryptContext
import psycopg2
import psycopg2.extras
from PIL import Image
from celery import Celery
from celery.bin.celery import CeleryCommand
from celery.bin.base import Error as CeleryException

# Local imports
from web import config


def check_login(username: str, password: str) -> bool:
	ok = False

	userid = authenticate_user(username, password)
	if userid is not None:
		ok = True
		session.new = True
		session.permanent = True
		session['userid'] = userid

	return ok


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if not is_logged_in():
			return redirect(url_for('login'))
		return f(*args, **kwargs)

	return decorated_function


def authenticate_user(username: str, password: str) -> int:
	if username is not None and password is not None:
		existing = fetch_query(
			"SELECT * FROM app.enduser WHERE TRIM(username) = TRIM(%s)",
			(username,),
			single_row=True
		)
		if existing:
			password_context = CryptContext().from_path(
				os.path.dirname(os.path.abspath(__file__)) + '/passlibconfig.ini'
			)
			ok, new_hash = password_context.verify_and_update(
				password.strip(),
				existing['password'].strip()
			)
			if ok:
				if new_hash:
					mutate_query(
						"UPDATE app.enduser SET password = %s WHERE id = %s",
						(new_hash, existing['id'],)
					)

				return existing['id']


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
		backend=config.CELERY_BACKEND,
		broker=config.CELERY_BROKER
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


def is_logged_in() -> bool:
	return session.get('userid') is not None


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


def connect_database() -> psycopg2.extensions.connection:
	# Only initialise connection once per request maximum
	if 'conn' in g:
		g.conn.set_client_encoding('UTF8')
		return g.conn
	g.conn = psycopg2.connect(
		database=config.DBNAME, user=config.DBUSER,
		password=config.DBPASS, port=config.DBPORT,
		host=config.DBHOST,
		cursor_factory=psycopg2.extras.DictCursor
	)
	g.conn.set_client_encoding('UTF8')
	# Not using request path as application due to Celery
	return g.conn


def disconnect_database() -> None:
	if 'conn' in g:
		g.conn.close()


def fetch_query(qry: str, qargs: tuple = None, single_row: bool = False) -> any:
	resp = None
	conn = connect_database()

	cursor = conn.cursor()
	try:
		cursor.execute(qry, qargs)
		resp = query_to_dict_list(cursor)
		if single_row is True:
			resp = resp[0] if len(resp) > 0 else None
	except psycopg2.DatabaseError:
		cursor.close()
		raise
	cursor.close()

	return resp


def mutate_query(qry: str, qargs: tuple = None, returning: bool = False, executemany: bool = False) -> any:
	if returning is True and executemany is True:
		raise Exception('Cannot run executemany and return results.')
	resp = None
	conn = connect_database()

	cursor = conn.cursor()
	try:
		if executemany is True:
			cursor.executemany(qry, qargs)
		else:
			cursor.execute(qry, qargs)
		conn.commit()
		if returning is True:
			resp = query_to_dict_list(cursor)
			resp = resp[0] if len(resp) > 0 else None
	except psycopg2.DatabaseError:
		conn.rollback()
		cursor.close()
		raise
	cursor.close()

	return resp


def query_to_dict_list(cursor: psycopg2.extras.DictCursor) -> list:
	d = []
	for row in cursor.fetchall():
		r = OrderedDict()
		for (attr, val) in zip((d[0] for d in cursor.description), row):
			if val == '':
				val = None
			r[str(attr)] = val
		d.append(r)
	return d


def get_static_file(filename: str) -> str:
	return app.static_folder + filename


def strip_unicode_characters(s: str) -> str:
	replacements = {
		'’': "'",
		'\u2014': '-',
		'\u2605': ''
	}
	for key, value in replacements.items():
		s = s.replace(key, value)
	return s


def pagecount(count: int, limit: int) -> int:
	import math
	pages = 0
	if count:
		pages = count / limit
		if pages > 0 and pages < 1:
			pages = 1
		else:
			# Checking for overflow
			if limit % count != 0:
				pages = math.ceil(pages)
	return int(pages)


def fetch_image(filename: str, url: str) -> None:
	urlretrieve(url, filename)
	if not filename.endswith('.svg'):
		img = Image.open(filename)
		img_scaled = img.resize((int(img.size[0] / 2), int(img.size[1] / 2)), Image.ANTIALIAS)
		img_scaled.save(filename, optimize=True, quality=95)
	print('Fetched {}'.format(url))


def check_image_exists(imageurl: str) -> bool:
	resp = requests.get(imageurl)
	return resp.status_code == 200


class BetterExceptionFlask(Flask):
	def log_exception(self, exc_info):
		"""Overrides log_exception called by flask to give more information
		in exception emails.
		"""
		err_text = """
URL:                  {}{}
HTTP Method:          {}
Client IP Address:    {}

request.form:
{}

request.args:
{}

session:
{}

""".format(
			request.host, request.path,
			request.method,
			request.remote_addr,
			request.form,
			request.args,
			session,
		)

		self.logger.critical(err_text, exc_info=exc_info)
