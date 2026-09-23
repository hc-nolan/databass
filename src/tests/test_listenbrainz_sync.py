from databass.listenbrainz_sync import detect_album_listens


def test_detects_three_distinct_tracks_as_album():
    listens = [
        {"listened_at": 100, "release_name": "Album", "artist_name": "Artist", "track_name": "One"},
        {"listened_at": 200, "release_name": "Album", "artist_name": "Artist", "track_name": "Two"},
        {"listened_at": 300, "release_name": "Album", "artist_name": "Artist", "track_name": "Three"},
    ]
    result = detect_album_listens(listens)
    assert len(result) == 1
    assert result[0]["track_names"] == ["One", "Two", "Three"]


def test_splits_album_after_long_gap():
    listens = [
        {"listened_at": 100, "release_name": "Album", "artist_name": "Artist", "track_name": "One"},
        {"listened_at": 101, "release_name": "Album", "artist_name": "Artist", "track_name": "Two"},
        {"listened_at": 102, "release_name": "Album", "artist_name": "Artist", "track_name": "Three"},
        {"listened_at": 10000, "release_name": "Album", "artist_name": "Artist", "track_name": "Four"},
    ]
    assert len(detect_album_listens(listens)) == 1
