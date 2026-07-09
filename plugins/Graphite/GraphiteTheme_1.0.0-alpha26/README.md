# Graphite Theme 1.0.0-alpha26 zero-build2

This version does **not** use CSS `@import`.

Stash loads every source CSS file directly from `graphite.yml`, in order. Edit files under `graphite/src/`, reload plugins, then hard refresh the browser.

Install:

1. Copy `graphite.yml` and the `graphite` folder into `%USERPROFILE%\.stash\plugins`.
2. Stash → Settings → Plugins → Reload plugins.
3. Hard refresh the browser.

Why this exists: the first zero-build package relied on CSS `@import`, and Stash apparently decided that was too generous.


## alpha11 changes

- Darker Graphite base around `#0d0e0f`.
- Purple accent pass.
- Performer-card button backgrounds removed.
- Performer/group card title size reduced to `1.05rem`.
- Scene detail title restored to stock-ish h3 sizing.


## 1.0.0-alpha11

- The scene detail metadata block now uses Graphite background/text styling.
- Performer-card favorite/mousetrap overlay button is excluded from Graphite button styling.


## alpha20 notes

- Integrated the previous alpha override rules into `graphite/src/components/99-alpha-refinements.css`.
- Added `graphite/src/components/95-plugin-integrations.css` for the Graphite-adapted Refract plugin/settings-page styling.
- Left `graphite/src/overrides/*` empty so future quick experiments do not become a haunted junk drawer.


## alpha20
- Settings pages now use more horizontal viewport space.
- Settings → Plugins disabled rows are pushed to the bottom via a small UI JavaScript helper.

## alpha26 notes
- Removed idle tag-select caret sliver on performer edit tag fields.
- Tightened performer/detail action buttons.
- Removed accidental row-panel backgrounds from gallery/image details and scene edit controls.
- Narrowed gallery/image resize handles where Stash exposes resize-ish classes.
- Cleaned the scene queue active item to match Graphite.
