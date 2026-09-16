import traceback
from flask import Blueprint, render_template, request, get_flashed_messages, flash, redirect, jsonify
from werkzeug.exceptions import HTTPException
from .util import friendly_message

error_bp = Blueprint(
    'error_bp', __name__,
    template_folder='templates'
)

# TODO: make error handlers use the generic error.html template
@error_bp.errorhandler(405)
def method_not_allowed(e):
    data = {
        "method": request.method,
        "arguments": request.args,
        "url": request.url,
        "data": request.data,
        "error_full": e.description,
        "valid_methods": e.valid_methods
    }
    return render_template('errors/405.html', data=data), 405


@error_bp.errorhandler(404)
def not_found(e):
    data = {
        "method": request.method,
        "arguments": request.args,
        "url": request.url,
        "data": request.data,
        "error_full": e.description,
    }
    return render_template('errors/404.html', data=data), 404


@error_bp.errorhandler(415)
def unsupported_media_type(e):
    data = {
        "method": request.method,
        "arguments": request.args,
        "url": request.url,
        "data": request.data,
        "error_full": e.description,
    }
    return render_template('errors/415.html', data=data), 415


@error_bp.route('/error', methods=['GET'])
def error():
    error_message = get_flashed_messages()
    return render_template('error.html', error=error_message)


@error_bp.app_errorhandler(Exception)
def handle_uncaught_exception(e):
    """
    Last-resort safety net for any exception that a route didn't handle
    itself. Logs the full traceback server-side (so it's still debuggable)
    and shows the user a short, friendly message instead of a raw 500.
    """
    if isinstance(e, HTTPException):
        return e

    traceback.print_exc()
    message = friendly_message(e)
    if request.path.startswith('/api/'):
        return jsonify({"error": message}), 500
    flash(message)
    return redirect('/error')