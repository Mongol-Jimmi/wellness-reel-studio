#!/usr/bin/env python3
"""Write a Reel Spec for every approved topic that does not have one, then render it.

The operator's Approve tick is the only human step. This script reads the Issue, asks a
model for a Spec grounded in the paper it carries, enforces the shape and copy guards,
commits the Spec, and dispatches the render. Publication remains a separate decision.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.spec_guard import guard
from src.spec_reel import validate_spec

SPECS = ROOT / "reels" / "specs"
REPOSITORY = "Mongol-Jimmi/wellness-reel-studio"
QUEUE_LABEL = "state:spec-review"
SECTION = re.compile(r"^## (.+?)\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
ATTEMPTS = 3


def run(command: list[str], stdin: str | None = None) -> str:
    completed = subprocess.run(command, input=stdin, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError(f"title produced an empty slug: {title!r}")
    return slug


def sections(body: str) -> dict[str, str]:
    return {name.strip().lower(): text.strip() for name, text in SECTION.findall(body)}


def queued_issues() -> list[dict]:
    payload = run(["gh", "issue", "list", "--repo", REPOSITORY, "--label", f"topic-proposal,{QUEUE_LABEL}",
                   "--state", "open", "--limit", "20", "--json", "number,title,body"])
    return json.loads(payload)


def prompt_for(issue: dict, parts: dict[str, str], slug: str) -> str:
    return f"""You are writing a Reel Spec for a calming mental wellness short video. Return ONLY the JSON object, no prose, no code fence.

Contract, all required:
- Keys exactly: version, issue_number, slug, title, render_version, status, publication_status, format, sources, safety, beats
- version 1, issue_number {issue['number']}, slug "{slug}", render_version "1.0.0"
- status "ready_to_render", publication_status "human_review_required"
- format {{"width": 1080, "height": 1920, "fps": 30, "duration_seconds": N}} where N is between 32 and 42
- 6 or 7 beats. Beat times are contiguous, start at 0, and the last end equals duration_seconds
- Each beat: id, start, end, headline, body, and source_label only when the beat shows a number
- id: one or two lowercase words joined by a hyphen. It is drawn on screen in capitals, so make it a content word like "one-window", never "hook" or "beat-1"
- headline at most 52 characters. body at most 180 characters, except the LAST beat whose body is at most 120 characters because the safety line is drawn beneath it. source_label at most 40 characters
- sources: exactly ["{parts['source_url']}"]
- safety: exactly ["{parts['safety']}"] copied character for character

Copy rules, enforced by a validator that will reject the Spec:
- No em dashes anywhere
- Every number a viewer reads must appear in the evidence text below. If a number is not there, write the idea in words instead
- Any beat whose headline or body contains a digit must carry a source_label naming the source, for example "Meta-analysis, 2021"
- Forbidden words: cure, guarantee, prevents, eliminates, instantly, proven, you should, you must, you need to
- Warm, plain, adult. Contractions are good. One idea per sentence. Explain an unfamiliar term before advising anything
- Offer actions as optional: "You could try", "A good place to start"
- Never imply the viewer failed if something does not help
- Do not overstate the study. If it is observational, say linked or associated, never that it prevents anything

Structure: beat 1 is the hook with the strongest honest number. Beat 2 explains the idea in plain words. Middle beats each give one action. The last beat closes gently and does not add a new claim.

Title to use: {parts['title']}
Hook direction: {parts['hook']}
Reviewed finding, this is the ground truth: {parts['claim']}
Actions the reviewer approved: {parts['actions']}
Visual direction, for tone only: {parts['visual']}

Evidence text, the only place numbers may come from:
{parts['evidence']}
"""


def ask_model(prompt: str, model: str) -> dict:
    raw = run([model, "-p", prompt])
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else raw)


def build_spec(issue: dict, parts: dict[str, str], slug: str, model: str) -> dict:
    prompt = prompt_for(issue, parts, slug)
    failure = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            spec = ask_model(prompt + failure, model)
            validate_spec(spec)
            guard(spec, parts["evidence"], parts["safety"])
            if spec["slug"] != slug or spec["issue_number"] != issue["number"]:
                raise ValueError("slug or issue_number does not match the Issue")
            return spec
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            print(f"  attempt {attempt} rejected: {error}")
            failure = f"\n\nYour previous answer was rejected with this error. Fix exactly this and return the whole JSON again: {error}"
    raise RuntimeError(f"no valid Spec for Issue #{issue['number']} after {ATTEMPTS} attempts")


def issue_parts(issue: dict) -> dict[str, str]:
    parts = sections(issue["body"])
    evidence_block = parts.get("evidence this reel is built on", "")
    claim = ""
    for line in evidence_block.splitlines():
        if line.startswith("Reviewed finding:"):
            claim = line.split(":", 1)[1].strip()
    source = re.search(r"https://\S+", evidence_block)
    if not claim or not source:
        raise ValueError(f"Issue #{issue['number']} has no reviewed finding or source URL")
    citation = evidence_block.splitlines()[0].strip()
    return {
        "title": issue["title"].replace("[Topic Proposal] ", "").strip(),
        "hook": parts.get("hook", ""),
        "claim": claim,
        "actions": " | ".join(
            line.lstrip("- ").strip() for line in parts.get("possible actions", "").splitlines() if line.strip()
        ),
        "visual": parts.get("visual direction", ""),
        "safety": parts.get("safety boundary", "").split("\n\n")[0].strip(),
        "source_url": source.group().rstrip(")."),
        "evidence": f"{citation}\n{claim}",
    }


def publish(issue: dict, spec_path: Path) -> None:
    relative = spec_path.relative_to(ROOT).as_posix()
    run(["git", "-C", str(ROOT), "add", relative])
    run(["git", "-C", str(ROOT), "commit", "-m", f"feat: add Reel Spec for Issue #{issue['number']}"])
    run(["git", "-C", str(ROOT), "push", "origin", "HEAD:main"])
    run(["gh", "issue", "edit", str(issue["number"]), "--repo", REPOSITORY,
         "--remove-label", QUEUE_LABEL, "--add-label", "state:ready-to-render"])
    run(["gh", "workflow", "run", "render-spec.yml", "--repo", REPOSITORY,
         "-f", f"spec_path={relative}", "-f", f"issue_number={issue['number']}"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude", help="CLI that takes -p PROMPT and prints JSON")
    parser.add_argument("--issue", type=int, help="Only this Issue number")
    parser.add_argument("--dry-run", action="store_true", help="Write nothing, print the Spec")
    args = parser.parse_args()

    issues = [issue for issue in queued_issues() if args.issue in (None, issue["number"])]
    if not issues:
        print("nothing approved and waiting for a Reel Spec")
        return

    for issue in issues:
        print(f"Issue #{issue['number']}: {issue['title']}")
        parts = issue_parts(issue)
        slug = slugify(parts["title"])
        spec_path = SPECS / f"{slug}.json"
        if spec_path.exists():
            print(f"  spec already exists at {spec_path.relative_to(ROOT)}, skipping")
            continue
        spec = build_spec(issue, parts, slug, args.model)
        if args.dry_run:
            print(json.dumps(spec, indent=2))
            continue
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        publish(issue, spec_path)
        print(f"  rendered from {spec_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
