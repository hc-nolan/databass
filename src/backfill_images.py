"""
One-off backfill for releases/artists/labels whose `image` column is NULL
because of the UUID image-filename bug (fixed in f3385ff): fetch_image()/
Util.get_image_from_url() wrote files to disk but their return value was
discarded, so the DB row never recorded where the image lived.

Two passes:
  1. Relink entities to images written under the pre-UUID filename scheme
     (`<entity_id>.<ext>`), which can still be matched back to their entity
     by ID.
  2. Re-fetch cover art (via the same CAA/Discogs logic used on entity
     creation) for anything still missing an image after pass 1. Images
     written under the UUID scheme during the buggy window have no
     recoverable link back to their entity and can only be re-fetched, not
     relinked.

Run inside the app container, from /databass:
    uv run python backfill_images.py [--dry-run] [--skip-refetch]
"""

import argparse
import re
from pathlib import Path

from databass import create_app
from databass.api import image as image_api
from databass.api.util import IMG_BASE_PATH
from databass.db import models
from databass.db.operations import update

ENTITY_MODELS = {
    "release": models.Release,
    "artist": models.Artist,
    "label": models.Label,
}

LEGACY_FILENAME_RE = re.compile(r"^(\d+)\.\w+$")


def relink_legacy_files(dry_run: bool) -> int:
    """Pass 1: match pre-UUID `<id>.<ext>` files back to their entity by ID."""
    relinked = 0
    for entity_type, model in ENTITY_MODELS.items():
        img_dir = Path(IMG_BASE_PATH) / entity_type
        if not img_dir.is_dir():
            continue
        for file in sorted(img_dir.iterdir()):
            match = LEGACY_FILENAME_RE.match(file.name)
            if not match:
                continue
            entity_id = int(match.group(1))
            entity = model.exists_by_id(entity_id)
            if entity is None or entity.image:
                continue
            new_path = f"./static/img/{entity_type}/{file.name}"
            print(f"[relink] {entity_type} {entity_id}: -> {new_path}")
            if not dry_run:
                entity.image = new_path
                update(entity)
            relinked += 1
    return relinked


def _fetch_args(entity_type: str, entity) -> dict:
    if entity_type == "release":
        return {
            "mbid": entity.mbid,
            "release_name": entity.name,
            "artist_name": entity.artist.name if entity.artist else None,
            "label_name": entity.label.name if entity.label else None,
        }
    if entity_type == "artist":
        return {
            "mbid": None,
            "release_name": None,
            "artist_name": entity.name,
            "label_name": None,
        }
    return {  # label
        "mbid": None,
        "release_name": None,
        "artist_name": None,
        "label_name": entity.name,
    }


def refetch_missing(dry_run: bool) -> int:
    """Pass 2: re-fetch cover art for anything still missing an image."""
    refetched = 0
    for entity_type, model in ENTITY_MODELS.items():
        for entity in model.get_all():
            if entity.image:
                continue
            try:
                new_image = image_api.fetch_image(
                    entity_type=entity_type, **_fetch_args(entity_type, entity)
                )
            except Exception as err:
                print(f"[refetch] {entity_type} {entity.id} ({entity.name}): ERROR: {err}")
                continue
            if new_image is None:
                print(f"[refetch] {entity_type} {entity.id} ({entity.name}): no image found")
                continue
            print(f"[refetch] {entity_type} {entity.id} ({entity.name}): -> {new_image}")
            if not dry_run:
                entity.image = new_image
                update(entity)
            refetched += 1
    return refetched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to the DB or fetching new images",
    )
    parser.add_argument(
        "--skip-refetch",
        action="store_true",
        help="Only run the legacy-filename relink pass; skip network re-fetching",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        relinked = relink_legacy_files(args.dry_run)
        print(f"\nRelinked {relinked} entities from legacy filenames.\n")

        if args.skip_refetch:
            return
        refetched = refetch_missing(args.dry_run)
        print(f"\nRe-fetched images for {refetched} entities.")


if __name__ == "__main__":
    main()
