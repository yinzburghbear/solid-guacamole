# Bulk GEVI Performer Scrape

Adds **Scrape selected with GEVI…** to the bulk operations menu on the Stash performer list.

## Behavior

- All metadata fields start disabled each time the dialog opens.
- The task refuses to run unless at least one field is selected.
- If a performer already has exactly one GEVI URL, that URL is scraped directly.
- Without a GEVI URL, the plugin searches by the current Stash name.
- The name search must return exactly one result and its full name (including disambiguation) must match exactly, ignoring only case and repeated whitespace.
- Zero results, multiple results, mismatched names, multiple GEVI URLs, and failed full scrapes are skipped.
- Skipped performers can be tagged `GEVI: Skipped Performer`.
- Successful performers can automatically have that skipped tag removed.
- URLs are always merged. Aliases may be merged or replaced.

## Installation

Copy the `BulkGEVIPerformerScrape` folder into your Stash plugins directory, then reload plugins.

The existing **GEVI** scraper must be installed and working. The plugin locates it by scraper name and calls it through Stash; it does not contain a duplicate copy of GEVI's site parser.

## Files

- `BulkGEVIPerformerScrape.yml` — plugin manifest
- `BulkGEVIPerformerScrape.js` — performer-list bulk action and field-selection dialog
- `BulkGEVIPerformerScrape.py` — matching, scraping, field filtering, updates, and skipped tagging
