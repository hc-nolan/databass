"""Tests for ListenBrainz listen import, catalog matching, and listen metrics."""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from databass import create_app
from databass.db.base import app_db
from databass.db.models import Artist, Genre, Label, Listen, Release, ScrobbledAlbum
from databass.listenbrainz_sync import (
    CatalogIndex,
    _import_batch,
    dedupe_key,
    relink_unmatched,
    sync_listens,
)


@pytest.fixture()
def app():
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture()
def seeded_app(app, monkeypatch):
    monkeypatch.setenv("LISTENBRAINZ_USERNAME", "tester")
    with app.app_context():
        _seed_library()
        yield app


def _seed_library():
    """Two artists with two releases each, so favourites' count>1 filter passes."""
    label = Label(name="Test Label", mbid="label-1")
    genre = Genre(name="rock")
    app_db.session.add_all([label, genre])
    app_db.session.commit()

    artist_a = Artist(name="Artist A", mbid="artist-a")
    artist_b = Artist(name="Artist B", mbid="artist-b")
    app_db.session.add_all([artist_a, artist_b])
    app_db.session.commit()

    releases = [
        Release(mbid="rel-a1", artist_id=artist_a.id, label_id=label.id, name="A One",
                year=2020, runtime=3000000, rating=90, listen_date=datetime(2024, 1, 1),
                track_count=10, main_genre_id=genre.id),
        Release(mbid="rel-a2", artist_id=artist_a.id, label_id=label.id, name="A Two",
                year=2021, runtime=3000000, rating=80, listen_date=datetime(2024, 2, 1),
                track_count=10, main_genre_id=genre.id),
        Release(mbid="rel-b1", artist_id=artist_b.id, label_id=label.id, name="B One",
                year=2020, runtime=3000000, rating=85, listen_date=datetime(2024, 3, 1),
                track_count=10, main_genre_id=genre.id),
        Release(mbid="rel-b2", artist_id=artist_b.id, label_id=label.id, name="B Two",
                year=2021, runtime=3000000, rating=85, listen_date=datetime(2024, 4, 1),
                track_count=10, main_genre_id=genre.id),
    ]
    app_db.session.add_all(releases)
    app_db.session.commit()


def _listen(**overrides):
    base = {
        "listened_at": 1_700_000_000,
        "track_name": "Track",
        "artist_name": "Artist A",
        "artist_mbid": "artist-a",
        "release_name": "A One",
        "release_mbid": "rel-a1",
        "release_group_mbid": None,
        "recording_mbid": "rec-1",
    }
    base.update(overrides)
    return base


class TestCatalogIndex:
    def test_resolves_exact_release_mbid(self, seeded_app):
        index = CatalogIndex()
        assert index.resolve_release(_listen()) is not None
        assert index.resolve_artist(_listen()) is not None

    def test_resolves_by_release_group_after_learning(self, seeded_app):
        index = CatalogIndex()
        # An exact MBID match seeds the group → release mapping ...
        first = _listen(release_mbid="rel-a1", release_group_mbid="rg-a1")
        release_id = index.resolve_release(first)
        index.learn(first, release_id)
        # ... so a different pressing of the same group links without an MBID hit.
        second = _listen(release_mbid="some-other-pressing", release_group_mbid="rg-a1",
                         release_name="A One (Deluxe)")
        assert index.resolve_release(second) == release_id

    def test_name_fallback_ignores_case_and_punctuation(self, seeded_app):
        index = CatalogIndex()
        fuzzy = _listen(release_mbid=None, release_group_mbid=None, release_name="a ONE!")
        assert index.resolve_release(fuzzy) == index.resolve_release(_listen())

    def test_unmatched_returns_none(self, seeded_app):
        index = CatalogIndex()
        assert index.resolve_release(_listen(release_mbid=None, release_name="Nothing Here")) is None
        assert index.resolve_artist(_listen(artist_mbid=None, artist_name="Nobody")) is None


class TestImportBatch:
    def test_import_is_idempotent(self, seeded_app):
        index = CatalogIndex()
        batch = [_listen(recording_mbid="rec-x", listened_at=1_700_000_000)]
        imported, _ = _import_batch(batch, index)
        assert imported == 1
        again, _ = _import_batch(batch, index)
        assert again == 0
        assert app_db.session.query(Listen).count() == 1

    def test_import_links_to_catalog(self, seeded_app):
        index = CatalogIndex()
        _import_batch([_listen(recording_mbid="rec-y", listened_at=1_700_000_100)], index)
        row = app_db.session.query(Listen).filter_by(recording_mbid="rec-y").one()
        assert row.release_id is not None
        assert row.artist_id is not None

    def test_relink_fills_listens_saved_before_release(self, seeded_app):
        index = CatalogIndex()
        # Import something that cannot match yet ...
        _import_batch(
            [_listen(release_mbid=None, release_group_mbid=None, release_name="Future Album",
                     artist_name="Future Artist", recording_mbid="rec-z", listened_at=1_700_000_200)],
            index,
        )
        row = app_db.session.query(Listen).filter_by(recording_mbid="rec-z").one()
        assert row.release_id is None

        # ... then log the release, and relink should connect it.
        genre = app_db.session.query(Genre).first()
        label = app_db.session.query(Label).first()
        artist = Artist(name="Future Artist")
        app_db.session.add(artist)
        app_db.session.commit()
        release = Release(mbid=None, artist_id=artist.id, label_id=label.id, name="Future Album",
                          year=2024, runtime=1, rating=70, listen_date=datetime(2024, 5, 1),
                          track_count=5, main_genre_id=genre.id)
        app_db.session.add(release)
        app_db.session.commit()

        assert relink_unmatched() >= 1
        app_db.session.refresh(row)
        assert row.release_id == release.id


