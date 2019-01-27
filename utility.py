# Standard library imports
import os
import requests
from functools import wraps
from collections import OrderedDict

# Third party imports
from flask import (
	Flask, g, redirect, url_for, session, request,
	current_app as app
)
from passlib.context import CryptContext


def check_login(username, password):
	ok = False
	if username is not None and password is not None:
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM app.enduser WHERE TRIM(username) = TRIM(%s)""", (username,))
		if cursor.rowcount > 0:
			resp = query_to_dict_list(cursor)[0]
			password_context = CryptContext().from_path(os.path.dirname(os.path.abspath(__file__)) + '/passlibconfig.ini')
			ok, new_hash = password_context.verify_and_update(password.strip(), resp['password'].strip())
			if ok:
				if new_hash:
					cursor.execute("""UPDATE app.enduser SET password = %s WHERE id = %s""", (new_hash, resp['id'],))
					g.conn.commit()
				session.new = True
				session.permanent = True
				session['userid'] = resp['id']
		cursor.close()

	return ok


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if not is_logged_in():
			return redirect(url_for('login'))
		return f(*args, **kwargs)

	return decorated_function


def is_logged_in():
	return session.get('userid') is not None


def params_to_dict(request_params):
	d = request_params.to_dict()
	for key, value in d.items():
		if isinstance(value, str):
			value = value.strip()
		if value == '':
			d[key] = None
	return d


def query_to_dict_list(cursor):
	d = []
	for row in cursor.fetchall():
		r = OrderedDict()
		for (attr, val) in zip((d[0] for d in cursor.description), row):
			if val == '':
				val = None
			r[str(attr)] = val
		d.append(r)
	return d


def get_static_file(filename):
	return app.static_folder + filename


def strip_unicode_characters(s):
	replacements = {'’': "'"}
	for key, value in replacements.items():
		s = s.replace(key, value)
	return s.encode('ascii', 'ignore').decode('ascii')


def pagecount(count, limit):
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


def check_image_exists(imageurl):
	resp = requests.get(imageurl)
	return resp.status_code == 200


class BetterExceptionFlask(Flask):
	def log_exception(self, exc_info):
		"""Overrides log_exception called by flask to give more information
		in exception emails.
		"""
		err_text = """
URL:                  %s%s
HTTP Method:          %s
Client IP Address:    %s

request.form:
%s

request.args:
%s

session:
%s

""" % (
			request.host, request.path,
			request.method,
			request.remote_addr,
			request.form,
			request.args,
			session,
		)

		self.logger.critical(err_text, exc_info=exc_info)
