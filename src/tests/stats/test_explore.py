"""Tests for the stats "explore" query engine (databass.explore)."""

import pytest
from databass import create_app
from databass.db.base import app_db
from databass.db.models import Release, Artist, Label, Genre
from databass.explore import ExploreError, explore_options, run_query, validate_spec
from databass.db.models.associations import release_genre_association
from datetime import datetime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture()
def seeded_app(app):
    """App whose in-memory DB is seeded, kept inside an app context so direct
    ``run_query`` calls (which touch app_db.session) work."""
    with app.app_context():
        _seed_library()
        yield app


@pytest.fixture()
def seeded_client(app):
    """Test client whose DB is seeded (for the API-level tests)."""
    with app.app_context():
        _seed_library()
    with app.test_client() as client:
        yield client


def _seed_library():
    """A small library big enough to exercise the issue's example query.

    Artists:
      Arcade Fire  (CA, active 2001-)      - 3 releases
      Rush         (CA, active 1968-2015)  - 2 releases
      Daft Punk    (FR, active 1993-2021)  - 3 releases
      The Weeknd   (CA, active 2010-)      - 2 releases
    """
    arcade = Artist(name="Arcade Fire", country="CA", begin=datetime(2001, 1, 1).date(), end=None)
    rush = Artist(name="Rush", country="CA", begin=datetime(1968, 1, 1).date(), end=datetime(2015, 12, 31).date())
    daft = Artist(name="Daft Punk", country="FR", begin=datetime(1993, 1, 1).date(), end=datetime(2021, 2, 22).date())
    weeknd = Artist(name="The Weeknd", country="CA", begin=datetime(2010, 1, 1).date(), end=None)
    app_db.session.add_all([arcade, rush, daft, weeknd])

    modular = Label(name="Mercury Records", country="GB")
    anthem = Label(name="Anthem", country="CA")
    virgin = Label(name="Virgin", country="GB")
    xo = Label(name="XO", country="US")
    app_db.session.add_all([modular, anthem, virgin, xo])

    art_rock = Genre(name="Art Rock")
    prog_rock = Genre(name="Prog Rock")
    house = Genre(name="House")
    rnb = Genre(name="R&B")
    synth_pop = Genre(name="Synth-pop")
    app_db.session.add_all([art_rock, prog_rock, house, rnb, synth_pop])
    app_db.session.flush()

    def rel(name, artist, label, year, rating, listen, genre_id, country=None):
        r = Release(
            name=name,
            artist_id=artist.id,
            label_id=label.id,
            year=year,
            runtime=45 * 60000,
            rating=rating,
            listen_date=listen,
            track_count=10,
            main_genre_id=genre_id,
            country=country,
        )
        app_db.session.add(r)
        return r

    rel("Funeral", arcade, modular, 2004, 90, datetime(2022, 1, 5), art_rock.id, "CA")
    rel("Neon Bible", arcade, modular, 2007, 80, datetime(2023, 2, 10), art_rock.id, "CA")
    rel("The Suburbs", arcade, modular, 2010, 88, datetime(2024, 3, 15), art_rock.id, "CA")
    rel("Moving Pictures", rush, anthem, 1981, 92, datetime(2022, 4, 20), prog_rock.id, "CA")
    rel("2112", rush, anthem, 1976, 85, datetime(2023, 5, 25), prog_rock.id, "CA")
    rel("Homework", daft, virgin, 1997, 82, datetime(2022, 6, 30), house.id, "FR")
    rel("Discovery", daft, virgin, 2001, 88, datetime(2023, 7, 5), house.id, "FR")
    rel("Random Access Memories", daft, virgin, 2013, 86, datetime(2024, 8, 12), house.id, "FR")
    rel("House of Balloons", weeknd, xo, 2011, 93, datetime(2023, 9, 18), rnb.id, "CA")
    rel("Starboy", weeknd, xo, 2016, 78, datetime(2024, 10, 22), rnb.id, "CA")
    app_db.session.flush()

    # Give "Neon Bible" a subgenre matched only via the many-to-many table,
    # so the genre filter proves it reaches past main_genre_id.
    app_db.session.execute(
        release_genre_association.insert().values(
            release_id=(
                app_db.session.query(Release).filter(Release.name == "Neon Bible").first().id
            ),
            genre_id=synth_pop.id,
        )
    )
    app_db.session.commit()


