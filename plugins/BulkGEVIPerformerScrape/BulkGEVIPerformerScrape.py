import json
import re
import sys
import urllib.request
from typing import Any

PLUGIN_ID = "BulkGEVIPerformerScrape"
TASK_NAME = "Scrape selected performers"
SCRAPER_NAME = "GEVI"
SKIPPED_TAG_NAME = "GEVI: Skipped Performer"
GEVI_HOST = "gayeroticvideoindex.com"

SCRAPED_FIELDS = """
  name
  disambiguation
  gender
  urls
  birthdate
  ethnicity
  country
  eye_color
  height
  penis_length
  circumcised
  tattoos
  aliases
  images
  image
  details
  death_date
  hair_color
  weight
"""

PERFORMER_FIELDS = """
  id
  name
  disambiguation
  urls
  alias_list
  tag_ids: tags { id name }
"""


def log(level: str, message: str) -> None:
    """Write diagnostic output away from stdout.

    With interface: raw, Stash expects stdout to contain exactly one JSON result.
    """
    print(f"[{level.upper()}] {message}", file=sys.stderr, flush=True)


class StashGraphQL:
    def __init__(self, connection: dict[str, Any]):
        scheme = connection.get("Scheme") or connection.get("scheme") or "http"
        host = str(connection.get("Host") or connection.get("host") or "localhost").strip()
        port = connection.get("Port") or connection.get("port") or 9999

        # Stash may report its bind/listen address to plugins. Wildcard addresses
        # are valid for a server to listen on, but are not valid destinations for
        # a client connection on Windows (WinError 10049). Connect locally instead.
        if host.casefold() in {"0.0.0.0", "::", "[::]", "*"}:
            host = "127.0.0.1"
        elif ":" in host and not host.startswith("["):
            # Bracket ordinary IPv6 literals when constructing a URL.
            host = f"[{host}]"

        self.url = f"{scheme}://{host}:{port}/graphql"
        self.api_key = connection.get("ApiKey") or connection.get("api_key") or ""

    def call(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["ApiKey"] = self.api_key
        request = urllib.request.Request(self.url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("errors"):
            raise RuntimeError("; ".join(e.get("message", str(e)) for e in result["errors"]))
        return result.get("data", {})


def normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def display_name(name: str | None, disambiguation: str | None) -> str:
    base = (name or "").strip()
    return f"{base} ({disambiguation.strip()})" if disambiguation else base


def is_gevi_url(url: str) -> bool:
    return GEVI_HOST in url.casefold()


def parse_aliases(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def unique_casefold(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = normalize(value)
        if key and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def integer_value(value: Any) -> int | None:
    if value is None or value == "":
        return None
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else None


def float_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None




def circumcised_value(value: Any) -> str | None:
    if value is None or value == "":
        return None
    normalized = normalize(str(value)).replace("-", " ")
    mapping = {
        "cut": "CUT",
        "circumcised": "CUT",
        "uncut": "UNCUT",
        "uncircumcised": "UNCUT",
        "un cut": "UNCUT",
    }
    return mapping.get(normalized)

def find_gevi_scraper(stash: StashGraphQL) -> str:
    query = """
      query FindScrapers { listScrapers(types: [PERFORMER]) { id name performer { supported_scrapes } } }
    """
    scrapers = stash.call(query).get("listScrapers") or []
    exact = [s for s in scrapers if normalize(s.get("name")) == normalize(SCRAPER_NAME)]
    if not exact:
        exact = [s for s in scrapers if "gevi" in normalize(s.get("name"))]
    if len(exact) != 1:
        names = ", ".join(s.get("name", "") for s in exact) or "none"
        raise RuntimeError(f"Could not uniquely locate the installed GEVI scraper (matches: {names}).")
    return str(exact[0]["id"])


def get_or_create_tag(stash: StashGraphQL, name: str) -> str:
    query = """
      query FindTags($filter: FindFilterType, $tag_filter: TagFilterType) {
        findTags(filter: $filter, tag_filter: $tag_filter) { tags { id name } }
      }
    """
    variables = {
        "filter": {"q": name, "per_page": 50},
        "tag_filter": {"name": {"value": name, "modifier": "EQUALS"}},
    }
    tags = stash.call(query, variables).get("findTags", {}).get("tags") or []
    for tag in tags:
        if normalize(tag.get("name")) == normalize(name):
            return str(tag["id"])
    mutation = "mutation CreateTag($input: TagCreateInput!) { tagCreate(input: $input) { id } }"
    return str(stash.call(mutation, {"input": {"name": name}})["tagCreate"]["id"])


def find_performer(stash: StashGraphQL, performer_id: str) -> dict[str, Any]:
    query = f"query FindPerformer($id: ID!) {{ findPerformer(id: $id) {{ {PERFORMER_FIELDS} }} }}"
    performer = stash.call(query, {"id": performer_id}).get("findPerformer")
    if not performer:
        raise RuntimeError(f"Performer {performer_id} no longer exists.")
    performer["tag_ids"] = performer.pop("tag_ids", [])
    return performer


def scrape_by_name(stash: StashGraphQL, scraper_id: str, name: str) -> list[dict[str, Any]]:
    query = f"""
      query Search($source: ScraperSourceInput!, $input: ScrapeSinglePerformerInput!) {{
        scrapeSinglePerformer(source: $source, input: $input) {{ {SCRAPED_FIELDS} }}
      }}
    """
    data = stash.call(query, {"source": {"scraper_id": scraper_id}, "input": {"query": name}})
    return data.get("scrapeSinglePerformer") or []


def scrape_by_fragment(stash: StashGraphQL, scraper_id: str, performer: dict[str, Any]) -> list[dict[str, Any]]:
    fragment: dict[str, Any] = {
        "name": performer.get("name"),
        "disambiguation": performer.get("disambiguation"),
        "urls": performer.get("urls") or [],
    }
    query = f"""
      query Scrape($source: ScraperSourceInput!, $input: ScrapeSinglePerformerInput!) {{
        scrapeSinglePerformer(source: $source, input: $input) {{ {SCRAPED_FIELDS} }}
      }}
    """
    data = stash.call(query, {"source": {"scraper_id": scraper_id}, "input": {"performer_input": fragment}})
    return data.get("scrapeSinglePerformer") or []


def scrape_full_from_url(stash: StashGraphQL, scraper_id: str, url: str, name: str) -> dict[str, Any] | None:
    fragment = {"name": name, "urls": [url]}
    query = f"""
      query Scrape($source: ScraperSourceInput!, $input: ScrapeSinglePerformerInput!) {{
        scrapeSinglePerformer(source: $source, input: $input) {{ {SCRAPED_FIELDS} }}
      }}
    """
    results = stash.call(query, {"source": {"scraper_id": scraper_id}, "input": {"performer_input": fragment}}).get("scrapeSinglePerformer") or []
    return results[0] if len(results) == 1 else None


def selected_update(performer: dict[str, Any], scraped: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    fields = set(options.get("fields") or [])
    update: dict[str, Any] = {"id": performer["id"]}

    direct_map = {
        "name": "name",
        "disambiguation": "disambiguation",
        "gender": "gender",
        "birthdate": "birthdate",
        "ethnicity": "ethnicity",
        "country": "country",
        "eye_color": "eye_color",
        "tattoos": "tattoos",
        "details": "details",
        "death_date": "death_date",
        "hair_color": "hair_color",
    }
    for selected, gql_field in direct_map.items():
        if selected in fields and scraped.get(selected) is not None:
            update[gql_field] = scraped[selected]

    if "circumcised" in fields:
        value = circumcised_value(scraped.get("circumcised"))
        if value is not None:
            update["circumcised"] = value

    if "height" in fields:
        value = integer_value(scraped.get("height"))
        if value is not None:
            update["height_cm"] = value
    if "weight" in fields:
        value = integer_value(scraped.get("weight"))
        if value is not None:
            update["weight"] = value
    if "penis_length" in fields:
        value = float_value(scraped.get("penis_length"))
        if value is not None:
            update["penis_length"] = value

    if "aliases" in fields and scraped.get("aliases") is not None:
        scraped_aliases = parse_aliases(scraped.get("aliases"))
        if options.get("merge_aliases", True):
            scraped_aliases = unique_casefold((performer.get("alias_list") or []) + scraped_aliases)
        update["alias_list"] = scraped_aliases

    if "urls" in fields:
        scraped_urls = scraped.get("urls") or ([] if not scraped.get("url") else [scraped["url"]])
        update["urls"] = unique_casefold((performer.get("urls") or []) + scraped_urls)

    if "image" in fields:
        images = scraped.get("images") or []
        image = images[0] if images else scraped.get("image")
        if image:
            update["image"] = image

    return update


def update_performer(stash: StashGraphQL, update: dict[str, Any]) -> None:
    mutation = "mutation Update($input: PerformerUpdateInput!) { performerUpdate(input: $input) { id } }"
    stash.call(mutation, {"input": update})


def set_skipped_tag(stash: StashGraphQL, performer: dict[str, Any], tag_id: str, add: bool) -> None:
    existing = [str(tag["id"]) for tag in performer.get("tag_ids") or []]
    if add and tag_id not in existing:
        existing.append(tag_id)
    if not add and tag_id in existing:
        existing.remove(tag_id)
    update_performer(stash, {"id": performer["id"], "tag_ids": existing})


def process() -> None:
    payload = json.load(sys.stdin)
    args = payload.get("args") or {}
    connection = payload.get("server_connection") or {}
    performer_ids = [str(x) for x in args.get("performer_ids") or []]
    options = args.get("options") or {}
    fields = options.get("fields") or []

    if not performer_ids:
        raise RuntimeError("No performers were selected.")
    if not fields:
        raise RuntimeError("No scrape fields were selected. Nothing was changed.")

    stash = StashGraphQL(connection)
    scraper_id = find_gevi_scraper(stash)
    skipped_tag_id = get_or_create_tag(stash, SKIPPED_TAG_NAME) if options.get("tag_skipped", True) else ""

    stats = {"selected": len(performer_ids), "updated": 0, "skipped": 0, "failed": 0}

    for index, performer_id in enumerate(performer_ids, start=1):
        try:
            performer = find_performer(stash, performer_id)
            expected_name = display_name(performer.get("name"), performer.get("disambiguation"))
            gevi_urls = [u for u in performer.get("urls") or [] if is_gevi_url(u)]
            scraped: dict[str, Any] | None = None
            reason = ""

            if len(gevi_urls) == 1:
                scraped = scrape_full_from_url(stash, scraper_id, gevi_urls[0], performer.get("name") or "")
                if not scraped:
                    reason = "GEVI URL did not return exactly one performer"
            elif len(gevi_urls) > 1:
                reason = "more than one GEVI URL is attached"
            else:
                candidates = scrape_by_name(stash, scraper_id, expected_name)
                if len(candidates) != 1:
                    reason = f"GEVI search returned {len(candidates)} results"
                else:
                    candidate = candidates[0]
                    candidate_name = display_name(candidate.get("name"), candidate.get("disambiguation"))
                    candidate_urls = candidate.get("urls") or ([] if not candidate.get("url") else [candidate["url"]])
                    if normalize(candidate_name) != normalize(expected_name):
                        reason = f'name mismatch: "{candidate_name}"'
                    elif len(candidate_urls) != 1 or not is_gevi_url(candidate_urls[0]):
                        reason = "the exact result did not contain one GEVI URL"
                    else:
                        scraped = scrape_full_from_url(stash, scraper_id, candidate_urls[0], performer.get("name") or "")
                        if not scraped:
                            reason = "the exact GEVI result could not be fully scraped"

            if not scraped:
                stats["skipped"] += 1
                if skipped_tag_id:
                    set_skipped_tag(stash, performer, skipped_tag_id, True)
                log("info", f'[{index}/{len(performer_ids)}] Skipped {expected_name}: {reason}')
                continue

            update = selected_update(performer, scraped, options)
            if len(update) > 1:
                update_performer(stash, update)
            if skipped_tag_id and options.get("remove_skipped_on_success", True):
                refreshed = find_performer(stash, performer_id)
                set_skipped_tag(stash, refreshed, skipped_tag_id, False)
            stats["updated"] += 1
            log("info", f'[{index}/{len(performer_ids)}] Updated {expected_name}')
        except Exception as exc:
            stats["failed"] += 1
            log("error", f"[{index}/{len(performer_ids)}] Performer {performer_id} failed: {exc}")

    summary = "Bulk GEVI Performer Scrape complete — " + ", ".join(f"{k}: {v}" for k, v in stats.items())
    log("info", summary)
    print(json.dumps({"output": summary}), flush=True)


if __name__ == "__main__":
    try:
        process()
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        log("error", message)
        print(json.dumps({"error": message}), flush=True)
        sys.exit(1)
