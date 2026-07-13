import json
import re
import sys
import urllib.request
from typing import Any

PLUGIN_ID = "BulkGEVIPerformerScrape"
TASK_NAME = "Scrape selected performers"
SCRAPER_NAME = "GEVI"
SKIPPED_TAG_NAME = "GEVI: Skipped Performer"
MISSING_TAG_PREFIX = "GEVI: Missing "
FIELD_LABELS = {
    "name": "Name", "disambiguation": "Disambiguation", "aliases": "Aliases",
    "gender": "Gender", "urls": "URL", "image": "Image",
    "hair_color": "Hair Color", "eye_color": "Eye Color",
    "height": "Height", "weight": "Weight", "ethnicity": "Ethnicity",
    "country": "Country", "circumcised": "Circumcision",
    "penis_length": "Penis Length", "tattoos": "Tattoos",
    "birthdate": "Birth Year", "death_date": "Death Year", "details": "Details",
}
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
  gender
  birthdate
  ethnicity
  country
  eye_color
  height_cm
  penis_length
  circumcised
  tattoos
  details
  death_date
  hair_color
  weight
  image_path
  tag_ids: tags { id name }
"""


def log(level: str, message: str) -> None:
    """Write only actionable problems to stderr.

    Stash classifies every stderr line as an Error, regardless of the prefix.
    Routine progress is therefore kept silent and returned only in the final
    JSON summary.
    """
    if level.casefold() in {"error", "ambiguous"}:
        label = "AMBIGUOUS" if level.casefold() == "ambiguous" else "ERROR"
        print(f"[{label}] {message}", file=sys.stderr, flush=True)


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


def find_tag(stash: StashGraphQL, name: str) -> str | None:
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
    return None


def get_tag(stash: StashGraphQL, name: str, create: bool) -> str | None:
    tag_id = find_tag(stash, name)
    if tag_id or not create:
        return tag_id
    mutation = "mutation CreateTag($input: TagCreateInput!) { tagCreate(input: $input) { id } }"
    return str(stash.call(mutation, {"input": {"name": name}})["tagCreate"]["id"])


def missing_tag_name(field: str) -> str:
    return f"{MISSING_TAG_PREFIX}{FIELD_LABELS.get(field, field.replace('_', ' ').title())}"


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


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def local_field_has_value(performer: dict[str, Any], field: str) -> bool:
    mapping = {
        "name": "name",
        "disambiguation": "disambiguation",
        "aliases": "alias_list",
        "gender": "gender",
        "urls": "urls",
        "image": "image_path",
        "hair_color": "hair_color",
        "eye_color": "eye_color",
        "height": "height_cm",
        "weight": "weight",
        "ethnicity": "ethnicity",
        "country": "country",
        "circumcised": "circumcised",
        "penis_length": "penis_length",
        "tattoos": "tattoos",
        "birthdate": "birthdate",
        "death_date": "death_date",
        "details": "details",
    }
    value = performer.get(mapping[field])
    if field == "urls":
        return any(is_gevi_url(url) for url in (value or []))
    return has_value(value)


def scraped_field_value(scraped: dict[str, Any], field: str) -> Any:
    if field == "aliases":
        aliases = parse_aliases(scraped.get("aliases"))
        return aliases or None
    if field == "urls":
        urls = scraped.get("urls") or ([] if not scraped.get("url") else [scraped["url"]])
        return urls or None
    if field == "image":
        images = scraped.get("images") or []
        return (images[0] if images else scraped.get("image")) or None
    if field in {"height", "weight"}:
        return integer_value(scraped.get(field))
    if field == "penis_length":
        return float_value(scraped.get(field))
    if field == "circumcised":
        return circumcised_value(scraped.get(field))
    return scraped.get(field)


def selected_update(
    performer: dict[str, Any], scraped: dict[str, Any], options: dict[str, Any]
) -> tuple[dict[str, Any], list[str], list[str]]:
    fields = list(options.get("fields") or [])
    merge_mode = options.get("update_mode") == "merge"
    update: dict[str, Any] = {"id": performer["id"]}
    missing: list[str] = []
    considered: list[str] = []

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

    for field in fields:
        # In merge mode, only fields that are empty in Stash actually need data.
        if merge_mode and local_field_has_value(performer, field):
            continue

        considered.append(field)
        value = scraped_field_value(scraped, field)
        if not has_value(value):
            missing.append(field)
            continue

        if field in direct_map:
            update[direct_map[field]] = value
        elif field == "height":
            update["height_cm"] = value
        elif field == "weight":
            update["weight"] = value
        elif field == "penis_length":
            update["penis_length"] = value
        elif field == "circumcised":
            update["circumcised"] = value
        elif field == "aliases":
            scraped_aliases = list(value)
            if merge_mode or options.get("merge_aliases", True):
                scraped_aliases = unique_casefold((performer.get("alias_list") or []) + scraped_aliases)
            update["alias_list"] = scraped_aliases
        elif field == "urls":
            update["urls"] = unique_casefold((performer.get("urls") or []) + list(value))
        elif field == "image":
            update["image"] = value

    return update, missing, considered

def update_performer(stash: StashGraphQL, update: dict[str, Any]) -> None:
    mutation = "mutation Update($input: PerformerUpdateInput!) { performerUpdate(input: $input) { id } }"
    stash.call(mutation, {"input": update})


def update_tag_membership(
    stash: StashGraphQL,
    performer: dict[str, Any],
    add_ids: list[str] | None = None,
    remove_ids: list[str] | None = None,
) -> None:
    existing = [str(tag["id"]) for tag in performer.get("tag_ids") or []]
    changed = False
    for tag_id in add_ids or []:
        if tag_id and tag_id not in existing:
            existing.append(tag_id)
            changed = True
    for tag_id in remove_ids or []:
        if tag_id and tag_id in existing:
            existing.remove(tag_id)
            changed = True
    if changed:
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
    maintain_tags = bool(options.get("maintain_tags", True))
    create_tags = bool(options.get("create_tags", True))
    remove_resolved = bool(options.get("remove_resolved_tags", True))
    tag_cache: dict[str, str | None] = {}

    def resolve_tag(name: str) -> str | None:
        if name not in tag_cache:
            tag_cache[name] = get_tag(stash, name, create_tags)
            if tag_cache[name] is None:
                log("info", f'Tag "{name}" does not exist and automatic tag creation is disabled.')
        return tag_cache[name]

    stats = {"selected": len(performer_ids), "updated": 0, "skipped": 0, "failed": 0}

    for index, performer_id in enumerate(performer_ids, start=1):
        try:
            performer = find_performer(stash, performer_id)
            expected_name = display_name(performer.get("name"), performer.get("disambiguation"))
            gevi_urls = [u for u in performer.get("urls") or [] if is_gevi_url(u)]
            scraped: dict[str, Any] | None = None
            reason = ""
            ambiguous = False

            if len(gevi_urls) == 1:
                scraped = scrape_full_from_url(stash, scraper_id, gevi_urls[0], performer.get("name") or "")
                if not scraped:
                    reason = "GEVI URL did not return exactly one performer"
            elif len(gevi_urls) > 1:
                reason = "more than one GEVI URL is attached"
                ambiguous = True
            else:
                candidates = scrape_by_name(stash, scraper_id, expected_name)
                if len(candidates) != 1:
                    reason = f"GEVI search returned {len(candidates)} results"
                    ambiguous = len(candidates) > 1
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
                if maintain_tags:
                    skipped_tag_id = resolve_tag(SKIPPED_TAG_NAME)
                    update_tag_membership(
                        stash, performer,
                        add_ids=[skipped_tag_id] if skipped_tag_id else [],
                    )
                if ambiguous:
                    log("ambiguous", f'[{index}/{len(performer_ids)}] {expected_name}: {reason}')
                continue

            update, missing_fields, considered_fields = selected_update(performer, scraped, options)
            changed = len(update) > 1
            if changed:
                update_performer(stash, update)

            refreshed = find_performer(stash, performer_id)

            if maintain_tags:
                names_by_field = {field: missing_tag_name(field) for field in considered_fields}
                missing_names = [names_by_field[field] for field in missing_fields]
                resolved_names = [
                    names_by_field[field] for field in considered_fields
                    if field not in missing_fields
                ]

                add_ids = [
                    tag_id for tag_id in (resolve_tag(name) for name in missing_names)
                    if tag_id
                ]
                remove_ids: list[str] = []

                if remove_resolved:
                    remove_ids.extend(
                        tag_id for tag_id in (resolve_tag(name) for name in resolved_names)
                        if tag_id
                    )

                skipped_tag_id = resolve_tag(SKIPPED_TAG_NAME)
                if skipped_tag_id:
                    if missing_fields:
                        add_ids.append(skipped_tag_id)
                    elif remove_resolved:
                        remove_ids.append(skipped_tag_id)

                update_tag_membership(
                    stash, refreshed, add_ids=add_ids, remove_ids=remove_ids
                )

            if missing_fields:
                stats["skipped"] += 1
                missing_text = ", ".join(FIELD_LABELS.get(field, field) for field in missing_fields)
                action = "Updated available fields; " if changed else ""
                log("info", f'[{index}/{len(performer_ids)}] {action}Tagged {expected_name}: GEVI returned no value for {missing_text}')
            else:
                if changed:
                    stats["updated"] += 1
                    log("info", f'[{index}/{len(performer_ids)}] Updated {expected_name}')
                else:
                    stats.setdefault("unchanged", 0)
                    stats["unchanged"] += 1
                    if considered_fields:
                        log("info", f'[{index}/{len(performer_ids)}] No changes needed for {expected_name}')
                    else:
                        log("info", f'[{index}/{len(performer_ids)}] Merge skipped {expected_name}: selected fields already had values')
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
