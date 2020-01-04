# Standard library imports
from functools import wraps
from datetime import datetime, timedelta, timezone

# Third party imports
from flask import request, jsonify, current_app
import jwt

# Local imports
from ..sitetools import db

LIFE_SPAN = timedelta(hours=1)


def _gen_token_payload(
	userid: int,
	lifespan: timedelta,
	token_type: str
) -> dict:
	issued = datetime.now(timezone.utc)
	return {
		'iss': current_app.name.upper(),
		'iat': issued,
		'exp': issued + lifespan,
		'sub': userid,
		'token_type': token_type,
	}


def _validate_auth_token(token: str) -> int:
	userid = None
	try:
		if token is not None:
			payload = jwt.decode(token.encode(), current_app.secret_key)
			userid = payload['sub']
	except (jwt.exceptions.ExpiredSignatureError, jwt.exceptions.InvalidTokenError):
		pass

	if userid is not None:
		existing = db.fetch_query(
			"SELECT * FROM app.enduser WHERE id = %s",
			(userid,),
			single_row=True
		)
		if existing:
			return userid
	return None


def generate_auth_token(userid: int) -> str:
	payload = _gen_token_payload(
		userid,
		timedelta(days=7),
		'bearer'
	)

	token = jwt.encode(payload, current_app.secret_key)
	return token.decode()


def auth_token_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		print(current_app.name)
		userid = _validate_auth_token(request.headers.get('Authorization'))
		if userid is None:
			return jsonify('Unauthorized access.'), 401
		return f(userid, *args, **kwargs)

	return decorated_function
