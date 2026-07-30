# ADR 0002: Previews are baked into the Pages artifact

## Status

Accepted, 2026-07-29. Amends [ADR 0001](0001-github-control-plane-and-pages-previews.md).

## Context

ADR 0001 stored rendered previews as assets on the `preview-assets` prerelease and had
the dashboard fetch each `.preview.json` from its `browser_download_url`.

Release asset downloads redirect to `release-assets.githubusercontent.com`, which answers
without an `Access-Control-Allow-Origin` header. The browser therefore blocked every
metadata fetch from the Pages origin, the previews promise rejected, and the dashboard
showed an error instead of any Reel, including the two static ones.

## Decision

The release remains the durable store for rendered output. `scripts/assemble_site.py
--with-release` downloads the release assets at build time, writes them into the Pages
artifact, and merges their cards into a single same-origin `reels.json`. The dashboard
fetches only that file. The render workflow dispatches **Deploy preview dashboard** after
publishing, so a new Reel appears without a manual step.

## Consequences

- No cross-origin fetch of media or metadata, so playback and review work in any browser.
- Pages redeploys after every render, which is one extra short workflow run.
- Release asset names and preview filenames are validated before becoming file paths.
- A missing release is tolerated at build time. Any other API failure fails the build loudly.
