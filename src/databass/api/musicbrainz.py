from os import getenv
from dateutil import parser as dateparser
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import musicbrainzngs as mbz
import musicbrainzngs.musicbrainz
from .util import Util
from .types import ArtistInfo, LabelInfo, ReleaseInfo, EntityInfo, SearchResult

load_dotenv()
VERSION = getenv("VERSION")


class MbzParser:
    @staticmethod
    def parse_label_info(r: dict) -> dict:
        """
        Parse MusicBrainz release search results into dict with keys `mbid` and `name`
        representing label info
        """
        labelinfo_list = r.get("label-info-list")
        try:
            labelinfo = labelinfo_list[0].get("label", {})
        except (AttributeError, TypeError, IndexError):
            labelinfo = {}
            label_id = ""
            label_name = ""

        label_id = labelinfo.get("id")
        label_name = labelinfo.get("name")

        return {"mbid": label_id, "name": label_name}

    @staticmethod
    def parse_artist_info(r: dict) -> dict:
        """
        Parse MusicBrainz release search results into dict with keys `mbid` and `name`
        representing artist info
        """
        try:
            artist_info = r.get("artist-credit")[0]
            artist_name = artist_info.get("name")
            artist_mbid = artist_info.get("artist")["id"]
        except (AttributeError, TypeError, IndexError):
            artist_info = {}
            artist_name = ""
            artist_mbid = ""
        return {"mbid": artist_mbid, "name": artist_name}

    @staticmethod
    def parse_date(r: dict) -> str:
        try:
            raw_date = r.get("date")
            date = dateparser.parse(raw_date, fuzzy=True).year
        except Exception:
            date = ""
        return date

    @staticmethod
    def parse_format(r: dict) -> str:
        try:
            physical_release = r.get("medium-list", [])[0]
            fmt = physical_release.get("format")
        except (TypeError, IndexError):
            fmt = ""
        return fmt

    @staticmethod
    def parse_track_count(r: dict) -> int:
        track_count = 0
        try:
            for disc in r.get("medium-list", []):
                track_count += disc.get("track-count")
        except IndexError:
            track_count = 0
        return track_count

    @staticmethod
    def parse(r: dict) -> ReleaseInfo:
        """
        Parse all release information from MusicBrainz search results
        """
        label = MbzParser.parse_label_info(r)
        date = MbzParser.parse_date(r)
        release_format = MbzParser.parse_format(r)
        track_count = MbzParser.parse_track_count(r)
        country = r.get("country")
        release_id = r.get("id")
        release_name = r.get("title")

        artist = MbzParser.parse_artist_info(r)
        return ReleaseInfo(
            release={"name": release_name, "mbid": release_id},
            artist=artist,
            label=label,
            date=date,
            format=release_format,
            track_count=track_count,
            country=country,
            release_group_id=r.get("release-group")["id"],
        )

    @staticmethod
    def parse_search_result(search_result: SearchResult) -> EntityInfo:
        """
        Parse a search result from the MusicBrainz API into a dictionary with the following keys:
        - name: The name of the item (e.g. label, artist)
        - mbid: The MusicBrainz ID of the item
        - begin: The start date of the item, as a datetime object or None if not available
        - end: The end date of the item, as a datetime object or None if not available
        - country: The country of the item, or None if not available
        - type: The type of the item (e.g. "Label", "Artist"), or None if not available

        Args:
            search_result (dict): The raw search result dictionary from the MusicBrainz API.

        Returns:
            dict: A dictionary containing the parsed information about the item.
        """
        if not isinstance(search_result, dict) or not search_result:
            raise ValueError("Invalid or empty search result passed to the function")

        country = search_result.get("country")
        item_type = search_result.get("type")
        lifespan = search_result.get("life_span", {})

        begin_raw = lifespan.get("begin")
        end_raw = lifespan.get("end")
        begin = Util.to_date("begin", begin_raw)
        begin = Util.to_date("begin", begin_raw)
        end = Util.to_date("end", end_raw)

        item = EntityInfo(
            name=search_result["name"],
            mbid=search_result["id"],
            begin=begin,
            end=end,
            country=country,
            type=item_type,
        )
        return item


