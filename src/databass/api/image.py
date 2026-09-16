"""
Image-fetching orchestration: pulls cover art from CoverArtArchive/Discogs
and writes it to disk. Kept separate from util.py so that Util can stay a
leaf module with no dependency on MusicBrainz/Discogs.
"""

import signal
from pathlib import Path
from typing import Optional
from uuid import uuid4
import requests
from .discogs import Discogs
from .musicbrainz import MusicBrainz
from .util import (
    IMG_BASE_PATH,
    VALID_TYPES,
    VERSION,
    Util,
    timeout_handler,
)


def get_caa_image(mbid: str) -> dict:
    """Get image from CoverArtArchive"""
    print(f"Attempting to fetch image from CoverArtArchive: {mbid}")

    timeout_duration = 5
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_duration)

    img = MusicBrainz.get_image(mbid)
    if img is not None:
        print("CoverArtArchive image found")
        # CAA returns the raw image data
        img_type = Util.get_image_type_from_bytes(img)
    else:
        raise ValueError(
            "No image returned by CoverArtArchive, or an error was encountered when fetching the image."
        )
    return {"image": img, "type": img_type}


def get_discogs_image(
    entity_type: str,
    release_name: Optional[str],
    artist_name: Optional[str],
    label_name: Optional[str],
) -> dict:
    match entity_type:
        case "release":
            img_url = Discogs.get_release_image_url(
                name=release_name, artist=artist_name
            )
        case "artist":
            img_url = Discogs.get_artist_image_url(name=artist_name)
        case "label":
            img_url = Discogs.get_label_image_url(name=label_name)
        case _:
            return {}
    if img_url is None:
        return {}
    response = requests.get(
        img_url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"databass/{VERSION} (https://github.com/hc-nolan/databass)",
        },
        timeout=60,
    )
    img = response.content
    img_type = Util.get_image_type_from_bytes(img)
    return {"image": img, "type": img_type}


def write_image(entity_type: str, img_type: str, img_bytes: bytes) -> str:
    file_name = str(uuid4()) + img_type
    file_path = IMG_BASE_PATH + "/" + entity_type + "/" + file_name
    with open(file_path, "wb") as img_file:
        img_file.write(img_bytes)
    print(f"Image saved to {file_path}")
    return file_path.replace("databass/", "")


def get_image(
    entity_type: str,
    entity_id: str | int,
    mbid: Optional[str],
    release_name: Optional[str],
    artist_name: Optional[str],
    label_name: Optional[str],
    url: Optional[str],
):
    if entity_type not in VALID_TYPES:
        raise ValueError(f"Unexpected entity_type: {entity_type}")
    if url:
        return Util.get_image_from_url(entity_type=entity_type, url=url)
    Path(f"{IMG_BASE_PATH}/{entity_type}").mkdir(parents=True, exist_ok=True)

    img = img_type = None

    if mbid is not None and entity_type == "release":
        try:
            caa_image = get_caa_image(mbid=mbid)
            img = caa_image.get("image")
            img_type = caa_image.get("type")
        except Exception:
            print("Image not found on CAA, checking Discogs")
            return get_image(
                url=None,
                mbid=None,
                entity_type=entity_type,
                entity_id=entity_id,
                release_name=release_name,
                artist_name=artist_name,
                label_name=label_name,
            )
    else:
        print(f"Attempting to fetch {entity_type} image from Discogs")
        try:
            discogs_image = get_discogs_image(
                entity_type=entity_type,
                release_name=release_name,
                artist_name=artist_name,
                label_name=label_name,
            )
        except Exception as err:
            print(f"WARNING: Could not fetch {entity_type} image from Discogs: {err}")
            return None
        img = discogs_image.get("image")
        img_type = discogs_image.get("type")

    if img is not None and img_type is not None:
        return write_image(
            entity_type=entity_type,
            img_bytes=img,
            img_type=img_type,
        )
