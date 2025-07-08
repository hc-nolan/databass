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
    ) -> Optional[list[ReleaseInfo]]:
        """
        Performs a search for music releases on the MusicBrainz API.

        Args:
            release (str, optional): The release name to search for.
            artist (str, optional): The artist name to search for.
            label (str, optional): The label name to search for.

        Returns:
            Optional[list[ReleaseInfo]]: A list of `ReleaseInfo` objects representing the search results, or `None` if no results were found.
        """
        if MusicBrainz.init:
            if all(search_term is None for search_term in (release, artist, label)):
                raise ValueError("At least one query term is required")
            results = mbz.search_releases(artist=artist, label=label, release=release)
            search_data = []  # Will hold the main return data
            for r in results["release-list"]:
                # Parse label data
                try:
                    labelinfo = r["label-info-list"][0]["label"]
                    try:
                        label_id = labelinfo["id"]
                    except KeyError:
                        label_id = ""
                    try:
                        label_name = labelinfo["name"]
                    except KeyError:
                        label_name = ""
                except (KeyError, IndexError):
                    # No label info found; continue with empty label data
                    label_id = ""
                    label_name = ""
                label = {"mbid": label_id, "name": label_name}
                try:
                    raw_date = r["date"]
                    date = dateparser.parse(raw_date, fuzzy=True).year
                except (KeyError, dateparser.ParserError):
                    date = ""
                try:
                    physical_release = r["medium-list"][0]
                    try:
                        release_format = physical_release["format"]
                    except KeyError:
                        release_format = ""
                    try:
                        track_count = 0
                        for disc in r["medium-list"]:
                            track_count += disc["track-count"]
                    except KeyError:
                        track_count = ""
                except (KeyError, IndexError):
                    release_format = ""
                    track_count = ""
                try:
                    country = r["country"]
                except KeyError:
                    country = ""

                release_id = r["id"]

                rel = ReleaseInfo(
                    release={"name": r["title"], "mbid": release_id},
                    artist={
                        "name": r["artist-credit"][0]["name"],
                        "mbid": r["artist-credit"][0]["artist"]["id"],
                    },
                    label=label,
                    date=date,
                    format=release_format,
                    track_count=track_count,
                    country=country,
                    release_group_id=r["release-group"]["id"],
                )
                search_data.append(rel)
            return search_data
        try:
            MusicBrainz.initialize()
            return MusicBrainz.release_search(release, artist, label)
        except RecursionError:
            return None

    @staticmethod
    def label_search(name: str, mbid: str = None) -> Optional[LabelInfo]:
        """
        Search MusicBrainz for a label matching the given name or MusicBrainz ID (MBID).

        Args:
            name (str): The name of the label to search for.
            mbid (str, optional): The MusicBrainz ID of the label, if known. If provided, the function will attempt to directly query the label by ID instead of searching.

        Returns:
            Optional[LabelInfo]: A `LabelInfo` object containing the parsed information about the label, or `None` if the search fails.
        """
        if not name or not isinstance(name, str):
            return None
        if MusicBrainz.init:
            if mbid is not None:
                try:
                    # If we have MBID, we can query the label directly
                    label_result = mbz.get_label_by_id(mbid, includes=["area-rels"])[
                        "label"
                    ]
                    label = MusicBrainz.parse_search_result(label_result)
                    return label
                except Exception as e:
                    raise e
            else:
                # No MBID, have to search. Assume first result is correct
                label_results = mbz.search_labels(query=name)
                try:
                    label_id = label_results["label-list"][0]["id"]
                    # Now that we have an MBID, recursively call this function using that ID to grab the label data
                    # This call is required because begin_date/end_date are not included in search results
                    return MusicBrainz.label_search(name=name, mbid=label_id)
                except (KeyError, IndexError):
                    return None
        else:
            # MusicBrainz class not initialized; call initialize function, then re-call function
            try:
                MusicBrainz.initialize()
                return MusicBrainz.label_search(name, mbid)
            except RecursionError:
                return None

    @staticmethod
    def artist_search(name: str, mbid: str = None) -> Optional[ArtistInfo]:
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
        if MusicBrainz.init:
            if mbid is not None:
                try:
                    # If we have MBID, we can query the label directly
                    artist_result = mbz.get_artist_by_id(mbid, includes=["area-rels"])[
                        "artist"
                    ]
                    artist = MusicBrainz.parse_search_result(artist_result)
                    return artist
                except KeyError:
                    return None
            else:
                # No MBID, have to search. Assume first result is correct
                artist_results = mbz.search_artists(query=name)
                try:
                    artist_id = artist_results["artist-list"][0]["id"]
                    # Now that we have an MBID, recursively call this function using that ID to grab the label data
                    # This call is required because begin_date/end_date are not included in search results
                    return MusicBrainz.artist_search(name=name, mbid=artist_id)
                except (KeyError, IndexError):
                    return None
        else:
            # MusicBrainz class not initialized; call initialize function, then re-call function
            try:
                MusicBrainz.initialize()
                return MusicBrainz.artist_search(name, mbid)
            except RecursionError:
                return None

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
        try:
            # Try to get the label's creation date
            begin_raw = search_result["life_span"]["begin"]
        except KeyError:
            begin_raw = None
        try:
            # Try to get the label's end date
            end_raw = search_result["life_span"]["end"]
        except KeyError:
            end_raw = None
            # Parse from string to datetime
        begin = Util.to_date("begin", begin_raw)
        end = Util.to_date("end", end_raw)

        try:
            country = search_result["country"]
        except KeyError:
            country = None

        try:
            item_type = search_result["type"]
        except KeyError:
            item_type = None

        item = EntityInfo(
            name=search_result["name"],
            mbid=search_result["id"],
            begin=begin,
            end=end,
            country=country,
            type=item_type,
        )
        return item

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
            try:
                MusicBrainz.initialize()
            except RecursionError:
                return 0

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
            try:
                covers: Dict[str, Any] = mbz.get_image_list(mbid)
                if covers:
                    try:
                        coverid = covers["images"][0]["id"]
                        return mbz.get_image(mbid, coverid=coverid, size=size)
                    except (KeyError, IndexError):
                        pass
            except musicbrainzngs.musicbrainz.ResponseError:
                return None
        except Exception:
            return None
