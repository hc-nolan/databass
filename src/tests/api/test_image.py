from databass.api.image import get_art_candidates

CAA_CANDIDATES = [
    {
        "source": "caa",
        "url": "http://coverartarchive.org/release/rel-1/front",
        "thumb": "http://coverartarchive.org/release/rel-1/front-250",
        "label": "Front",
    }
]
DISCOGS_CANDIDATES = [
    {
        "source": "discogs",
        "url": "http://i.discogs.com/art.jpg",
        "thumb": "http://i.discogs.com/art-150.jpg",
        "label": "primary",
    }
]


class TestGetArtCandidates:
    """Tests for the get_art_candidates orchestration"""

    def test_combines_both_sources(self, mocker):
        mock_caa = mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            return_value=CAA_CANDIDATES,
        )
        mock_discogs = mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            return_value=DISCOGS_CANDIDATES,
        )

        result = get_art_candidates(
            release_group_mbid="rg-1",
            release_mbid="rel-1",
            release_name="Test Album",
            artist_name="Test Artist",
        )

        assert result == CAA_CANDIDATES + DISCOGS_CANDIDATES
        mock_caa.assert_called_once_with(
            release_group_mbid="rg-1", release_mbid="rel-1"
        )
        mock_discogs.assert_called_once_with(
            name="Test Album", artist="Test Artist"
        )

    def test_caa_failure_does_not_block_discogs(self, mocker):
        mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            side_effect=Exception("CAA down"),
        )
        mock_discogs = mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            return_value=DISCOGS_CANDIDATES,
        )

        result = get_art_candidates(
            release_group_mbid="rg-1", release_name="Test Album"
        )

        assert result == DISCOGS_CANDIDATES
        mock_discogs.assert_called_once()

    def test_discogs_failure_does_not_block_caa(self, mocker):
        mock_caa = mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            return_value=CAA_CANDIDATES,
        )
        mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            side_effect=Exception("Discogs rate limited"),
        )

        result = get_art_candidates(
            release_group_mbid="rg-1", release_name="Test Album"
        )

        assert result == CAA_CANDIDATES
        mock_caa.assert_called_once()

    def test_no_inputs_returns_empty(self):
        assert get_art_candidates() == []

    def test_skips_caa_without_mbid(self, mocker):
        mock_caa = mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            return_value=CAA_CANDIDATES,
        )
        mock_discogs = mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            return_value=DISCOGS_CANDIDATES,
        )

        result = get_art_candidates(release_name="Test Album", artist_name="Test Artist")

        assert result == DISCOGS_CANDIDATES
        mock_caa.assert_not_called()
        mock_discogs.assert_called_once()

    def test_skips_discogs_without_release_name(self, mocker):
        mock_caa = mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            return_value=CAA_CANDIDATES,
        )
        mock_discogs = mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            return_value=DISCOGS_CANDIDATES,
        )

        result = get_art_candidates(release_group_mbid="rg-1")

        assert result == CAA_CANDIDATES
        mock_caa.assert_called_once()
        mock_discogs.assert_not_called()

    def test_respects_total_limit(self, mocker):
        many_caa = [
            dict(CAA_CANDIDATES[0], url=f"http://coverartarchive.org/{i}")
            for i in range(30)
        ]
        mocker.patch(
            "databass.api.image.MusicBrainz.get_image_candidates",
            return_value=many_caa,
        )
        mocker.patch(
            "databass.api.image.Discogs.get_release_images",
            return_value=DISCOGS_CANDIDATES,
        )

        result = get_art_candidates(
            release_group_mbid="rg-1", release_name="Test Album"
        )

        assert len(result) == 10