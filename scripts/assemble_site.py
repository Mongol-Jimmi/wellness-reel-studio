#!/usr/bin/env python3
"""Assemble and validate the static GitHub Pages artifact."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
MEDIA_ROOTS = {"media": ROOT / "previews", "captions": ROOT / "edit"}


def source_for(relative_url: str) -> Path:
    path = PurePosixPath(relative_url)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 2:
        raise ValueError(f"unsafe local asset path: {relative_url}")
    source_root = MEDIA_ROOTS.get(path.parts[0])
    if source_root is None:
        raise ValueError(f"unsupported local asset path: {relative_url}")
    source = source_root / path.name
    if not source.is_file():
        raise FileNotFoundError(source)
    return source


def assemble(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ("index.html", "styles.css", "dashboard.js", "reels.json"):
        shutil.copy2(SITE_SOURCE / name, output / name)

    reels = json.loads((SITE_SOURCE / "reels.json").read_text(encoding="utf-8"))
    if not isinstance(reels, list):
        raise TypeError("site/reels.json must be an array")
    for reel in reels:
        for field in ("slug", "title", "status", "duration", "resolution", "renderVersion", "sourceIssue", "video"):
            if not reel.get(field):
                raise ValueError(f"static preview is missing {field}")
        local_assets = [reel["video"], reel.get("poster")]
        local_assets.extend(url for url in reel.get("links", {}).values() if not url.startswith("https://"))
        for relative_url in filter(None, local_assets):
            source = source_for(relative_url)
            destination = output / relative_url
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("site-dist"))
    args = parser.parse_args()
    assemble(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
