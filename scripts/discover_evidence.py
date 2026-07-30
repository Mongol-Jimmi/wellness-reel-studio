#!/usr/bin/env python3
"""Evidence-first discovery. Sweep reviews and meta-analyses, then propose Reel topics from what the evidence supports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
from pathlib import Path
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.research_issue import (
    HUMAN_FIELDS,
    MAX_RESPONSE_BYTES,
    OPENALEX,
    markdown_text,
    open_request,
    search_terms,
)

# Wellness domains to sweep. Edit this list to steer what the channel can talk about.
SEEDS = (
    "sleep AND insomnia AND behavioural intervention",
    "breathwork AND slow breathing AND stress",
    "physical activity AND mood AND depression",
    "mindfulness AND perceived stress",
    "habit formation AND behaviour change technique",
    "implementation intentions AND goal attainment",
    "nature exposure AND green space AND mental health",
    "rumination AND worry AND perseverative cognition",
    "loneliness AND social connection AND intervention",
    "self-compassion AND self-criticism",
    "screen time AND smartphone use AND wellbeing",
    "daylight AND light exposure AND circadian",
)
MIN_YEAR = 2015
MIN_CITATIONS = 25
CURRENT_YEAR = 2026
MAX_LIVE_REQUESTS = 12
ELICIT_STUDY_TYPES = ("Systematic Review", "Meta-Analysis", "RCT")


def abstract_text(inverted_index: object) -> str:
    """Rebuild an abstract from the OpenAlex inverted index."""
    if not isinstance(inverted_index, dict):
        return ""
    positions: dict[int, str] = {}
    for word, places in inverted_index.items():
        if not isinstance(word, str) or not isinstance(places, list):
            continue
        for place in places:
            if isinstance(place, int):
                positions[place] = word
    return " ".join(positions[index] for index in sorted(positions))


def fetch_elicit(client, seed: str, per_seed: int) -> list[dict]:
    """One paid Elicit request per seed. Semantic search filtered to review, meta-analysis, and RCT."""
    cards = []
    for paper in client.search_papers(
        seed.replace(" AND ", " "),
        max_results=min(max(per_seed, 1), 25),
        min_year=MIN_YEAR,
        study_types=ELICIT_STUDY_TYPES,
    ):
        doi = f"https://doi.org/{paper.doi}" if paper.doi and not paper.doi.startswith("http") else paper.doi
        cards.append(
            {
                "seed": seed,
                "provider": "Elicit",
                "id": doi or paper.elicit_id or paper.title,
                "title": paper.title,
                "year": paper.year,
                "authors": list(paper.authors[:5]),
                "doi": doi,
                "source": paper.venue,
                "cited_by_count": paper.cited_by_count or 0,
                "abstract": (paper.abstract or "")[:2000],
                "human_review_required": True,
            }
        )
    return cards


def fetch(seed: str, per_seed: int) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "filter": ",".join(
                [
                    f"title_and_abstract.search:{search_terms(seed)}",
                    f"primary_topic.field.id:{HUMAN_FIELDS}",
                    "type:review",
                    f"publication_year:>{MIN_YEAR - 1}",
                    f"cited_by_count:>{MIN_CITATIONS - 1}",
                ]
            ),
            "sort": "cited_by_count:desc",
            "per-page": min(max(per_seed, 1), 25),
            "select": "id,display_name,publication_year,doi,primary_location,authorships,cited_by_count,abstract_inverted_index",
            "mailto": "kiranjasonshu@gmail.com",
        }
    )
    request = Request(
        f"{OPENALEX}?{params}",
        headers={"User-Agent": "wellness-reel-studio/1.0 (mailto:kiranjasonshu@gmail.com)"},
    )
    with open_request(request) as response:
        raw_payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw_payload) > MAX_RESPONSE_BYTES:
        raise ValueError("OpenAlex response exceeded the size limit")
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise TypeError("OpenAlex returned an invalid response")

    cards = []
    for work in payload["results"]:
        if not isinstance(work, dict) or not isinstance(work.get("id"), str):
            continue
        source = (work.get("primary_location") or {}).get("source") or {}
        cards.append(
            {
                "seed": seed,
                "provider": "OpenAlex",
                "id": work["id"],
                "title": work.get("display_name"),
                "year": work.get("publication_year") if isinstance(work.get("publication_year"), int) else None,
                "authors": [
                    entry.get("author", {}).get("display_name")
                    for entry in work.get("authorships", [])[:5]
                    if entry.get("author", {}).get("display_name")
                ],
                "doi": work.get("doi"),
                "source": source.get("display_name"),
                "cited_by_count": work.get("cited_by_count") if isinstance(work.get("cited_by_count"), int) else 0,
                "abstract": abstract_text(work.get("abstract_inverted_index"))[:2000],
                "human_review_required": True,
            }
        )
    return cards


def rank(cards: list[dict]) -> list[dict]:
    """Dedupe by work, then order by citations per year since publication."""
    unique: dict[str, dict] = {}
    for card in cards:
        unique.setdefault(card["id"], card)

    # ponytail: citations per year is a crude strength proxy. A human still reads every abstract.
    def score(card: dict) -> float:
        age = max(1, CURRENT_YEAR - (card["year"] or CURRENT_YEAR) + 1)
        return card["cited_by_count"] / age

    return sorted(unique.values(), key=score, reverse=True)


def write_cards(output_dir: Path, cards: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cards.json").write_text(
        json.dumps({"human_review_required": True, "cards": cards}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Evidence-first candidates",
        "",
        "> Reviews and meta-analyses found before any topic existed. Discovery leads, not proof.",
        "> A human reads the full text and writes the claim. Nothing here is publication approved.",
        "",
    ]
    for index, card in enumerate(cards, 1):
        authors = ", ".join(markdown_text(author) for author in card["authors"]) or "Authors unavailable"
        links = " · ".join(
            markdown_text(link) for link in dict.fromkeys(value for value in (card["doi"], card["id"]) if value)
        )
        lines.extend(
            [
                f"## {index}. {markdown_text(card['title'])}",
                "",
                f"{authors} ({card['year'] or 'year unavailable'})",
                "",
                f"Source: {markdown_text(card['source'])} · Cited by: {card['cited_by_count']} · Found by: {markdown_text(card['provider'])} · Seed: {markdown_text(card['seed'])}",
                "",
                links,
                "",
                f"Abstract: {markdown_text(card['abstract'], 'abstract unavailable')}",
                "",
            ]
        )
    (output_dir / "cards.md").write_text("\n".join(lines), encoding="utf-8")


def issue_body(card: dict, claim: str, hook: str, actions: list[str], visual: str, safety: str) -> str:
    action_lines = "\n".join(f"- {action}" for action in actions)
    citation = f"{card['title']} ({card['year']}), {card['source']}"
    return f"""## Hook

