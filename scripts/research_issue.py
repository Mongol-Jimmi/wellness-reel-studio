#!/usr/bin/env python3
"""Discover OpenAlex evidence candidates for one approved topic Issue."""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener

QUERY = re.compile(r"<!--\s*research-query:\s*(.*?)\s*-->")
EVIDENCE_SECTION = re.compile(
    r"^## Evidence question\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
OPENALEX = "https://api.openalex.org/works"
MAX_RESPONSE_BYTES = 2_000_000


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def open_request(request: Request):
    opener = build_opener(NoRedirectHandler())
    return opener.open(request, timeout=30)  # nosec B310: fixed HTTPS host, redirects disabled


def extract_query(body: str) -> str:
    metadata = QUERY.search(body)
    section = EVIDENCE_SECTION.search(body)
    raw_query = metadata.group(1) if metadata else section.group(1) if section else ""
    query = html.unescape(HTML_COMMENT.sub("", raw_query)).strip()
    if len(query) < 8 or len(query) > 500:
        raise ValueError("Issue needs an evidence question between 8 and 500 characters")
    return query


def markdown_text(value: object, fallback: str = "unavailable") -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    flattened = " ".join(value.split())[:500]
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", flattened)


def search_terms(query: str) -> str:
    """Strip OpenAlex wildcards, which its stemmed search rejects with HTTP 400."""
    return " ".join(re.sub(r"[*?]", " ", query).split())


def discover(query: str, limit: int = 10) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "search": search_terms(query),
            "per-page": min(max(limit, 1), 10),
            "select": "id,display_name,publication_year,doi,primary_location,authorships,cited_by_count",
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

    candidates = []
    for work in payload["results"][:10]:
        if not isinstance(work, dict):
            continue
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        authors = [
            entry.get("author", {}).get("display_name")
            for entry in work.get("authorships", [])[:5]
            if entry.get("author", {}).get("display_name")
        ]
        candidates.append(
            {
                "title": work.get("display_name"),
                "year": work.get("publication_year") if isinstance(work.get("publication_year"), int) else None,
                "authors": authors,
                "doi": work.get("doi"),
                "openalex": work.get("id"),
                "source": source.get("display_name"),
                "cited_by_count": work.get("cited_by_count")
                if isinstance(work.get("cited_by_count"), int) and not isinstance(work.get("cited_by_count"), bool)
                else 0,
                "human_review_required": True,
            }
        )
    return candidates


def write_markdown(path: Path, issue_number: int, query: str, candidates: list[dict]) -> None:
    lines = [
        f"# Evidence candidates for Issue #{issue_number}",
        "",
        f"**Discovery query:** {markdown_text(query)}",
        "",
        "> These are discovery leads, not proof. Human full-text review is required.",
        "",
    ]
    for index, candidate in enumerate(candidates, 1):
        authors = ", ".join(markdown_text(author) for author in candidate["authors"]) or "Authors unavailable"
        links = " · ".join(markdown_text(link) for link in (candidate["doi"], candidate["openalex"]) if link)
        lines.extend(
            [
                f"## {index}. {markdown_text(candidate['title'])}",
                "",
                f"{authors} ({candidate['year'] or 'year unavailable'})",
                "",
                f"Source: {markdown_text(candidate['source'])} · Cited by: {candidate['cited_by_count']}",
                "",
                links,
                "",
                "Review: methods, sample, outcome, relevance, limitations, conflicts, and full-text context.",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("research-output"))
    args = parser.parse_args()

    query = extract_query(args.body_file.read_text(encoding="utf-8"))
    candidates = discover(query)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "issue_number": args.issue_number,
        "query": query,
        "provider": "OpenAlex",
        "human_review_required": True,
        "candidates": candidates,
    }
    (args.output_dir / "candidates.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_dir / "candidates.md", args.issue_number, query, candidates)
    print(f"Discovered {len(candidates)} evidence candidates for Issue #{args.issue_number}")


if __name__ == "__main__":
    main()
