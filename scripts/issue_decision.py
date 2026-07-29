#!/usr/bin/env python3
"""Validate the mutually exclusive decision checkboxes in a topic Issue."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

APPROVE_LABEL = "Approve for research"
REJECT_LABEL = "Reject"
CHECKBOX = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.+?)\s*$", re.MULTILINE)


def parse_decision(body: str) -> str:
    states: dict[str, list[bool]] = {APPROVE_LABEL: [], REJECT_LABEL: []}
    for mark, label in CHECKBOX.findall(body):
        if label in states:
            states[label].append(mark.lower() == "x")

    if any(len(values) != 1 for values in states.values()):
        return "invalid"

    approve = states[APPROVE_LABEL][0]
    reject = states[REJECT_LABEL][0]
    if approve == reject:
        return "invalid"
    return "approve" if approve else "reject"


def event_outputs(event: dict) -> dict[str, str]:
    issue = event.get("issue", {})
    decision = parse_decision(issue.get("body") or "")
    previous_body = event.get("changes", {}).get("body", {}).get("from")
    previous_decision = parse_decision(previous_body) if isinstance(previous_body, str) else "unknown"
    return {
        "decision": decision,
        "previous_decision": previous_decision,
        "decision_changed": str(decision != previous_decision).lower(),
        "issue_number": str(issue.get("number", "")),
        "is_topic": str(any(label.get("name") == "topic-proposal" for label in issue.get("labels", []))).lower(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    event = json.loads(args.event.read_text(encoding="utf-8"))
    output = event_outputs(event)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            for key, value in output.items():
                stream.write(f"{key}={value}\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
