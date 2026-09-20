"""
Serves the built SvelteKit SPA (frontend/build, copied into the Docker image
as frontend_build/). Local dev doesn't build the frontend into Flask's static
tree at all -- `pnpm dev`'s Vite server is used instead, proxying /api and
/img to Flask -- so this only ever serves real content inside the Docker
image, where `pnpm build` always runs first.
"""

from pathlib import Path
from flask import Blueprint, abort, send_from_directory, send_file

FRONTEND_BUILD_DIR = Path(__file__).resolve().parent.parent / "frontend_build"
FRONTEND_INDEX = FRONTEND_BUILD_DIR / "index.html"

spa_bp = Blueprint("spa_bp", __name__)


def serve_spa():
    if not FRONTEND_INDEX.is_file():
        abort(404)
    return send_file(FRONTEND_INDEX)


@spa_bp.route("/_app/<path:filename>")
def spa_asset(filename):
    return send_from_directory(FRONTEND_BUILD_DIR / "_app", filename)


@spa_bp.route("/robots.txt")
def spa_robots():
    return send_from_directory(FRONTEND_BUILD_DIR, "robots.txt")


@spa_bp.route("/", defaults={"path": ""})
@spa_bp.route("/<path:path>")
def spa_catch_all(path):
    return serve_spa()
