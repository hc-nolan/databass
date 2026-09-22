"""
Implements Discogs API-related functions via Discogs class methods
"""

from os import getenv
from typing import Dict, Optional, Any, Literal
from urllib.parse import urljoin, urlencode
import time
import re
import requests
from dotenv import load_dotenv


load_dotenv()
DISCOGS_KEY = getenv("DISCOGS_KEY")
DISCOGS_SECRET = getenv("DISCOGS_SECRET")
VERSION = getenv("VERSION")
RATE_LIMIT_THRESHOLD: float = 1.1
DIMENSIONS_PATTERN = r"/h:\d+/w:\d+/"
HEIGHT_PATTERN = r"/h:(\d+)/.*"
WIDTH_PATTERN = r".*/w:(\d+)/.*"
DISAMBIG_PATTERN = r"\s*\(\d+\)\s*$"
FORBIDDEN_FORMATS = ["Blu-ray"]

valid_entity_types = Literal["release", "artist", "label"]


class Discogs:
    """
    Discogs API client class
    Attributes:
        url (str): The base URL for the Discogs API
        headers (dict): The headers to use for the requests
        remaining_requests (int): The number of remaining requests
    """

    url: str = "https://api.discogs.com"
    headers: Dict[str, str] = {
        "User-Agent": f"Databass/{VERSION} +https://github.com/chunned/databass",
        "Authorization": f"Discogs key={DISCOGS_KEY}, secret={DISCOGS_SECRET}",
    }
    remaining_requests: Optional[int] = None

    @classmethod
    def update_rate_limit(cls, response: requests.Response):
        """
        Updates rate limit remaining requests based on response header
        """
        limit = response.headers.get("x-discogs-ratelimit-remaining")
        cls.remaining_requests = int(limit)

    @classmethod
    def is_throttled(cls) -> bool:
        """
        Checks if we have enough remaining requests to make new request per rate limiting guidelines
        If remaining_requests is None, no requests have been sent yet and thus we are not throttled
        If we have 1.1 or fewer remaining requests, we are throttled
        """
        return (
            cls.remaining_requests is not None
            and cls.remaining_requests <= RATE_LIMIT_THRESHOLD
        )

    @staticmethod
    def request(endpoint: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Sends request to an endpoint then updates rate limit count
        Returns json if response code is 200

        Args:
            endpoint (str): The Discogs API endpoint to request.
            timeout (int): Request timeout in seconds. Use a short value for
                latency-sensitive callers (e.g. the art picker).
        """
        resp = requests.get(
            urljoin(Discogs.url, endpoint), headers=Discogs.headers, timeout=timeout
        )
        Discogs.update_rate_limit(resp)
        if Discogs.is_throttled() is True:
            time.sleep(5)  # Sleep for 5s to avoid exceeding rate limit
        if resp.status_code == 200:
            return resp.json()

        raise requests.exceptions.RequestException(f"Status code != 200: {resp}")

    @staticmethod
    def get_item_id(
        name: str,
        item_type: str,
        artist: Optional[str] = None,
        timeout: int = 60,
    ) -> Optional[str]:
        """
        Gets the ID for the specified item type and name.

        Args:
            name (str): The name of the item to search for.
            item_type (str): The type of item to search for, e.g. 'release'.
            artist (str, optional): The artist name to filter the search by.
            timeout (int): Request timeout in seconds; see ``Discogs.request``.

        Returns:
            str or None: The ID of the item if found, None otherwise.
        """
        if not name or not item_type:
            return None
        print(f"Getting ID for {item_type}: {name}")
        query_params = (
            {"q": artist, "type": "release", "release_title": name}
            if item_type == "release"
            else {"q": name, "type": item_type}
        )
        encoded_params = urlencode(query_params)
        endpoint = f"/database/search?{encoded_params}"
        print(f"Search endpoint: {endpoint}")

        try:
            res = Discogs.request(endpoint, timeout=timeout)
        except requests.RequestException:
            return None

        item_id = None
        results = res.get("results", [])
        results_filtered = [r for r in results if r.get("title")]
        results_filtered = [
            r
            for r in results_filtered
            if not any(fmt in FORBIDDEN_FORMATS for fmt in (r.get("format") or []))
        ]
        for result in results_filtered:
            # remove disambiguation chars
            # e.g. "Future (4)" -> "Future"
            result_title = re.sub(DISAMBIG_PATTERN, "", result.get("title"))
            if result_title == name:
                item_id = result.get("id")
                break

        if item_id:
            print(f"ID for {item_type} {name}: {item_id}")
            return item_id

        return None

    @staticmethod
    def find_image(search_results: Dict[str, Any]) -> Optional[str]:
        """
        Finds the first square image from the provided search results.

        Args:
            search_results (requests.Response): The search results containing image data.

        Returns:
            Optional[str]: The URL of the first square image found, or None if no square images are found.
        """
        if (
            not search_results
            or "images" not in search_results.keys()
            or not isinstance(search_results["images"], list)
        ):
            return None
        imgs = search_results.get("images", [])
        print(f"{len(imgs)} candidates found")
        for image in imgs:
            img_url = image.get("uri")
            height = image.get("height")
            width = image.get("width")
            if height == width and height is not None:
                print(f"Square image found: {img_url}")
                return img_url
            print(f"Non-square image: H:{height}/W:{width} | {img_url}")

        print("No square images found. Returning first image result")
        try:
            return imgs[0].get("uri")
        except IndexError:
            print("No images found in search results.")
            return None

    @staticmethod
    def _get_image_url_by_item_id(item_id: str, endpoint_prefix: str) -> Optional[str]:
        """
        Shared by get_release_image_url/get_artist_image_url/get_label_image_url:
        given an already-resolved Discogs item ID, fetches the item's detail
        endpoint and returns its first square image URL, if any.
        """
        endpoint = f"/{endpoint_prefix}/{item_id}"
        try:
            res = Discogs.request(endpoint)
            img = Discogs.find_image(res)
            return img if img else None
        except requests.exceptions.RequestException:
            return None

    @staticmethod
    def get_release_image_url(name: str, artist: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs release.

        Args:
            name (str): The name of the Discogs release to search for.
            artist (str): The name of the Discogs artist associated with the release.

        Returns:
            Optional[str]:  The URL of the image associated with the release,
                            or None if no image is found or an error occurs.
        """
        if (
            not name
            or not isinstance(name, str)
            or not artist
            or not isinstance(artist, str)
        ):
            return None

        release_id = Discogs.get_item_id(name=name, artist=artist, item_type="release")
        if release_id:
            return Discogs._get_image_url_by_item_id(release_id, "releases")
        return None

    @staticmethod
    def get_release_images(
        name: str, artist: Optional[str] = None, limit: int = 4
    ) -> list[dict]:
        """
        Return cover-art candidates for the best-matching Discogs release.

        Each candidate has ``source``, ``url`` (the full-size image), ``thumb``
        (a 150px thumbnail) and ``label`` (the Discogs image type). Square
        images are listed first, matching ``find_image``'s heuristic.

        Returns:
            list[dict]: At most ``limit`` candidates, or an empty list if no
            matching release (or its images) can be found.
        """
        if not name or not isinstance(name, str):
            return []

        release_id = Discogs.get_item_id(
            name=name, artist=artist, item_type="release", timeout=10
        )
        if not release_id:
            return []

        try:
            res = Discogs.request(f"/releases/{release_id}", timeout=10)
        except requests.RequestException:
            return []

        images = [
            img
            for img in res.get("images") or []
            if isinstance(img, dict) and img.get("uri")
        ]
        images.sort(
            key=lambda img: 0
            if img.get("height") is not None and img.get("height") == img.get("width")
            else 1
        )

        candidates = []
        for img in images[:limit]:
            url = img["uri"]
            candidates.append(
                {
                    "source": "discogs",
                    "url": url,
                    "thumb": img.get("uri150") or url,
                    "label": img.get("type"),
                }
            )
        return candidates

    @staticmethod
    def get_artist_image_url(name: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs artist.

        Args:
            name (str): The name of the Discogs artist to search for.

        Returns:
            Optional[str]: The URL of the image associated with the artist,
                            or None if no image is found or an error occurs.
        """
        if not name or not isinstance(name, str):
            return None

        artist_id = Discogs.get_item_id(name=name, item_type="artist")
        if artist_id:
            return Discogs._get_image_url_by_item_id(artist_id, "artists")
        return None

    @staticmethod
    def get_label_image_url(name: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs label.

        Args:
            name (str): The name of the Discogs label to search for.

        Returns:
            Optional[str]: The URL of the image associated with the label,
                            or None if no image is found or an error occurs.
        """
        if not name or not isinstance(name, str):
            return None

        label_id = Discogs.get_item_id(name=name, item_type="label")
        if label_id:
            return Discogs._get_image_url_by_item_id(label_id, "labels")
        return None

    @staticmethod
    def resolve_image_url(
        entity_type: valid_entity_types,
        release_name: Optional[str],
        artist_name: Optional[str],
        label_name: Optional[str],
    ):
        log_str = f"Resolving image URL from Discogs: {entity_type} - "
        match entity_type:
            case "release":
                print(log_str, release_name)
                img_url = Discogs.get_release_image_url(
                    name=release_name, artist=artist_name
                )
            case "artist":
                print(log_str, artist_name)
                img_url = Discogs.get_artist_image_url(name=artist_name)
            case "label":
                print(log_str, label_name)
                img_url = Discogs.get_label_image_url(name=label_name)
            case _:
                img_url = {}
        return img_url
