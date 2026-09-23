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
