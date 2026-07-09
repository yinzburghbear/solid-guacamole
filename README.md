# Graphite Theme 1.0.0-beta3

Graphite is a desktop-first dark theme for Stash 0.31.x. It keeps the core Stash layout, but makes the interface denser, quieter, and more consistent across detail pages, edit forms, settings, taggers, filters, galleries, and plugin-heavy screens.

## Install

1. Copy `graphite.yml` and the `graphite` folder into your Stash plugins folder.
2. In Stash, go to **Settings → Plugins → Reload plugins**.
3. Hard refresh the browser.

Typical Windows path:

```text
%USERPROFILE%\.stash\plugins
```

## Design direction

Graphite uses a muted graphite palette, restrained purple accents, embedded form fields, compact spacing, and consistent resize handles. Color is semantic: purple for primary intent, muted red for destructive actions, muted green for save/success, and graphite for everything that does not need to yell.

## File layout

Stash loads each source CSS file directly from `graphite.yml`, in order. There is no build step required.

```text
graphite.yml
graphite/
  src/
    base/
    layouts/
    components/
    utilities/
    graphite.js
  graphite.css
```

`graphite/graphite.css` is a concatenated reference copy of the loaded CSS. The source files under `graphite/src/` are the files to edit.

# Changelog

## 1.0.0-beta3

- Fixed country selector regression caused by React-Select styling.

## 1.0.0-beta2

- Fixed React-Select scrolling.
- Restored selected country display.

## 1.0.0-beta1

- First feature-complete beta release.
- Unified styling across Scenes, Images, Galleries, Performers, Studios, Settings, Taggers, and modals.
- Introduced Graphite design system and density improvements.
