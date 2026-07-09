# Graphite Theme 1.0.0-alpha9 — Zero Build

Install `graphite.yml` and the `graphite` folder into your Stash plugins folder:

```text
%USERPROFILE%\.stash\plugins
```

Then reload plugins in Stash and hard refresh the browser.

## Editing

Stash loads:

```text
graphite/graphite.css
```

That file only contains `@import` lines. Edit the source files in:

```text
graphite/src/
```

Then hard refresh Stash. No Python, npm, Sass, sacrificial goat, or build script needed.

## Source layout

```text
graphite/src/
├── base/          variables, document defaults, typography
├── layouts/       app shell and detail-page layout
├── components/    nav, cards, buttons, forms, tables, tags, tabs, modals
├── utilities/     density and reduced-motion helpers
└── overrides/     Stash/Bootstrap-specific alpha patches
```

`overrides/90-prototype-and-alpha-patches.css` is intentionally last. That is the containment zone for the ugly-but-necessary specificity fixes.
