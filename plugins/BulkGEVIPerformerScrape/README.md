# Bulk GEVI Performer Scrape

Version 1.1.3

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

## 1.0.1

- Uses Stash's {pluginDir} substitution to launch the backend from any plugin installation path.
- GEVI itself is still called through Stash GraphQL by scraper ID; no GEVI filesystem path is required.
- The plugin does not add anything to the Tagger source dropdown.

## 1.0.2

- Uses Stash's {pluginDir} substitution to launch the backend from any plugin installation path.
- GEVI itself is still called through Stash GraphQL by scraper ID; no GEVI filesystem path is required.
- The plugin does not add anything to the Tagger source dropdown.

## 1.0.3

- Url wildcard removed from .py file to prevent WinError 10049

## 1.0.4

- Updating Circumcised enum.

## 1.1.1

## GEVI maintenance tags

New options in the modal:

Maintain GEVI missing/status tags
Create tags automatically when needed
Remove missing/status tags when the field is later populated

- **Create tags automatically when needed** creates only tags required by the current run.
- **Remove missing/status tags when the field is later populated** cleans up resolved tags.
- `GEVI: Skipped Performer` remains the general tag for performers that cannot be matched or fully scraped.

## 1.1.3

- added tage for when there is no match

## Logging

Stash displays every line written to stderr as an error. Version 1.1.2 therefore
keeps routine progress silent. Only ambiguous matches and genuine processing
failures are written to the Stash error log. The task result still contains the
final run summary.
