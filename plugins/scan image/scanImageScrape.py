import sys
import json
import time

import stashapi.log as log
from stashapi.stash_types import StashItem
from stashapi.stashapp import StashInterface
from stashapi.scrape_parser import ScrapeParser

# ─────────────────────────────────────────────
# Hardcoded scraper — matches the imagescraper
# folder name (scraper ID as Stash sees it)
# ─────────────────────────────────────────────
SCRAPER_ID: str = "01 FanScraper"

# Settings — mirror the defaults from BulkImageScrape
# so behavior is consistent. Edit here if needed.
CREATE_MISSING_PERFORMERS: bool = True
CREATE_MISSING_STUDIOS:    bool = True
CREATE_MISSING_TAGS:       bool = True
MERGE_EXISTING_TAGS:       bool = True


def scrape_is_valid(scrape_input: dict | list[dict] | None) -> bool:
    if scrape_input is None:
        return False
    elif isinstance(scrape_input, list):
        return len(scrape_input) == 1 and scrape_is_valid(scrape_input[0])
    elif isinstance(scrape_input, dict):
        return any(
            value
            for value in scrape_input.values()
            if value is not None and value != [] and value != {} and value != ""
        )
    return False


def process_image_scrape(
    parser: ScrapeParser,
    image_input: dict,
    scrape_input: dict | list[dict],
) -> dict | None:
    if isinstance(scrape_input, list) and len(scrape_input) == 1:
        scrape_input = scrape_input[0]
    elif not isinstance(scrape_input, dict):
        log.error(f"Unknown scrape input type for image {image_input['id']}")
        return None

    update_dict: dict = parser.image_from_scrape(scrape_input)
    update_dict["id"] = image_input["id"]

    if MERGE_EXISTING_TAGS:
        existing_tags: list = [tag["id"] for tag in image_input.get("tags", [])]
        merged_tags: list = list(set(existing_tags + update_dict.get("tag_ids", [])))
        update_dict["tag_ids"] = merged_tags

    return update_dict


# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────

json_input: dict = json.loads(sys.stdin.read())
FRAGMENT_SERVER: dict = json_input["server_connection"]
stash: StashInterface = StashInterface(FRAGMENT_SERVER)

# Pull the image ID out of the hook input.
# Stash passes: {"hookContext": {"id": <int>, "type": "Image"}}
hook_context: dict = json_input.get("args", {}).get("hookContext", {})
image_id: str | None = str(hook_context.get("id")) if hook_context.get("id") else None

if not image_id:
    log.error("ScanImageScrape: no image ID found in hook input — exiting")
    sys.exit(0)

log.info(f"ScanImageScrape: triggered for image {image_id}")

# ─────────────────────────────────────────────
# Give DefaultDataForPath (and any other hooks
# on Image.Create.Post) a moment to finish
# assigning studio/performer/tags first, so
# imagescraper can resolve the studio name.
# ─────────────────────────────────────────────
time.sleep(2)

# ─────────────────────────────────────────────
# Validate the scraper is available
# ─────────────────────────────────────────────
scrapers: list[dict] = stash.list_scrapers([StashItem.IMAGE])
scraper_ids = [s["id"] for s in scrapers]

if SCRAPER_ID not in scraper_ids:
    log.error(
        f"ScanImageScrape: scraper '{SCRAPER_ID}' not found in installed image scrapers.\n"
        f"Available image scrapers: {scraper_ids}"
    )
    sys.exit(1)

# ─────────────────────────────────────────────
# Fetch the full image record from Stash
# ─────────────────────────────────────────────
image: dict | None = stash.find_image(image_id)

if not image:
    log.error(f"ScanImageScrape: could not find image {image_id} in Stash — exiting")
    sys.exit(0)

# ─────────────────────────────────────────────
# Scrape
# ─────────────────────────────────────────────
scrape_parser = ScrapeParser(
    stash,
    log,
    CREATE_MISSING_TAGS,
    CREATE_MISSING_STUDIOS,
    CREATE_MISSING_PERFORMERS,
)

log.debug(f"ScanImageScrape: scraping image {image_id} with scraper '{SCRAPER_ID}'")

try:
    scrape_result = stash.scrape_image(SCRAPER_ID, image_id)
except Exception as e:
    log.error(f"ScanImageScrape: scraper raised an exception for image {image_id}: {e}")
    sys.exit(0)

if not scrape_is_valid(scrape_result):
    log.debug(
        f"ScanImageScrape: scraper returned empty/invalid result for image {image_id} — skipping"
    )
    sys.exit(0)

update_input: dict | None = process_image_scrape(scrape_parser, image, scrape_result)

if update_input is None:
    log.error(f"ScanImageScrape: failed to build update payload for image {image_id}")
    sys.exit(0)

try:
    stash.update_image(update_input)
    log.info(f"ScanImageScrape: successfully updated image {image_id}")
except Exception as e:
    log.error(f"ScanImageScrape: failed to update image {image_id}: {e}")
