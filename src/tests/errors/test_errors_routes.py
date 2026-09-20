import pytest
from databass import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def client(app):
    with app.test_client() as client:
        yield client


class TestUncaughtExceptionHandler:
    def test_uncaught_exception_on_api_route_returns_json_500(self, client, mocker):
        mocker.patch(
            "databass.db.models.Goal.get_incomplete", side_effect=RuntimeError("boom")
        )
        response = client.get("/api/home")
        assert response.status_code == 500
        assert response.get_json()["error"] == "boom"

    def test_404_when_no_frontend_build_present(self, client):
        """
        Catch-all route falls back to a plain 404 when the SvelteKit build
        (frontend_build/) isn't present -- the case in test/CI environments,
        which never run `pnpm build`.
        """
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404