# ---------------------------------------------------------------------------
# Spec validation
# ---------------------------------------------------------------------------


class TestValidateSpec:
    def test_rejects_empty(self):
        with pytest.raises(ExploreError):
            validate_spec({})

    def test_rejects_unknown_group_by(self):
        with pytest.raises(ExploreError):
            validate_spec({"group_by": "album"})

    def test_rejects_unknown_metric(self):
        with pytest.raises(ExploreError):
            validate_spec({"metric": "vibe"})

    def test_rejects_unknown_order(self):
        with pytest.raises(ExploreError):
            validate_spec({"order": "sideways"})

    def test_rejects_unknown_field(self):
        with pytest.raises(ExploreError):
            validate_spec({"filters": [{"field": "bogus", "op": "eq", "value": "x"}]})

    def test_rejects_bad_operator(self):
        with pytest.raises(ExploreError):
            validate_spec({"filters": [{"field": "artist_country", "op": "gte", "value": "CA"}]})

    def test_rejects_out_of_range_rating(self):
        with pytest.raises(ExploreError):
            validate_spec(
                {"filters": [{"field": "rating", "op": "gte", "value": 11}]}
            )

    def test_rejects_inverted_range(self):
        with pytest.raises(ExploreError):
            validate_spec(
                {"filters": [{"field": "rating", "op": "between", "value": [9, 5]}]}
            )

    def test_rejects_bad_years_overlap(self):
        with pytest.raises(ExploreError):
            validate_spec(
                {"filters": [{"field": "artist_active", "op": "overlaps", "value": [2004, 1995]}]}
            )

    def test_clamps_limit(self):
        assert validate_spec({"limit": 9999})["limit"] == 50
        assert validate_spec({"limit": -3})["limit"] == 1

    def test_clamps_min_items(self):
        assert validate_spec({"min_items": 0})["min_items"] == 1

    def test_normalizes_text_filter(self):
        spec = validate_spec(
            {"filters": [{"field": "artist_name", "op": "contains", "value": "  af "}]}
        )
        assert spec["filters"][0]["value"] == "af"

    def test_rejects_bool_as_integer(self):
        with pytest.raises(ExploreError):
            validate_spec(
                {"filters": [{"field": "rating", "op": "gte", "value": True}]}
            )
        with pytest.raises(ExploreError):
            validate_spec(
                {"filters": [{"field": "artist_active", "op": "overlaps", "value": [1995, True]}]}
            )
        with pytest.raises(ExploreError):
            validate_spec({"limit": True})

    def test_rejects_too_many_filters(self):
        many = [
            {"field": "genre", "op": "eq", "value": f"g{i}"} for i in range(21)
        ]
        with pytest.raises(ExploreError, match="Too many filters"):
            validate_spec({"filters": many})


# ---------------------------------------------------------------------------
# Query correctness
# ---------------------------------------------------------------------------