{hook}

## Evidence this Reel is built on

{citation}

{card['doi'] or card['id']}

Reviewed finding: {claim}

## Possible actions

{action_lines}

## Evidence question

{card['seed']}

## Visual direction

{visual}

## Safety boundary

{safety}

The paper above is a discovery lead until a human confirms the full text, methods, relevance, and limitations.

## Decision

Select exactly one. Approval starts scripting from the evidence above. It does not approve claims, rendering, or publication.

- [ ] Approve for research
- [ ] Reject

<!-- source-id: {card['id']} -->
<!-- research-query: {card['seed']} -->
"""


def create_issue(repo: str, title: str, body: str) -> str:
    completed = subprocess.run(
        [
            "gh", "issue", "create", "--repo", repo,
            "--title", f"[Topic Proposal] {title}",
            "--body", body,
            "--label", "topic-proposal,state:evidence-review,human-review-required",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("research/generated/evidence-first"))
    parser.add_argument("--per-seed", type=int, default=5)
    parser.add_argument("--seed", action="append", help="Override the seed list. Repeatable.")
    parser.add_argument(
        "--provider",
        choices=("elicit", "openalex"),
        default="elicit",
        help="elicit spends one paid request per seed. openalex is free and less precise.",
    )
    parser.add_argument("--propose", help="Path to a JSON proposal file built from one evidence card")
    parser.add_argument("--repo", default="Mongol-Jimmi/wellness-reel-studio")
    parser.add_argument("--apply", action="store_true", help="Create the Issue. Default is a dry run.")
    args = parser.parse_args()

    if args.propose:
        proposal = json.loads(Path(args.propose).read_text(encoding="utf-8"))
        body = issue_body(
            proposal["card"],
            proposal["claim"],
            proposal["hook"],
            proposal["actions"],
            proposal["visual"],
            proposal["safety"],
        )
        if "—" in body:
            raise ValueError("proposal contains an em dash")
        if not args.apply:
            print(body)
            return
        print(create_issue(args.repo, proposal["title"], body))
        return

    seeds = list(dict.fromkeys(args.seed or SEEDS))
    cards = []
    if args.provider == "elicit":
        if len(seeds) > MAX_LIVE_REQUESTS:
            raise SystemExit(f"{len(seeds)} seeds would exceed the {MAX_LIVE_REQUESTS} request ceiling")
        from src.elicit_client import ElicitClient

        client = ElicitClient.from_environment()
        print(f"Elicit live search: {len(seeds)} requests against the paid plan quota")
        for seed in seeds:
            cards.extend(fetch_elicit(client, seed, args.per_seed))
    else:
        for seed in seeds:
            cards.extend(fetch(seed, args.per_seed))
    ranked = rank(cards)
    write_cards(args.output_dir, ranked)
    print(f"Found {len(ranked)} unique evidence candidates across {len(seeds)} seeds via {args.provider}")


if __name__ == "__main__":
    main()
