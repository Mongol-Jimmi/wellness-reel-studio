#!/usr/bin/env python3
"""Assemble and validate the static GitHub Pages artifact."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
MEDIA_ROOTS = {"media": ROOT / "previews", "captions": ROOT / "edit"}
REPOSITORY = "Mongol-Jimmi/wellness-reel-studio"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/preview-assets"
ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
MAX_ASSET_BYTES = 60_000_000


def safe_asset_name(name: object) -> str:
    """Release asset names are external input and become file paths in the artifact."""
    if not isinstance(name, str) or not ASSET_NAME.fullmatch(name) or ".." in name:
        raise ValueError(f"unsafe release asset name: {name!r}")
    return name


def download(url: str, limit: int = MAX_ASSET_BYTES, accept: str = "application/octet-stream") -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"release asset must use HTTPS: {url!r}")
    request = Request(url, headers={"User-Agent": "wellness-reel-studio/1.0", "Accept": accept})
    with urlopen(request, timeout=60) as response:  # nosec B310: HTTPS enforced above
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError(f"release asset exceeded {limit} bytes: {url!r}")
    return payload


def release_previews(output: Path) -> list[dict]:
    """Bake rendered previews into the artifact.

    Release assets answer without an Access-Control-Allow-Origin header, so the
    dashboard cannot fetch them from the Pages origin. The build copies them in.
    """
    try:
        payload = json.loads(download(RELEASE_API, limit=2_000_000, accept="application/vnd.github+json"))
    except HTTPError as error:
        if error.code != 404:
            raise
        print("warning: no preview-assets release yet, only static previews are baked in")
        return []
    except URLError as error:
        raise RuntimeError(f"could not reach {RELEASE_API}: {error.reason}") from None

    assets = {safe_asset_name(asset.get("name")): asset.get("browser_download_url") for asset in payload.get("assets", [])}
    reels = []
    for name in sorted(assets):
        if not name.endswith(".preview.json"):
            continue
        preview = json.loads(download(assets[name], limit=2_000_000))
        files = {
            "media": [safe_asset_name(preview["videoFile"]), safe_asset_name(preview["posterFile"])],
            "captions": [safe_asset_name(preview["captionsFile"])],
        }
        for directory, filenames in files.items():
            for filename in filenames:
                if filename not in assets:
                    raise FileNotFoundError(f"release is missing {filename}")
                destination = output / directory / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(download(assets[filename]))
        reels.append(
            {
                "slug": preview["slug"],
                "title": preview["title"],
                "status": preview["status"],
                "duration": preview["duration"],
                "resolution": preview["resolution"],
                "renderVersion": preview["renderVersion"],
                "sourceIssue": f"Issue #{preview['issueNumber']}",
                "video": f"media/{preview['videoFile']}",
                "poster": f"media/{preview['posterFile']}",
                "links": {
                    "Captions": f"captions/{preview['captionsFile']}",
                    "Issue": f"https://github.com/{REPOSITORY}/issues/{preview['issueNumber']}",
                    "Reel Spec": f"https://github.com/{REPOSITORY}/blob/main/{preview['specPath']}",
                    "Evidence": preview["sources"][0],
                },
            }
        )
    return reels


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


def assemble(output: Path, include_release: bool = False) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ("index.html", "styles.css", "dashboard.js"):
        shutil.copy2(SITE_SOURCE / name, output / name)

    reels = json.loads((SITE_SOURCE / "reels.json").read_text(encoding="utf-8"))
    if not isinstance(reels, list):
        raise TypeError("site/reels.json must be an array")
    generated = release_previews(output) if include_release else []
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

    (output / "reels.json").write_text(json.dumps(reels + generated, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("site-dist"))
    parser.add_argument(
        "--with-release",
        action="store_true",
        help="Bake rendered previews from the preview-assets release into the artifact.",
    )
    args = parser.parse_args()
    assemble(args.output, include_release=args.with_release)
    print(args.output)


if __name__ == "__main__":
    main()