class TestRunQuery:
    def test_count_by_artist(self, seeded_app):
        res = run_query({"group_by": "artist", "metric": "count"})
        rows = {r["label"]: r for r in res["rows"]}
        assert res["meta"]["total_matched"] == 10
        assert rows["Arcade Fire"]["value"] == 3
        assert rows["Daft Punk"]["value"] == 3
        assert rows["The Weeknd"]["value"] == 2
        # top two are the 3-release artists
        assert res["rows"][0]["label"] in ("Arcade Fire", "Daft Punk")
        assert res["rows"][0]["href"].startswith("/artist/")
        assert res["rows"][0]["sub"] == "30% of matched"

    def test_min_items_filters_thin_groups(self, seeded_app):
        res = run_query({"group_by": "artist", "metric": "count", "min_items": 3})
        labels = {r["label"] for r in res["rows"]}
        assert labels == {"Arcade Fire", "Daft Punk"}

    def test_country_filter(self, seeded_app):
        res = run_query(
            {"group_by": "artist", "metric": "count",
             "filters": [{"field": "artist_country", "op": "eq", "value": "CA"}]}
        )
        assert res["meta"]["total_matched"] == 7
        assert {r["label"] for r in res["rows"]} == {"Arcade Fire", "Rush", "The Weeknd"}

    def test_issue_example_active_canada(self, seeded_app):
        """'Favourite artists from Canada active from 1995-2004'."""
        res = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [
                    {"field": "artist_country", "op": "eq", "value": "CA"},
                    {"field": "artist_active", "op": "overlaps", "value": [1995, 2004]},
                ],
            }
        )
        assert res["meta"]["total_matched"] == 5
        assert {r["label"] for r in res["rows"]} == {"Arcade Fire", "Rush"}

    def test_active_era_excludes_post_window(self, seeded_app):
        # The Weeknd starts in 2010, so is outside 1995-2004.
        res = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [{"field": "artist_active", "op": "overlaps", "value": [1995, 2004]}],
            }
        )
        assert {r["label"] for r in res["rows"]} == {"Arcade Fire", "Rush", "Daft Punk"}

    def test_active_era_includes_open_ended(self, seeded_app):
        # 2017-2020: Rush ended in 2015; open-ended begin 2001/2010 still overlap.
        res = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [{"field": "artist_active", "op": "overlaps", "value": [2017, 2020]}],
            }
        )
        assert {r["label"] for r in res["rows"]} == {"Arcade Fire", "Daft Punk", "The Weeknd"}

    def test_genre_filter_matches_main_and_subgenre(self, seeded_app):
        res = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [{"field": "genre", "op": "eq", "value": "House"}],
            }
        )
        assert res["meta"]["total_matched"] == 3
        assert {r["label"] for r in res["rows"]} == {"Daft Punk"}

        sub = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [{"field": "genre", "op": "eq", "value": "Synth-pop"}],
            }
        )
        # Only Neon Bible carries the Synth-pop subgenre (M2M), via Arcade Fire.
        assert sub["rows"][0]["label"] == "Arcade Fire"
        assert sub["rows"][0]["value"] == 1

    def test_release_year_range(self, seeded_app):
        res = run_query(
            {
                "group_by": "release_year",
                "metric": "count",
                "filters": [{"field": "release_year", "op": "between", "value": [2000, 2012]}],
            }
        )
        rows = {r["label"]: r["value"] for r in res["rows"]}
        assert rows["2004"] == 1
        assert rows["2010"] == 1
        assert rows["2011"] == 1
        assert "2013" not in rows  # RAM falls just outside the window

    def test_rating_threshold_scales_to_db(self, seeded_app):
        res = run_query(
            {
                "group_by": "artist",
                "metric": "count",
                "filters": [{"field": "rating", "op": "gte", "value": 9}],
            }
        )
        rows = {r["label"]: r["value"] for r in res["rows"]}
        # 90 (Funeral), 92 (Moving Pictures), 93 (House of Balloons)
        assert rows == {"Arcade Fire": 1, "Rush": 1, "The Weeknd": 1}

    def test_listen_year_filter(self, seeded_app):
        res = run_query(
            {
                "group_by": "release_year",
                "metric": "count",
                "filters": [{"field": "listen_year", "op": "between", "value": [2022, 2022]}],
            }
        )
        assert res["meta"]["total_matched"] == 3

    def test_group_by_release_decade(self, seeded_app):
        res = run_query({"group_by": "release_decade", "metric": "count"})
        rows = {r["label"]: r["value"] for r in res["rows"]}
        assert rows["2000s"] == 3  # Funeral, Neon Bible, Discovery
        assert rows["2010s"] == 4  # The Suburbs, House of Balloons, RAM, Starboy
        assert rows["1980s"] == 1

    def test_group_by_listen_month(self, seeded_app):
        res = run_query({"group_by": "listen_month", "metric": "count"})
        rows = {r["label"]: r["value"] for r in res["rows"]}
        assert rows["JAN"] == 1
        assert rows["FEB"] == 1

    def test_group_by_genre(self, seeded_app):
        res = run_query({"group_by": "genre", "metric": "count"})
        rows = {r["label"]: r["value"] for r in res["rows"]}
        assert rows["Art Rock"] == 3
        assert rows["R&B"] == 2

    def test_group_by_label(self, seeded_app):
        res = run_query({"group_by": "label", "metric": "count"})
        rows = {r["label"]: r["value"] for r in res["rows"]}
        assert rows["Virgin"] == 3
        assert rows["Anthem"] == 2

    def test_avg_rating_metric(self, seeded_app):
        res = run_query({"group_by": "artist", "metric": "avg_rating", "order": "desc"})
        by_label = {r["label"]: r for r in res["rows"]}
        assert res["rows"][0]["label"] == "Rush"  # avg 88.5
        assert by_label["Arcade Fire"]["value"] == 8.6
        assert by_label["The Weeknd"]["display"] == "8.6 / 10"

    def test_runtime_metric(self, seeded_app):
        res = run_query({"group_by": "artist", "metric": "runtime_hours"})
        by_label = {r["label"]: r for r in res["rows"]}
        assert by_label["Arcade Fire"]["value"] == 2.2  # 3 x 45min = 2.25h, round-half-even
        # 3 x 45min = 2.25h -> "2h 15m", not the old "2m"
        assert by_label["Arcade Fire"]["display"] == "2h 15m"


