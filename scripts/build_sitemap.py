#!/usr/bin/env python3
"""
mcpjunction.ai sitemap builder

Walks public/ and emits public/sitemap.xml containing ONLY files that actually
exist on disk at build time. This is deliberate: the standing rule is no dead
links on day one, and a sitemap full of 404s is the fastest way to lose search
and agent trust. When the Astro server pages ship, they land in public/ and
get picked up automatically — no edit needed here.

lastmod comes from the dataset's generated_at for data-derived pages and from
file mtime for hand-written pages.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
BASE = "https://mcpjunction.ai"

# Files that exist but should not be advertised to crawlers.
EXCLUDE_NAMES = {"404.html", "listing_schema_template.html"}

# Non-HTML machine-readable endpoints worth listing.
EXTRA_PATHS = ["/data/mcp_servers.json", "/data/mcp_servers.csv"]

PRIORITY = {
    "/": "1.0",
    "/licensing.html": "0.8",
    "/data/mcp_servers.json": "0.9",
}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def url_path(p: Path) -> str:
    rel = p.relative_to(PUBLIC).as_posix()
    if rel == "index.html":
        return "/"
    return "/" + rel


def main() -> None:
    dataset_date = None
    ds = PUBLIC / "data" / "mcp_servers.json"
    if ds.exists():
        try:
            gen = json.loads(ds.read_text()).get("generated_at", "")
            dataset_date = gen[:10] or None
        except Exception:  # noqa: BLE001
            pass

    entries = []
    seen = set()

    for p in sorted(PUBLIC.rglob("*.html")):
        if p.name in EXCLUDE_NAMES:
            continue
        loc = url_path(p)
        if loc in seen:
            continue
        seen.add(loc)
        entries.append((loc, iso(p.stat().st_mtime)))

    for extra in EXTRA_PATHS:
        f = PUBLIC / extra.lstrip("/")
        if f.exists() and extra not in seen:
            seen.add(extra)
            entries.append((extra, dataset_date or iso(f.stat().st_mtime)))

    urlset = ET.Element("urlset",
                        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for loc, lastmod in sorted(entries):
        el = ET.SubElement(urlset, "url")
        ET.SubElement(el, "loc").text = BASE + loc
        ET.SubElement(el, "lastmod").text = lastmod
        ET.SubElement(el, "changefreq").text = (
            "daily" if loc.startswith("/data/") else "weekly")
        ET.SubElement(el, "priority").text = PRIORITY.get(loc, "0.6")

    ET.indent(urlset, space="  ")
    out = PUBLIC / "sitemap.xml"
    out.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(urlset, encoding="utf-8")
        + b"\n"
    )
    print(f"wrote {out.relative_to(ROOT)} with {len(entries)} URLs:")
    for loc, lastmod in sorted(entries):
        print(f"  {loc}  ({lastmod})")


if __name__ == "__main__":
    main()
