#!/usr/bin/env python3
"""Create the reviewed topic proposals as GitHub Issues."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REQUIRED_FIELDS = {
    "id",
    "title",
    "hook",
    "actions",
    "research_query",
    "visual",
    "rationale",
    "score",
    "safety",
}


def validate(proposals: list[dict]) -> None:
    if len(proposals) != 10:
        raise ValueError(f"Expected exactly 10 proposals, found {len(proposals)}")
    ids = [proposal.get("id") for proposal in proposals]
    if len(set(ids)) != len(ids):
        raise ValueError("Proposal IDs must be unique")
    for proposal in proposals:
        missing = REQUIRED_FIELDS - proposal.keys()
        if missing:
            raise ValueError(f"{proposal.get('id', 'unknown')} missing: {sorted(missing)}")
        if not 2 <= len(proposal["actions"]) <= 4:
            raise ValueError(f"{proposal['id']} must include 2 to 4 actions")
        serialized = json.dumps(proposal, ensure_ascii=False)
        if "—" in serialized:
            raise ValueError(f"{proposal['id']} contains an em dash")


def issue_body(proposal: dict) -> str:
    actions = "\n".join(f"- {action}" for action in proposal["actions"])
    return f"""## Hook

{proposal['hook']}

## Why it fits

{proposal['rationale']}

## Possible actions

{actions}

## Evidence question

{proposal['research_query']}

## Visual direction

{proposal['visual']}

## Safety boundary

{proposal['safety']}

All discovered papers remain evidence candidates until a human reviews the full text, methods, relevance, and limitations.

## Decision

Select exactly one. Approval starts research and scripting. It does not approve claims, rendering, or publication.

- [ ] Approve for research
- [ ] Reject

<!-- topic-id: {proposal['id']} -->
<!-- research-query: {proposal['research_query']} -->
"""


def create_issue(repo: str, proposal: dict) -> str:
    command = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        f"[Topic Proposal] {proposal['title']}",
        "--body",
        issue_body(proposal),
        "--label",
        "topic-proposal,state:proposed,human-review-required",
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("ideas/proposals.json"))
    parser.add_argument("--repo", default="Mongol-Jimmi/wellness-reel-studio")
    parser.add_argument("--apply", action="store_true", help="Create Issues. Default is a dry run.")
    args = parser.parse_args()

    proposals = json.loads(args.input.read_text(encoding="utf-8"))
    validate(proposals)
    if not args.apply:
        for proposal in proposals:
            print(f"[dry-run] {proposal['id']}: {proposal['title']}")
        return

    for proposal in proposals:
        print(create_issue(args.repo, proposal))


if __name__ == "__main__":
    main()