class TestRunQueryBayes:
    def test_favourites_bayesian(self, seeded_app):
        res = run_query(
            {"group_by": "artist", "metric": "bayes_rating", "min_items": 2}
        )
        labels = [r["label"] for r in res["rows"]]
        assert len(labels) == 4
        assert labels[0] == "Rush"  # small, high average scores best
        assert all(r["href"].startswith("/artist/") for r in res["rows"])

    def test_bayes_with_filter(self, seeded_app):
        res = run_query(
            {
                "group_by": "artist",
                "metric": "bayes_rating",
                "min_items": 1,
                "filters": [{"field": "artist_country", "op": "eq", "value": "CA"}],
            }
        )
        labels = {r["label"] for r in res["rows"]}
        assert labels == {"Arcade Fire", "Rush", "The Weeknd"}


class TestHardening:
    """Empty-library smoke test and meta honesty."""

    def test_empty_library(self, app):
        with app.app_context():
            res = run_query({"group_by": "artist", "metric": "count"})
            assert res["rows"] == []
            assert res["meta"]["total_matched"] == 0
            options = explore_options()
            assert options["defaults"]["metric"] == "bayes_rating"

    def test_total_groups_counts_before_limit(self, seeded_app):
        res = run_query({"group_by": "artist", "metric": "count", "limit": 2})
        assert len(res["rows"]) == 2
        assert res["meta"]["total_groups"] == 4  # all four seeded artists


def _seed_tiny_library():
    """A two-release library used for bucket/placeholder edge cases."""
    artist = Artist(name="Real Artist", country="US")
    label = Label(name="Real Label", country="US")
    genre = Genre(name="Rock")
    app_db.session.add_all([artist, label, genre])
    app_db.session.flush()

    def rel(name, artist_id, label_id, rating):
        app_db.session.add(
            Release(
                name=name,
                artist_id=artist_id,
                label_id=label_id,
                year=2000,
                runtime=45 * 60000,
                rating=rating,
                listen_date=datetime(2022, 1, 1),
                track_count=10,
                main_genre_id=genre.id,
            )
        )

    rel("Perfect", artist.id, label.id, 100)
    rel("High", artist.id, label.id, 95)
    rel("Mid", artist.id, label.id, 60)
    # Unknown is the id-0 placeholder entity created by ensure_db_placeholders.
    rel("Mystery", 0, 0, 70)
    app_db.session.commit()


