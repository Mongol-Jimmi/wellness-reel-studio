# Wellness Brand Lab

Five locally generated identity studies and evidence-linked Plain-Spoken Pebble Reels for a calming mental-wellness series.

## Prerequisites

- Python 3.14 and Pillow: `python3 -m pip install -r requirements.txt`
- FFmpeg and ffprobe 8.x available on `PATH`
- Optional development linting: `python3 -m pip install -r requirements-dev.txt`

## Render

```bash
cd /home/willem/wellness-brand-lab
python3 -m unittest discover -s tests -v
./render.sh
```

## Outputs

- `previews/soft-punctuation.mp4`
- `previews/plain-spoken-pebble.mp4`
- `previews/permission-slip.mp4`
- `previews/inner-weather.mp4`
- `previews/kind-broadcast.mp4`
- `previews/all-identities-comparison.mp4`
- `previews/identity-contact-sheet.png`

All visuals and sounds are generated locally. External spend: USD $0. The bundled Ubuntu Sans font and its licence are in `assets/fonts/` so renders do not depend on a host font installation.

## Evidence-linked content research

The selected **Plain-Spoken Pebble** identity now has an Elicit-backed research pipeline. It keeps easy action steps separate from paper-discovery results and marks every card for human review.

Zero-cost offline build (the default):

```bash
python3 src/research_pipeline.py
```

Live Elicit search after privately setting `ELICIT_API_KEY` and checking account quota:

```bash
python3 src/research_pipeline.py --live --confirm-quota --max-results 8
```

The default selection uses six topics and therefore six live requests when `--live` is explicit. Use `--topic sensory-grounding` to make one smaller call, repeat `--topic` to select several topics, or use `--all` for the ten-topic catalog. Topics are deduplicated and the client enforces a twelve-request ceiling. API access consumes Elicit plan quota.

Outputs are research candidates, never publication-ready cards:

- `research/generated/candidate-evidence-cards.json`
- `research/generated/candidate-evidence-cards.md`
- `research/elicit-api-notes.md`
- `research/openalex-api-notes.md`

OpenAlex research notes are included for a later optional adapter, but the implemented live provider is Elicit because that is the credential currently available.

## First Plain-Spoken Pebble Reel

The first low-resolution content draft combines one sensory grounding check with one comfortable, non-forced breath:

- `previews/plain-spoken-pebble-combined-check-in-lowres.mp4`
- `previews/combined-check-in-keyframes.png`
- `edit/combined-check-in-script.md`
- `edit/combined-check-in-plan.json`
- `edit/combined-check-in-captions.srt`

Render it with `./render_checkin.sh`. The draft remains general-wellness content and requires human playback/creative approval before publication.

## Native 1080×1920 Sleep Hygiene Reel

The second Reel explains sleep hygiene before offering four manageable starting points. It uses a current CDC/NCHS 2024 hook, a no-em-dash humanized copy pass, and a true 1080×1920 renderer rather than upscaling the low-resolution draft.

- `previews/plain-spoken-pebble-sleep-hygiene-1080p.mp4`
- `previews/sleep-hygiene-rendered-keyframes.png`
- `edit/sleep-hygiene-script.md`
- `edit/sleep-hygiene-plan.json`
- `edit/sleep-hygiene-captions.srt`
- `research/generated/sleep-hygiene/candidate-evidence-cards.md`

Run `./verify_sleep_reel.sh` to render first and then enforce the high-resolution artifact checks.

## GitHub Reel Studio

The repository is the control plane, and the pipeline runs evidence first:

1. `python3 scripts/discover_evidence.py` sweeps wellness domains on OpenAlex for reviews and meta-analyses, then writes ranked evidence cards with abstracts to `research/generated/evidence-first/`.
2. A human reads the abstracts, picks one finding, and writes the claim into a proposal file under `ideas/evidence-first/`.
3. `python3 scripts/discover_evidence.py --propose <file> --apply` opens a topic Issue that carries the paper, the reviewed finding, and the safety boundary. The topic exists because the evidence does.
4. The operator checks exactly one box: **Approve for research** or **Reject**.
5. A human writes a Reel Spec under `reels/specs/` that cites the same source.
6. The **Render reviewed Reel Spec** Action validates and renders the Spec at 1080 × 1920, stores the Preview in a GitHub prerelease, and exposes it through Pages.
7. Publication approval remains a separate human decision. YouTube upload is not implemented yet.

Topic-first discovery still exists for filling gaps in an approved topic: **Research approved topic** runs `scripts/research_issue.py` against the Issue's `research-query` comment. Write that query as keywords joined by AND, not as a sentence. OpenAlex searches are scoped to Psychology, Neuroscience, Medicine, and Health Professions because unscoped wellness words return radar and computer-vision papers.

The lifecycle and terms are documented in [`CONTEXT.md`](CONTEXT.md), [`docs/capabilities/reel-studio.md`](docs/capabilities/reel-studio.md), and [ADR 0001](docs/adr/0001-github-control-plane-and-pages-previews.md).

### Cost and secret boundaries

- OpenAlex discovery has no per-request fee and uses no secret.
- Elicit live requests consume account quota. They remain opt-in through `--live --confirm-quota` and are not enabled in GitHub Actions.
- GitHub Actions and Pages use the repository's GitHub allowance. No paid third-party media or AI service is called by the workflows.
- Never commit `ELICIT_API_KEY`. GitHub workflows do not need it for the current pipeline.

Create the proposal Issues only after the public repository and lifecycle labels exist:

```bash
python3 scripts/create_topic_issues.py            # dry run
python3 scripts/create_topic_issues.py --apply    # creates all 10 Issues
```
