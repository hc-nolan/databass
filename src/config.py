"""
Defines all Flask configurations
"""
from uuid import uuid4
import os
from dotenv import load_dotenv


load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, treating empty values as unset."""
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default

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
    LISTENBRAINZ_USERNAME = os.environ.get('LISTENBRAINZ_USERNAME')
    LISTENBRAINZ_TOKEN = os.environ.get('LISTENBRAINZ_TOKEN')
    LISTENBRAINZ_SYNC_INTERVAL_MIN = _env_int('LISTENBRAINZ_SYNC_INTERVAL_MIN', 15)
    LISTENBRAINZ_BACKFILL_DAYS = _env_int('LISTENBRAINZ_BACKFILL_DAYS', 0)
    # Keep Flask-APScheduler's REST control endpoints off.
    SCHEDULER_API_ENABLED = False
