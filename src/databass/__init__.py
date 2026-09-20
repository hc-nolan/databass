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

        @app.before_request
        def before_request():
            g.app_version = VERSION
            g.total_logged = Release.total_count()
            today = datetime.now()
            g.day_of_year = today.timetuple().tm_yday
            g.current_year = today.year

        return app
