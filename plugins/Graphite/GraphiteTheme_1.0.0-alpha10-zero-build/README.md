# Graphite Theme 1.0.0-alpha10 zero-build2

This version does **not** use CSS `@import`.

Stash loads every source CSS file directly from `graphite.yml`, in order. Edit files under `graphite/src/`, reload plugins, then hard refresh the browser.

Install:

1. Copy `graphite.yml` and the `graphite` folder into `%USERPROFILE%\.stash\plugins`.
2. Stash → Settings → Plugins → Reload plugins.
3. Hard refresh the browser.

Why this exists: the first zero-build package relied on CSS `@import`, and Stash apparently decided that was too generous.


## alpha10 changes

- Darker Graphite base around `#0d0e0f`.
- Purple accent pass.
- Performer-card button backgrounds removed.
- Performer/group card title size reduced to `1.05rem`.
- Scene detail title restored to stock-ish h3 sizing.
