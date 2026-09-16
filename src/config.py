"""
Defines all Flask configurations
"""
from uuid import uuid4
import os
from dotenv import load_dotenv


load_dotenv()

db_name = os.environ.get('DB_NAME')
db_user = os.environ.get('PG_USER')
db_password = os.environ.get('PG_PASSWORD')
db_hostname = os.environ.get('PG_HOSTNAME')
db_port = os.environ.get('PG_PORT')
db_connection_string = f'postgresql://{db_user}:{db_password}@{db_hostname}:{db_port}/{db_name}'

class Config:
    SECRET_KEY = uuid4().hex
    SQLALCHEMY_DATABASE_URI = db_connection_string
    DISCOGS_KEY = os.environ.get('DISCOGS_KEY')
    DISCOGS_SECRET = os.environ.get('DISCOGS_SECRET')
    TIMEZONE = os.environ.get('TIMEZONE')
    STATIC_FOLDER = 'static'
    DEBUG = True
    # Without this, DEBUG=True causes Flask to re-raise unhandled exceptions
    # instead of routing them through our registered error handlers, so the
    # user-facing error page/JSON responses are never shown.
    PROPAGATE_EXCEPTIONS = False
    # Flask-Assets
    LESS_BIN = '/usr/bin/lessc'
    ASSETS_DEBUG = False
    ASSETS_AUTO_BUILD = True
