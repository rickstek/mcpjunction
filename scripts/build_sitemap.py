#!/usr/bin/env python3
"""
mcpjunction.ai sitemap builder

Walks dist/ (the Astro build output) and emits dist/sitemap.xml containing
ONLY files that actually exist on disk at build time. This is deliberate: the
standing rule is no dead links on day one, and a sitemap full of 404s is the
fastest way to lose search and agent trust.

Must run AFTER `astro build`. dist/ is cleared on each build, so this step is
part of the build pipeline (never committed to git).

lastmod comes from the dataset's generated_at for data-derived pages and from
file mtime for hand-written pages.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = "https://mcpjunction.ai"

# Files that exist but should not be advertised to crawlers.
EXCLUDE_NAMES = {"404.html", "listing_schema_template.html"}

# Non-HTML machine-readable endpoints worth listing.
EXTRA_PATHS = ["/data/mcp_servers.json", "/data/mcp_servers.csv"]

PRIORITY = {
    "/": "1.0",
    "/licensing": "0.8",
    "/data/mcp_servers.json": "0.9",
}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def url_path(p: Path) -> str:
    """Return the CANONICAL url Cloudflare serves at 200.

    html_handling is auto-trailing-slash, so:
      index.html         -> /
      licensing.html     -> /licensing        (/licensing.html 307s here)
      folder/index.html  -> /folder/
    Listing the .html form in a sitemap would advertise a redirect, which
    wastes crawl budget and muddies canonicalisation.
    """
    rel = p.relative_to(DIST).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel.endswith(".html"):
        return "/" + rel[: -len(".html")]
    return "/" + rel


def main() -> None:
    dataset_date = None
    ds = DIST / "data" / "mcp_servers.json"
    if ds.exists():
        try:
            gen = json.loads(ds.read_text(encoding="utf-8")).get("generated_at", "")
            dataset_date = gen[:10] or None
        except Exception:  # noqa: BLE001
            pass

    entries = []
    seen = set()

    for p in sorted(DIST.rglob("*.html")):
        if p.name in EXCLUDE_NAMES:
            continue
        loc = url_path(p)
        if loc in seen:
            continue
        seen.add(loc)
        entries.append((loc, iso(p.stat().st_mtime)))

    for extra in EXTRA_PATHS:
        f = DIST / extra.lstrip("/")
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
    out = DIST / "sitemap.xml"
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