class MusicBrainz:
    init = False

    @classmethod
    def initialize(cls):
        if not cls.init:
            mbz.set_useragent(
                "Databass", f"v{VERSION}", contact="https://github.com/chunned/databass"
            )
            cls.init = True

    @staticmethod
    def release_search(
        release: str = None, artist: str = None, label: str = None
    ) -> list[ReleaseInfo]:
        """
        Performs a search for music releases on the MusicBrainz API.

        Args:
            release (str, optional): The release name to search for.
            artist (str, optional): The artist name to search for.
            label (str, optional): The label name to search for.

        Returns:
            list[ReleaseInfo]: A list of `ReleaseInfo` objects representing the search results, or `None` if no results were found.
        """  # noqa
        if not MusicBrainz.init:
            MusicBrainz.initialize()

        if all(search_term is None for search_term in (release, artist, label)):
            raise ValueError("At least one query term is required")
        results = mbz.search_releases(artist=artist, label=label, release=release)
        search_data = []  # Will hold the main return data
        for r in results.get("release-list"):
            release_info = MbzParser.parse(r)
            search_data.append(release_info)
        return search_data

    @staticmethod
    def label_search(name: str, mbid: Optional[str] = None) -> Optional[LabelInfo]:
        """
        Search MusicBrainz for a label matching the given name or MusicBrainz ID (MBID).

        Args:
            name (str): The name of the label to search for.
            mbid (str, optional): The MusicBrainz ID of the label, if known. If provided, the function will attempt to directly query the label by ID instead of searching.

        Returns:
            Optional[LabelInfo]: A `LabelInfo` object containing the parsed information about the label, or `None` if the search fails.
        """  # noqa
        if not name or not isinstance(name, str):
            return None
        if not MusicBrainz.init:
            MusicBrainz.initialize()

        if mbid is not None:
            # If we have MBID, we can query the label directly
            label_result = mbz.get_label_by_id(mbid, includes=["area-rels"])["label"]
            label = MbzParser.parse_search_result(label_result)
            return label

        # No MBID, have to search. Assume first result is correct
        label_results = mbz.search_labels(query=name)
        label_list = label_results.get("label-list")
        try:
            label_id = label_list[0]["id"]
            # Now that we have an MBID, call this function using that ID
            # This call is required because begin_date/end_date are not included in search results
            return MusicBrainz.label_search(name=name, mbid=label_id)
        except (IndexError, TypeError):
            return None

    @staticmethod
    def artist_search(name: str, mbid: Optional[str] = None) -> Optional[ArtistInfo]:
        """
        Search MusicBrainz for artists matching the search terms.

        Args:
            name (str): The name of the artist to search for.
            mbid (str, optional): The MusicBrainz ID of the artist, if known. If provided, the function will attempt to directly query the artist by ID instead of searching.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the parsed information about the artist, or None if the search fails.
        """
        if not name or not isinstance(name, str):
            return None
        if not MusicBrainz.init:
            MusicBrainz.initialize()
        if mbid is not None:
            # If we have MBID, we can query the label directly
            try:
                artist_result = mbz.get_artist_by_id(mbid, includes=["area-rels"])[
                    "artist"
                ]
            except Exception:
                return None
            artist = MbzParser.parse_search_result(artist_result)
            return artist
        # No MBID, have to search. Assume first result is correct
        artist_results = mbz.search_artists(query=name)
        artist_list = artist_results.get("artist-list")
        try:
            artist_id = artist_list[0]["id"]
            # Now that we have a MBID, call this function using that ID
            # This call is required because begin_date/end_date are not included in search results
            return MusicBrainz.artist_search(name=name, mbid=artist_id)
        except (TypeError, IndexError):
            return None

    @staticmethod
    def get_release_length(mbid: str) -> int:
        """
        Get the total length of a release on MusicBrainz in milliseconds.

        Args:
            mbid (str): The MBID (MusicBrainz ID) of the release.

        Returns:
            int: The total length of the release in milliseconds, or 0 if the length could not be determined.
        """
        if not mbid or not isinstance(mbid, str):
            return 0
        if not MusicBrainz.init:
            MusicBrainz.initialize()

        try:
            release_data = mbz.get_release_by_id(
                mbid, includes=["recordings", "media", "recording-level-rels"]
            )
            track_data = release_data.get("release")
            discs = track_data.get("medium-list")
            length = 0
            for disc in discs:
                tracks = disc.get("track-list")
                for track in tracks:
                    try:
                        track_len = track.get("length")
                        length += int(track_len)
                    except (KeyError, TypeError):
                        pass

            return length
        except Exception:
            return 0

    @staticmethod
    def get_image(mbid: str, size: str = "250") -> Optional[bytes]:
        """
        Search for the front cover image of a release group on MusicBrainz and return it as bytes, or return None if no image is found.

        Args:
            mbid (str): The MBID (MusicBrainz ID) of the release group.
            size (str): Desired size of the image in pixels, 250px by default

        Returns:
            Optional[bytes]: The front cover image of the release group as bytes, or None if no image is found.
        """
        if not size.isdigit():
            return None
        if not mbid or not isinstance(mbid, str):
            return None

        try:
            return mbz.get_release_group_image_front(mbid, size=size)
        except musicbrainzngs.musicbrainz.ResponseError:
            covers: Dict[str, Any] = mbz.get_image_list(mbid)
            coverid = MusicBrainz._get_first_cover_id(covers)
            if coverid:
                return mbz.get_image(mbid, coverid=coverid, size=size)
            return None
        except Exception:
            return None

    @staticmethod
    def _get_first_cover_id(covers: list) -> Optional[str]:
        """Retrieve the MBID of the first element in the list, or None"""
        if not covers:
            return None

        imgs = covers.get("images", [])
        return imgs[0].get("id") if imgs else None
