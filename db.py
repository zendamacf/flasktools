from collections import OrderedDict
from flask import g
import psycopg2
import psycopg2.extras
from . import exceptions


def _creds():
	from web import config
	try:
		return {
			'database': config.DBNAME,
			'user': config.DBUSER,
			'password': config.DBPASS,
			'port': config.DBPORT,
			'host': config.DBHOST
		}
	except AttributeError as e:
		raise exceptions.DBSetupException() from e


def connect_database() -> psycopg2.extensions.connection:
	# Only initialise connection once per request maximum
	if 'conn' in g:
		g.conn.set_client_encoding('UTF8')
		return g.conn
	creds = _creds()
	g.conn = psycopg2.connect(
		database=creds['database'],
		user=creds['user'],
		password=creds['password'],
		port=creds['port'],
		host=creds['host'],
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
