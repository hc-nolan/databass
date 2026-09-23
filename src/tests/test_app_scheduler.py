"""Tests for the optional ListenBrainz background scheduler startup."""

from databass import _scheduler_should_start, create_app


def _app(debug: bool):
    application = create_app()
    application.debug = debug
    return application


def test_scheduler_runs_under_gunicorn_docker(monkeypatch):
    """Production sets DOCKER; Config.DEBUG is always True, so this must win."""
    monkeypatch.setenv("DOCKER", "True")
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    assert _scheduler_should_start(_app(debug=True)) is True


def test_scheduler_runs_in_reloader_child(monkeypatch):
    monkeypatch.delenv("DOCKER", raising=False)
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    assert _scheduler_should_start(_app(debug=True)) is True


def test_scheduler_skips_reloader_parent(monkeypatch):
    monkeypatch.delenv("DOCKER", raising=False)
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    assert _scheduler_should_start(_app(debug=True)) is False


def test_scheduler_runs_without_debug(monkeypatch):
    monkeypatch.delenv("DOCKER", raising=False)
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    assert _scheduler_should_start(_app(debug=False)) is True


def test_scheduler_never_starts_under_testing(monkeypatch):
    monkeypatch.setenv("DOCKER", "True")
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "tester")
    app = _app(debug=True)
    from databass import _start_listenbrainz_scheduler

    _start_listenbrainz_scheduler(app, is_testing=True)
    assert "listenbrainz_scheduler" not in app.extensions
