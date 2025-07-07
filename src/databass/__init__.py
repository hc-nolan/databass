import os
from flask import Flask, g
from flask_assets import Environment, Bundle
from dotenv import load_dotenv
from .db.base import app_db
from .db.util import ensure_db_placeholders
from .routes import register_routes

load_dotenv()
VERSION = os.environ.get("VERSION")
print(f"App version: {VERSION}")


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object("config.Config")
    app.static_folder = "static"
    app_db.init_app(app)

    assets = Environment(app)
    style_bundle = Bundle(
        "src/less/*.less",
        filters="less,cssmin",
        output="dist/css/style.min.css",
        extra={"rel": "stylesheet/css"},
    )
    assets.register("main_styles", style_bundle)
    style_bundle.build()
    js_bundle = Bundle("src/js/main.js", filters="jsmin", output="dist/js/main.min.js")
    assets.register("main_js", js_bundle)
    js_bundle.build()

    with app.app_context():
        from .db.models import Base, Release, Artist, Label, Genre, Review, Goal

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

        register_routes(app)

        @app.before_request
        def before_request():
            g.app_version = VERSION

        return app
