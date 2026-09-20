import traceback
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import HTTPException
from .util import friendly_message

error_bp = Blueprint("error_bp", __name__)


@error_bp.app_errorhandler(Exception)
def handle_uncaught_exception(e):
    """
    Last-resort safety net for any exception that a route didn't handle
    itself. Logs the full traceback server-side (so it's still debuggable)
    and returns a JSON error for API routes instead of a raw 500. Non-API
    routes (the SPA shell) don't run any server-side logic that could throw,
    so this realistically only fires for /api/*.
    """
    if isinstance(e, HTTPException):
        return e

    traceback.print_exc()
    message = friendly_message(e)
    status = 500
    if request.path.startswith("/api/"):
        return jsonify({"error": message}), status
    return message, status