class TestFavourites:
    def test_most_listened_ranks_by_scrobbles(self, seeded_app):
        artist_a = app_db.session.query(Artist).filter_by(name="Artist A").one()
        release_a1 = app_db.session.query(Release).filter_by(mbid="rel-a1").one()
        release_b1 = app_db.session.query(Release).filter_by(mbid="rel-b1").one()
        app_db.session.add_all(
            [Listen(listened_at=datetime(2024, 1, 1), dedupe_key=f"a{i}",
                    artist_id=artist_a.id, release_id=release_a1.id) for i in range(5)]
            + [Listen(listened_at=datetime(2024, 1, 1), dedupe_key="b0",
                      release_id=release_b1.id)]
        )
        app_db.session.commit()

        board = Artist.most_listened(limit=5)
        assert board[0]["name"] == "Artist A"
        assert board[0]["listens"] == 5

    def test_favourites_matches_bayesian_without_listens(self, seeded_app):
        plain = {item["name"]: item["rating"] for item in Artist.average_ratings_bayesian()}
        weighted = {item["name"]: item["rating"] for item in Artist.favourites()}
        assert weighted == plain

    def test_favourites_weights_heavy_listens(self, seeded_app):
        """Artist A's highly-rated release is played a lot; it should outrank B."""
        artist_a = app_db.session.query(Artist).filter_by(name="Artist A").one()
        release_a1 = app_db.session.query(Release).filter_by(mbid="rel-a1").one()
        app_db.session.add_all(
            [Listen(listened_at=datetime(2024, 1, 1), dedupe_key=f"a{i}",
                    artist_id=artist_a.id, release_id=release_a1.id) for i in range(20)]
        )
        app_db.session.commit()

        ranking = {item["name"]: item["rating"] for item in Artist.favourites()}
        assert ranking["Artist A"] > ranking["Artist B"]

    def test_favourites_matches_bayesian_with_fractional_averages(self, seeded_app):
        """Truncation parity: fractional averages must round the same as before."""
        artist = Artist(name="Fractional")
        app_db.session.add(artist)
        app_db.session.commit()
        genre = app_db.session.query(Genre).first()
        label = app_db.session.query(Label).first()
        for i, rating in enumerate([90, 85, 81]):
            app_db.session.add(
                Release(mbid=None, artist_id=artist.id, label_id=label.id, name=f"Frac {i}",
                        year=2020, runtime=1, rating=rating, listen_date=datetime(2024, 1, 1),
                        track_count=1, main_genre_id=genre.id)
            )
        app_db.session.commit()

        plain = {item["name"]: item["rating"] for item in Artist.average_ratings_bayesian()}
        weighted = {item["name"]: item["rating"] for item in Artist.favourites()}
        assert weighted == plain


class TestTodayWindow:
    def test_dst_spring_forward_day_is_23_hours(self):
        """The local day, not start+24h, bounds the 'today' window."""
        tz = ZoneInfo("America/Toronto")
        # 2026-03-08 is the US/Canada spring-forward date.
        now_local = datetime(2026, 3, 8, 12, 0, tzinfo=tz)
        start, end = Listen._day_window_utc(now_local, tz)
        assert start == datetime(2026, 3, 8, 5, 0)   # EST (UTC-5) midnight
        assert end == datetime(2026, 3, 9, 4, 0)     # EDT (UTC-4) next midnight
        assert end - start == timedelta(hours=23)


class TestDetailSurfaces:
    def test_release_detail_includes_lb_listens(self, seeded_app):
        from databass.detail import build_release_detail

        release = app_db.session.query(Release).filter_by(mbid="rel-a1").one()
        app_db.session.add(
            Listen(listened_at=datetime(2024, 1, 1), dedupe_key="d1", release_id=release.id)
        )
        app_db.session.commit()

        detail = build_release_detail(release)
        labels = [fact["label"] for fact in detail["facts"]]
        assert "LB LISTENS" in labels

    def test_artist_detail_omits_lb_listens_when_disabled(self, app, monkeypatch):
        from databass.detail import build_artist_detail

        monkeypatch.delenv("LISTENBRAINZ_USERNAME", raising=False)
        with app.app_context():
            _seed_library()
            artist = app_db.session.query(Artist).filter_by(name="Artist A").one()
            detail = build_artist_detail(artist)
            labels = [fact["label"] for fact in detail["facts"]]
            assert "LB LISTENS" not in labels


