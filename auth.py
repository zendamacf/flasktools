import os
from functools import wraps
from flask import session, redirect, url_for
from passlib.context import CryptContext
from . import db


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
		existing = db.fetch_query(
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
					db.mutate_query(
						"UPDATE app.enduser SET password = %s WHERE id = %s",
						(new_hash, existing['id'],)
					)

				return existing['id']


def is_logged_in() -> bool:
	return session.get('userid') is not None
