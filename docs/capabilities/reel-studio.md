# Capability: GitHub Reel Studio

## Capability

A repository operator can review proposed wellness video topics in GitHub Issues, approve or reject each proposal, track approved ideas through evidence review and scripting, trigger deterministic Reel rendering, and watch resulting previews on a GitHub Pages dashboard before separately approving publication.

## Constraints

- The public repository must never contain API keys, private health information, client footage, or unpublished sensitive material.
- Each Topic Idea exposes exactly one valid Decision: approve for research or reject.
- Approval authorizes research and drafting only. It does not authorize a factual claim, final render, or publication.
- Elicit results remain Evidence Candidates until human full-text review.
- A render requires a validated Reel Spec with sources, safety language, timing, and `human_review_required` status.
- GitHub Pages may show Previews, but YouTube publication remains a separate future capability and approval.
- Generated MP4 files are stored in the `preview-assets` GitHub prerelease, not Git history. Pages loads their metadata and media for review.
- GitHub Actions secrets are used only at runtime and must never be written to logs, artifacts, issue bodies, or committed files.

## Implementation contract

### Actors

- **Operator:** checks Approve or Reject and reviews rendered previews.
- **Automation:** validates decisions, updates labels, runs tests/renders, and deploys Pages.
- **Evidence reviewer:** turns Evidence Candidates into approved source notes and Reel Specs.

### Surfaces

- GitHub Issues: Topic Idea inbox and decision controls.
- GitHub labels: lifecycle state.
- Repository Reel Specs: reviewed source of truth.
- GitHub Actions: decision validation, evidence discovery, spec-gated rendering, verification, release upload, and Pages deployment.
- GitHub prerelease: generated Preview media and machine-readable metadata.
- GitHub Pages: playable Preview dashboard.

### States

```text
proposed
  -> rejected
  -> approved-for-research
       -> evidence-review
       -> spec-review
       -> ready-to-render
       -> rendering
       -> preview-review
            -> changes-requested
            -> publication-approved
                 -> published (future)
```

### Decision interface

Issue body:

```markdown
- [ ] Approve for research
- [ ] Reject
```

Exactly one checked box is valid. A changed decision with conflicting or empty controls becomes `invalid-decision` and receives a validation comment. Unrelated edits preserve the current lifecycle state.

### Preview interface

Each dashboard entry includes title, status, source Issue, duration, resolution, render version, MP4 controls, captions, Reel Spec, and evidence links. Existing pre-lifecycle drafts are explicitly identified as such.

A reviewed JSON Reel Spec under `reels/specs/` must pass strict source, safety, copy, timing, and output validation before the generic 1080 × 1920 renderer runs. The render workflow rechecks approval before uploading public preview assets.

## Non-goals

- Automatic diagnosis, treatment advice, or evidence-quality determination.
- Automatic publication to YouTube.
- Fully autonomous script generation from abstracts.
- Generated-video storage in Git history.
- Multi-user roles or billing in the MVP.

## Open questions

- Which LLM provider, if any, should draft future Reel Specs inside Actions?
- When should Preview media outgrow GitHub Releases and move to object storage?
- What exact second approval should authorize YouTube publication?

## Handoff

The MVP is implemented with GitHub Issues, Actions, OpenAlex candidate discovery, a manual evidence-to-spec review seam, deterministic generic rendering, GitHub Release preview storage, and a Pages dashboard. YouTube upload remains a later capability.
