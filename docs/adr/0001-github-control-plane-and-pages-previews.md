# ADR 0001: GitHub as the control plane and Pages as the preview surface

## Status

Accepted

## Context

The workflow needs a low-cost operator dashboard for topic proposals, explicit human decisions, automation logs, reproducible source, and playable video previews. A custom web backend would add authentication, hosting, database, and operations work before the content workflow is proven.

GitHub Issues already provide identity, audit history, edits, labels, and event triggers. GitHub Actions can render deterministic videos. Workflow artifacts are downloadable but temporary and are not a good watch-in-browser review experience. Repository video links are possible, but a dedicated Pages site provides a clearer playback surface.

## Decision

Use GitHub Issues as the Topic Idea inbox and lifecycle record, GitHub Actions as the automation runner, repository files as reviewed Reel Specs, and GitHub Pages as the playable Preview dashboard.

Issue checkboxes capture the requested approve/reject interaction. Automation enforces exactly one checked choice and maps it to labels. Approval means approved for research, not approved for publication.

Pages deployments include the dashboard and the two small pre-lifecycle MP4 previews. Newly generated Render files and metadata live in a dedicated GitHub prerelease, and the Pages dashboard loads them through the public GitHub API. When media volume makes Releases impractical, move Render storage behind the same Preview interface to object storage.

## Consequences

### Positive

- No separate authentication or database is needed for the MVP.
- Decisions and workflow history are auditable.
- Preview links can be posted directly back to Issues.
- The repository remains reproducible and portable.

### Negative

- Checkbox edits are less robust than labels and require validation.
- Public Pages exposes draft previews.
- GitHub Actions and Release assets are not a long-term media platform.
- Evidence and script review still require a human-authored Reel Spec before rendering.

## Alternatives considered

- Custom dashboard and database: rejected as premature operational complexity.
- Actions artifacts only: rejected because reviewers must download files and artifacts expire.
- Issue attachments only: rejected because automated attachment upload and durable organization are weaker.
- Immediate YouTube unlisted uploads: deferred until channel credentials and publication policy exist.
