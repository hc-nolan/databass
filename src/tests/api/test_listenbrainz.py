from databass.api.listenbrainz import ListenBrainz


def test_normalize_listen():
    result = ListenBrainz.normalize_listen(
        {
            "listened_at": 123,
            "track_metadata": {
                "artist_name": "Artist",
                "release_name": "Album",
                "track_name": "Track",
                "mbids": {
                    "artist_mbids": ["artist-id"],
                    "release_mbid": "release-id",
                    "release_group_mbid": "group-id",
                    "recording_mbid": "recording-id",
                },
            },
        }
    )
    assert result["artist_name"] == "Artist"
    assert result["release_group_mbid"] == "group-id"
    assert result["recording_mbid"] == "recording-id"


def test_fetch_listens_handles_empty_payload(mocker):
    mocker.patch.object(ListenBrainz, "_get", return_value=None)
    assert ListenBrainz.fetch_listens("test-user") == []


def test_normalize_listen_reads_mbid_mapping():
    """Newer payloads match IDs under `mbid_mapping`, not `mbids`."""
    result = ListenBrainz.normalize_listen(
        {
            "listened_at": 1,
            "track_metadata": {
                "artist_name": "X",
                "release_name": "Y",
                "track_name": "Z",
                "mbid_mapping": {
                    "artist_mbids": ["artist-id"],
                    "release_mbid": "release-id",
                    "recording_mbid": "recording-id",
                },
            },
        }
    )
    assert result["artist_mbid"] == "artist-id"
    assert result["release_mbid"] == "release-id"
    assert result["recording_mbid"] == "recording-id"


def test_get_retries_on_rate_limit(mocker):
    """A 429 should be retried (after the backoff) rather than raising."""
    rate_limited = mocker.Mock(status_code=429, headers={})
    ok = mocker.Mock(status_code=200)
    ok.json.return_value = {"ok": True}
    mocker.patch(
        "databass.api.listenbrainz.requests.get", side_effect=[rate_limited, ok]
    )
    mocker.patch.object(ListenBrainz, "_sleep_for_retry")
    assert ListenBrainz._get("/anything") == {"ok": True}


def test_get_retries_on_network_error(mocker):
    """A transient read timeout should be retried, not abort the import run."""
    import requests

    ok = mocker.Mock(status_code=200)
    ok.json.return_value = {"ok": True}
    mocker.patch(
        "databass.api.listenbrainz.requests.get",
        side_effect=[requests.exceptions.ReadTimeout("slow"), ok],
    )
    mocker.patch("databass.api.listenbrainz.time.sleep")
    assert ListenBrainz._get("/anything") == {"ok": True}
