# Wellness Brand Lab

A calming mental-wellness Reel studio. The current practice format uses sparse, breath-mapped visuals and softly paced OpenRouter speech instead of copy-heavy slides.

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

The bundled Ubuntu Sans font and its licence are in `assets/fonts/` so renders do not depend on a host font installation.

## One-minute practice format

A practice Reel guides one exercise and nothing else, in the Plain-Spoken Pebble language:
warm paper, the drifting lavender shapes, the mustard dots. There are two.

**Cyclic sighing.** The pebble is the guide rather than a label holder. It fills through
the inhale, lifts a second small pebble on the sip, and pales as it settles through the
sigh out. Three words appear all minute, each in a frosted chip: `in`, `more`, `out`.

**Step back.** A self-distancing minute the viewer plays along with. Two pebbles, yours and
the thing, ease apart while you watch it from outside, and a drawn line crosses the gap
while you put what you see into words. The 2022 meta-analysis found the visual and verbal
approach beat either half alone, so the describing gets its own mark on screen.

Narration is a Coral voice from `openai/gpt-audio-mini` through OpenRouter. Audio output
from that model requires `stream: true` and `pcm16`; a plain request is rejected.

Every motion runs a whole number of cycles per minute, so the last frame meets the first
and the Reel loops without a seam. Both practice test modules assert that seam, so a change
that breaks the loop fails the suite.

```bash
export OPENROUTER_API_KEY=...  # only needed the first time voice cues are generated
./render_practice.sh cyclic-sigh
./render_practice.sh step-back
```

Outputs:

- `previews/cyclic-sigh-pebble-60s.mp4`, `previews/step-back-60s.mp4`
- `edit/cyclic-sigh-practice-script.md`
- `edit/cyclic-sigh-practice-captions.srt`
- `edit/cyclic-sigh-practice-brief.md`
- `edit/step-back-practice-brief.md`
- `edit/step-back-practice-captions.srt`

### Motion and material

`src/motion.py` is the shared vocabulary both practices animate through, ported from the
news studio's locked-easing presets and animation bank: an easing chosen per gesture rather
than one smoothstep everywhere, a deterministic grain and vignette pass so the flat fills
read as printed, strokes that draw themselves on with a seeded wobble, and 12fps stutter on
decorative marks only. [ADR 0003](docs/adr/0003-motion-vocabulary-from-the-news-studio.md)
records what was ported, what was left behind, and why the grain cadence is what it is.

The speech call is paid through the configured OpenRouter account. Voice cues are cached
under ignored `work/audio/`, so re-rendering the visuals never calls OpenRouter again.

A practice is not a Reel Spec. It has no beats or text slides, so it does not go through
the approval autopilot and is not on the Pages dashboard yet.

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

1. `python3 scripts/discover_evidence.py` sweeps wellness domains for reviews, meta-analyses, and RCTs, then writes ranked evidence cards with abstracts to `research/generated/evidence-first/`. It uses the paid Elicit semantic search by default, one request per seed with a twelve request ceiling. Add `--provider openalex` for a free but noisier sweep.
2. A human reads the abstracts, picks one finding, and writes the claim into a proposal file under `ideas/evidence-first/`.
3. `python3 scripts/discover_evidence.py --propose <file> --apply` opens a topic Issue that carries the paper, the reviewed finding, and the safety boundary. The topic exists because the evidence does.
4. The operator checks exactly one box: **Approve for research** or **Reject**.
5. A human writes a Reel Spec under `reels/specs/` that cites the same source.
6. The **Render reviewed Reel Spec** Action validates and renders the Spec at 1080 × 1920, stores the Preview in a GitHub prerelease, and exposes it through Pages.
7. Publication approval remains a separate human decision. YouTube upload is not implemented yet.

Topic-first discovery still exists for filling gaps in an approved topic: **Research approved topic** runs `scripts/research_issue.py` against the Issue's `research-query` comment. Write that query as keywords joined by AND, not as a sentence. OpenAlex searches are scoped to Psychology, Neuroscience, Medicine, and Health Professions because unscoped wellness words return radar and computer-vision papers.

### Approval autopilot

Ticking **Approve for research** is the only human step in a Reel. A timer on the studio
machine picks the topic up within ten minutes and takes it the rest of the way:

```bash
python3 scripts/autopilot_spec.py             # every approved topic without a Spec
python3 scripts/autopilot_spec.py --issue 12 --dry-run
systemctl --user status wellness-autopilot.timer
```

The writer reads the Issue, asks a local model for a Reel Spec grounded in the paper the
Issue carries, and refuses to ship anything that fails these checks:

- every number on screen must appear in the paper's abstract or the reviewed finding
- any beat showing a number must also show a source label
- the safety boundary is copied from the Issue word for word
- no cure, guarantee, prevents, eliminates, instantly, proven, or you-must phrasing
- plus the existing shape rules: timing, lengths, HTTPS sources, no em dashes

A rejected draft is sent back to the model with the exact error, up to three attempts.
The model runs locally because the studio uses a Claude subscription rather than an API
key, so no model secret is stored in GitHub. These checks cannot tell whether a claim is
*true*, only whether it is grounded and hedged, which is why output stays a Preview and
publication remains a separate human decision.

The lifecycle and terms are documented in [`CONTEXT.md`](CONTEXT.md), [`docs/capabilities/reel-studio.md`](docs/capabilities/reel-studio.md), and [ADR 0001](docs/adr/0001-github-control-plane-and-pages-previews.md).

### Cost and secret boundaries

- OpenAlex discovery has no per-request fee and uses no secret.
- The evidence-first sweep calls Elicit and consumes plan quota, one request per seed. Export `ELICIT_API_KEY` before running it, keep it out of the repository, and use `--provider openalex` when a free sweep is enough.
- `src/research_pipeline.py` still keeps Elicit behind `--live --confirm-quota`. No workflow calls Elicit, so GitHub Actions needs no secret.
- GitHub Actions and Pages use the repository's GitHub allowance. No paid third-party media or AI service is called by the workflows.
- Never commit `ELICIT_API_KEY`. GitHub workflows do not need it for the current pipeline.

Create the proposal Issues only after the public repository and lifecycle labels exist:

```bash
python3 scripts/create_topic_issues.py            # dry run
python3 scripts/create_topic_issues.py --apply    # creates all 10 Issues
```
