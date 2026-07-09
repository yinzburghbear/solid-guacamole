# Graphite Theme for Stash

Graphite 1.0.0-alpha1 is the first design-system pass for Stash 0.31.x.

## Install

Copy `graphite.yml` and the `graphite` folder into:

`%USERPROFILE%\.stash\plugins`

Then in Stash: **Settings → Plugins → Reload plugins**. Hard refresh with `Shift + F5`.

## Notes

- `graphite/graphite.css` is the compiled CSS Stash loads.
- `graphite/src/` contains the planned modular source structure so future edits do not become one giant haunted stylesheet.
- Tags intentionally preserve the Graphite 0.1.3 look.
- CSS-only. No JavaScript, no backdrop-filter circus, no layout rewrite.

## Alpha1 focus

- Design tokens / CSS variables
- Compact global navigation
- Neutral buttons with calmer blue accents
- Detail-page divider cleanup
- Scene/detail spacing cleanup
- Dropdown transparency fixes
- Image preview overlay fix
