from functools import wraps
from celery import Celery
from celery.bin.celery import CeleryCommand
from celery.exceptions import CeleryError as CeleryException
from flask import Flask, current_app as app


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
