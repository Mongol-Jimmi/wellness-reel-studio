# Reviewed Reel Specs

A topic reaches this directory only after evidence review and script review. The renderer accepts JSON with this contract:

```json
{
  "version": 1,
  "issue_number": 12,
  "slug": "short-topic-slug",
  "title": "Plain title",
  "render_version": "1.0.0",
  "status": "ready_to_render",
  "publication_status": "human_review_required",
  "format": {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 35},
  "sources": ["https://doi.org/example"],
  "safety": ["General wellness only"],
  "beats": [
    {"id": "hook", "start": 0, "end": 7, "headline": "Visible hook", "body": "Visible explanation."}
  ]
}
```

Requirements enforced by `src/spec_reel.py`:

- 30 to 45 seconds at native 1080 × 1920 and 30 fps.
- Five to eight contiguous beats.
- At least one HTTPS source and one safety boundary.
- No em dashes in visible copy.
- `ready_to_render` and `human_review_required` gates.

After a reviewer commits the Spec and labels its Issue `state:ready-to-render`, dispatch **Render reviewed Reel Spec** with the repository-relative Spec path and Issue number. The workflow uploads the verified output to a prerelease, exposes it on the Pages dashboard, and moves the Issue to `state:preview-review`. It never publishes to YouTube.