class TestBucketAndPlaceholder:
    def test_rating_100_bucket_capped_at_10(self, app):
        with app.app_context():
            _seed_tiny_library()
            res = run_query({"group_by": "rating_bucket", "metric": "count"})
            rows = {r["label"]: r["value"] for r in res["rows"]}
            assert "11" not in rows
            assert rows.get("10") == 2  # ratings 95 and 100
            assert rows.get("7") == 1  # rating 60

    def test_unknown_placeholder_excluded_from_grouping(self, app):
        with app.app_context():
            _seed_tiny_library()
            res = run_query({"group_by": "artist", "metric": "count"})
            labels = {r["label"]: r["value"] for r in res["rows"]}
            assert "Unknown" not in labels
            # The placeholder release is filtered from grouping, but the real
            # artist still owns three releases (100, 95, 60 ratings).
            assert labels == {"Real Artist": 3}

    def test_unknown_placeholder_excluded_from_label_grouping(self, app):
        with app.app_context():
            _seed_tiny_library()
            res = run_query({"group_by": "label", "metric": "count"})
            labels = {r["label"]: r["value"] for r in res["rows"]}
            assert "Unknown" not in labels
            assert labels == {"Real Label": 3}


def _seed_country_junk():
    """Artists (and matching releases) with junk or legit country values."""
    label = Label(name="Country Label", country="CA")
    genre = Genre(name="Rock")
    artists = [
        Artist(name="Legit Artist", country="CA"),
        Artist(name="Question Artist", country="?"),
        Artist(name="Dash Artist", country="—"),
        Artist(name="XW Artist", country="XW"),
        Artist(name="None Artist", country="None"),
    ]
    app_db.session.add(label)
    app_db.session.add(genre)
    app_db.session.add_all(artists)
    app_db.session.flush()
    for artist in artists:
        app_db.session.add(
            Release(
                name=f"R-{artist.name}",
                artist_id=artist.id,
                label_id=label.id,
                year=2000,
                runtime=45 * 60000,
                rating=70,
                listen_date=datetime(2022, 1, 1),
                track_count=10,
                main_genre_id=genre.id,
                country=artist.country,
            )
        )
    app_db.session.commit()


class TestCountryCleanup:
    """Nonexistent country values ('?', '—', 'XW', 'None') don't leak onto the page."""

    def test_junk_countries_excluded_from_options(self, app):
        with app.app_context():
            _seed_country_junk()
            data = explore_options()
            assert [c for c, _ in data["options"]["artist_countries"]] == ["CA"]
            assert [c for c, _ in data["options"]["release_countries"]] == ["CA"]
            assert [c for c, _ in data["options"]["label_countries"]] == ["CA"]

    def test_junk_artist_countries_excluded_from_grouping(self, app):
        with app.app_context():
            _seed_country_junk()
            res = run_query({"group_by": "artist_country", "metric": "count"})
            rows = {r["label"]: r["value"] for r in res["rows"]}
            assert rows == {"Canada": 1}

    def test_junk_release_countries_excluded_from_grouping(self, app):
        with app.app_context():
            _seed_country_junk()
            res = run_query({"group_by": "release_country", "metric": "count"})
            rows = {r["label"]: r["value"] for r in res["rows"]}
            assert rows == {"Canada": 1}

    def test_legit_country_filter_still_matches(self, app):
        with app.app_context():
            _seed_country_junk()
            res = run_query(
                {
                    "group_by": "artist",
                    "metric": "count",
                    "filters": [{"field": "artist_country", "op": "eq", "value": "CA"}],
                }
            )
            assert {r["label"] for r in res["rows"]} == {"Legit Artist"}


class TestApiExplore:
    def test_options_payload(self, client):
        res = client.get("/api/explore/options")
        assert res.status_code == 200
        data = res.get_json()
        assert {f["value"] for f in data["fields"]} >= {"artist_country", "genre", "rating"}
        assert "artist_countries" in data["options"]
        assert "group_bys" in data
        assert "metrics" in data
        assert data["bounds"]["rating"] == [1, 10]

    def test_run_query_endpoint(self, seeded_client):
        res = seeded_client.post("/api/explore", json={"group_by": "genre", "metric": "count"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["meta"]["total_matched"] == 10
        assert {r["label"] for r in data["rows"]} >= {"House", "Art Rock"}

    def test_bad_spec_rejected(self, seeded_client):
        res = seeded_client.post("/api/explore", json={"group_by": "not-a-thing"})
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_empty_payload_rejected(self, seeded_client):
        res = seeded_client.post("/api/explore", json={})
        assert res.status_code == 400