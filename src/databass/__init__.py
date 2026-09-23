import os
from datetime import datetime
from decimal import Decimal
from flask import Flask, g
from flask.json.provider import DefaultJSONProvider
from dotenv import load_dotenv
from .db.base import app_db
from .db.util import ensure_db_placeholders
from .routes import register_routes

load_dotenv()
VERSION = os.environ.get("VERSION")
print(f"App version: {VERSION}")


class AppJSONProvider(DefaultJSONProvider):
    """Serialize Decimal (from Postgres avg()/sum() aggregates) as JSON
    numbers instead of Flask's default fallback to a string."""

    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object("config.Config")
    app.json_provider_class = AppJSONProvider
    app.json = AppJSONProvider(app)

    is_testing = (
        "PYTEST_CURRENT_TEST" in os.environ
        or app.config.get("TESTING", False)
        or os.environ.get("TESTING", "").lower() == "true"
    )
    if is_testing:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True

    app.static_folder = "static"
    app_db.init_app(app)

    with app.app_context():
        from .db.models import Base, Release

        Base.metadata.bind = app_db.engine
        Base.metadata.create_all(app_db.engine)
        ensure_db_placeholders()
        app_db.session.commit()
        from .releases.routes import release_bp

        app.register_blueprint(release_bp)

        from .artists.routes import artist_bp

        app.register_blueprint(artist_bp)

        from .labels.routes import label_bp

        app.register_blueprint(label_bp)

        from .errors.routes import error_bp

        app.register_blueprint(error_bp)

        from .spa import spa_bp

        app.register_blueprint(spa_bp)

        register_routes(app)

        _start_listenbrainz_scheduler(app, is_testing)

        @app.before_request
        def before_request():
            g.app_version = VERSION
            g.total_logged = Release.total_count()
            today = datetime.now()
            g.day_of_year = today.timetuple().tm_yday
            g.current_year = today.year

        return app


def _start_listenbrainz_scheduler(app: Flask, is_testing: bool) -> None:
    """Start the optional importer once per production app instance."""
    if is_testing or not os.environ.get("LISTENBRAINZ_USERNAME"):
        return
    if not _scheduler_should_start(app):
        return
    try:
        from flask_apscheduler import APScheduler
        from .listenbrainz_sync import sync_listens

        scheduler = APScheduler()
        scheduler.init_app(app)
        scheduler.add_job(
            id="listenbrainz_sync",
            func=lambda: _run_listenbrainz_sync(app, sync_listens),
            trigger="interval",
            minutes=max(app.config.get("LISTENBRAINZ_SYNC_INTERVAL_MIN", 15), 1),
            # Run once on boot so a fresh install starts filling immediately
            # rather than waiting a full interval.
            next_run_time=datetime.now(),
            replace_existing=True,
        )
        scheduler.start()
        app.extensions["listenbrainz_scheduler"] = scheduler
    except Exception as err:  # optional integration must not prevent app startup
        app.logger.warning("ListenBrainz scheduler unavailable: %s", err)


def _scheduler_should_start(app: Flask) -> bool:
    """Whether this process should own the background importer.

    The Werkzeug dev server runs a reloader parent plus a child; only the child
    (marked by ``WERKZEUG_RUN_MAIN``) should schedule jobs. Gunicorn has no such
    split and sets no Werkzeug marker — and ``Config.DEBUG`` is always True
    here — so production is detected via the compose-provided ``DOCKER`` flag
    instead of ``app.debug``.
    """
    if os.environ.get("WERKZEUG_RUN_MAIN") in ("true", "1"):
        return True
    if os.environ.get("DOCKER", "").lower() in ("true", "1"):
        return True
    return not app.debug


def _run_listenbrainz_sync(app: Flask, sync_fn) -> None:
    with app.app_context():
        try:
            sync_fn()
        except Exception:
            app.logger.exception("ListenBrainz sync failed")