class TestSyncFlow:
    def test_backfill_then_incremental_dedupes(self, app, monkeypatch):
        monkeypatch.setenv("LISTENBRAINZ_USERNAME", "tester")
        with app.app_context():
            _seed_library()
            now = int(datetime.now(timezone.utc).timestamp())
            history = [
                _listen(listened_at=now - 200, recording_mbid="r1"),
                _listen(listened_at=now - 100, recording_mbid="r2"),
            ]

            def backfill_fetch(username, *, min_ts=None, max_ts=None, count=1000):
                return list(history) if (min_ts is None and max_ts is None) else []

            monkeypatch.setattr(
                "databass.listenbrainz_sync.ListenBrainz.fetch_listens", backfill_fetch
            )
            first = sync_listens()
            assert first["imported"] == 2
            assert first["backfill_done"] is True
            assert first["total"] == 2

            # The incremental fetch re-delivers the same listens; they must not
            # be stored twice.
            def incremental_fetch(username, *, min_ts=None, max_ts=None, count=1000):
                return list(history) if min_ts is not None else []

            monkeypatch.setattr(
                "databass.listenbrainz_sync.ListenBrainz.fetch_listens", incremental_fetch
            )
            second = sync_listens()
            assert second["imported"] == 0
            assert second["backfill_done"] is True

    def test_sync_skips_when_already_running(self, seeded_app):
        from databass import listenbrainz_sync as sync_mod

        with seeded_app.app_context():
            assert sync_mod._sync_lock.acquire(blocking=False)
            try:
                assert sync_mod.sync_listens().get("busy") is True
            finally:
                sync_mod._sync_lock.release()


class TestSyncCursor:
    def test_sync_no_username_returns_empty(self, app, monkeypatch):
        monkeypatch.delenv("LISTENBRAINZ_USERNAME", raising=False)
        with app.app_context():
            result = sync_listens()
            assert result["imported"] == 0
            assert result["backfill_done"] is False


class TestApiSurfaces:
    def test_home_reports_today_when_configured(self, seeded_app):
        release = app_db.session.query(Release).filter_by(mbid="rel-a1").one()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        app_db.session.add(
            Listen(listened_at=now, dedupe_key="today-1", release_id=release.id)
        )
        app_db.session.commit()
        client = seeded_app.test_client()
        payload = client.get("/api/home").get_json()
        assert payload["today"] is not None
        assert payload["today"]["listens"] == 1

    def test_home_today_null_when_disabled(self, app, monkeypatch):
        monkeypatch.delenv("LISTENBRAINZ_USERNAME", raising=False)
        with app.app_context():
            _seed_library()
        client = app.test_client()
        payload = client.get("/api/home").get_json()
        assert payload["today"] is None

    def test_stats_leaderboards_expose_favourites(self, seeded_app):
        client = seeded_app.test_client()
        boards = client.get("/api/stats/leaderboards/artists").get_json()["boards"]
        titles = [board["title"] for board in boards]
        assert "Favourites" in titles

    def test_sync_endpoint_returns_summary(self, seeded_app, monkeypatch):
        monkeypatch.setattr(
            "databass.routes.sync_listens",
            lambda *a, **k: {"imported": 3, "suggestions": 1, "backfill_done": False, "total": 3},
        )
        client = seeded_app.test_client()
        payload = client.post("/api/listenbrainz/sync").get_json()
        assert payload["imported"] == 3

    def test_logging_a_suggestion_creates_a_release(self, seeded_app, monkeypatch):
        """Regression: the log payload must use name/mbid, not release_name/mbid."""
        monkeypatch.setattr("databass.api.image.fetch_image", lambda **kwargs: None)
        with seeded_app.app_context():
            before = app_db.session.query(Release).filter_by(name="A One").count()
            row = ScrobbledAlbum(
                album_key="sug-1", artist_name="Artist A", artist_mbid="artist-a",
                release_name="A One", release_mbid=None, release_group_mbid=None,
                listened_at=datetime(2024, 6, 1), track_names=["t1", "t2", "t3"],
                status="pending",
            )
            app_db.session.add(row)
            app_db.session.commit()
            suggestion_id = row.id

        client = seeded_app.test_client()
        resp = client.post(
            f"/api/listenbrainz/suggestions/{suggestion_id}/log",
            json={"rating": 80, "main_genre": "rock"},
        )
        assert resp.status_code == 201, resp.get_json()
        with seeded_app.app_context():
            assert app_db.session.query(Release).filter_by(name="A One").count() == before + 1
            assert (
                app_db.session.query(ScrobbledAlbum).filter_by(id=suggestion_id).one().status
                == "logged"
            )

    def test_logging_a_suggestion_requires_a_genre(self, seeded_app):
        with seeded_app.app_context():
            row = ScrobbledAlbum(
                album_key="sug-2", artist_name="Artist A", release_name="A One",
                listened_at=datetime(2024, 6, 1), track_names=["t1"], status="pending",
            )
            app_db.session.add(row)
            app_db.session.commit()
            suggestion_id = row.id

        client = seeded_app.test_client()
        resp = client.post(
            f"/api/listenbrainz/suggestions/{suggestion_id}/log", json={"rating": 80}
        )
        assert resp.status_code == 400

