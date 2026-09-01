#!/usr/bin/env python3
"""
mcpjunction.ai sitemap builder

Walks dist/ (the Astro build output) and emits dist/sitemap.xml containing
ONLY files that actually exist on disk at build time. This is deliberate: the
standing rule is no dead links on day one, and a sitemap full of 404s is the
fastest way to lose search and agent trust.

Must run AFTER `astro build`. dist/ is cleared on each build, so this step is
part of the build pipeline (never committed to git).

Two behaviours beyond "list the files":

1. Any page that declares `<meta name="robots" content="noindex">` is left out
   entirely. The template decides — delisted servers, the uncategorized holding
   pen — and the sitemap follows, so the two can never disagree.

2. `lastmod` is content-derived. Previously it came from file mtime, and since
   dist/ is rebuilt from scratch every night every URL carried the same date;
   Google's documented response to a sitemap whose lastmod values are all
   identical and always current is to ignore lastmod for the whole site. Each
   URL now gets a signature over the fields that actually render, stored in
   state/lastmod.json, and keeps its previous date until that signature moves.

   The signature for a server page deliberately EXCLUDES stars, forks, open
   issues and pushed_at. Those churn constantly — measured over two consecutive
   nightlies, 940 of 1,830 servers changed their star count and 504 changed
   pushed_at, against 25 that changed anything a reader would call an edit.
   Including them would recreate the uniform-lastmod problem and flood
   IndexNow. lastmod means "last significant modification", and an upstream
   star ticking over is not one.

The URLs whose signature moved are written to state/changed_urls.txt for the
IndexNow step, so the nightly submits the night's actual changes instead of
resubmitting the entire site.
"""

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STATE_DIR = ROOT / "state"
STATE_PATH = STATE_DIR / "lastmod.json"
CHANGED_PATH = STATE_DIR / "changed_urls.txt"
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

# The fields a server page renders that constitute an edit to the entry.
# Counters and upstream timestamps are excluded on purpose — see the module
# docstring.
SERVER_SIG_FIELDS = (
    "github_repo_id", "name", "full_name", "owner", "description", "category",
    "topics", "language", "license", "homepage", "install_hint", "status",
    "delisted_at", "editorial_summary", "security_reviewed", "verified_badge",
    "sponsor_tier",
)

# What a category page renders for each of its members. Star counts (and so
# the ordering) are left out for the same reason as above.
MEMBER_SIG_FIELDS = (
    "id", "name", "owner", "language", "description", "status",
    "security_reviewed", "sponsor_tier",
)

# Never blast the whole site at IndexNow, whatever the signatures say.
CHANGED_URL_CAP = 2000

# Source extensions that feed the template signature. An allowlist, not a
# denylist: a file type nobody anticipated should be ignored, not counted.
TEMPLATE_SUFFIXES = {
    ".astro", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".json",
}

# Templates every data-derived page depends on, whatever surface it is.
SHARED_TEMPLATE_DIRS = ("src/layouts/", "src/components/", "src/lib/")

# Page templates per surface. A server page does not change because a category
# template did, so they no longer share one signature.
SERVER_TEMPLATE_DIRS = ("src/pages/servers/",)
CATEGORY_TEMPLATE_DIRS = ("src/pages/categories/",)
TOPIC_TEMPLATE_DIRS = ("src/pages/topics/",)

# Bumped whenever signature CONSTRUCTION changes, so a scheme change is not
# mistaken for 1,800 pages changing at once. See the migration in main().
SIG_SCHEME = 2


def sig(obj) -> str:
    """Stable signature for any JSON-serialisable structure."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def byte_sig(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()[:32]


def declares_noindex(html: bytes) -> bool:
    """True if the document carries a robots meta tag asking for noindex.

    Scans whole <meta> tags rather than matching attribute order, so it
    survives however Astro's compressHTML chooses to emit them.
    """
    for m in re.finditer(rb"<meta\b[^>]*>", html, re.IGNORECASE):
        tag = m.group(0).lower()
        if b"robots" in tag and b"noindex" in tag:
            return True
    return False


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


def load_dataset() -> dict:
    ds = DIST / "data" / "mcp_servers.json"
    if not ds.exists():
        return {}
    return json.loads(ds.read_text(encoding="utf-8"))


def template_signature(page_dirs=()) -> str:
    """Signature over the templates that render one surface of data-derived pages.

    Data signatures alone would report "unchanged" after a template rewrite,
    which is false — the SEO phase changed every server page's title, H1,
    JSON-LD and topic list without touching one dataset field.

    Scoped per surface: the shared directories count for everything, but a
    page template counts only for the pages it actually renders. This used to
    hash all of src/ into one value folded into every page, so a four-line
    edit to a category heading -- which changed exactly one rendered page --
    reset lastmod on all 1,899 URLs and submitted them to IndexNow, which is
    the uniform-lastmod state this file exists to prevent. Pass ("src/",) to
    reproduce that original single-value behaviour, which the scheme
    migration in main() uses to tell a real change from a rescoping.

    Restricted to source extensions, and skips dotfiles, so the signature is
    the same on a developer's machine as in CI. Hashing "everything under
    src/" would let one stray .DS_Store or editor swap file flip every
    data-derived URL at once, for no change anyone made.
    """
    allowed = SHARED_TEMPLATE_DIRS + tuple(page_dirs)
    parts = []
    for p in sorted((ROOT / "src").rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEMPLATE_SUFFIXES:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if any(seg.startswith(".") for seg in rel.split("/")):
            continue
        if not rel.startswith(allowed):
            continue
        parts.append(rel)
        parts.append(byte_sig(p.read_bytes()))
    return sig(parts)


def build_signatures(dataset: dict, legacy: bool = False) -> dict:
    """Content signature per URL for the data-derived pages.

    legacy=True reproduces scheme 1, where a single all-of-src/ value was
    folded into every page. Only the scheme migration uses it.
    """
    servers = dataset.get("servers", [])
    if legacy:
        tpl_server = tpl_cat = tpl_topic = template_signature(("src/",))
    else:
        tpl_server = template_signature(SERVER_TEMPLATE_DIRS)
        tpl_cat = template_signature(CATEGORY_TEMPLATE_DIRS)
        tpl_topic = template_signature(TOPIC_TEMPLATE_DIRS)
    out = {}

    for s in servers:
        out[f"/servers/{s['id']}"] = sig([tpl_server] + [s.get(f) for f in SERVER_SIG_FIELDS])

    try:
        cats = json.loads((ROOT / "categories.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"REFUSING TO BUILD SITEMAP: cannot read categories.json ({exc})")

    by_cat = {}
    for s in servers:
        if s.get("status") == "active":
            by_cat.setdefault(s.get("category"), []).append(s)

    for c in cats["categories"]:
        members = sorted(by_cat.get(c["slug"], []), key=lambda s: s["id"])
        payload = {
            "template": tpl_cat,
            "name": c.get("name"),
            "description": c.get("description"),
            "noindex": c.get("noindex", False),
            "members": [[m.get(f) for f in MEMBER_SIG_FIELDS] for m in members],
        }
        # Only present once written. Adding the key unconditionally would change
        # every category's signature the moment intros became possible, which is
        # a signature-CONSTRUCTION change and would need a SIG_SCHEME bump; this
        # way an unwritten category hashes exactly as it always did.
        if c.get("intro"):
            payload["intro"] = c["intro"]
        out[f"/categories/{c['slug']}"] = sig(payload)

    # Topic pages: exact membership over the topics array, mirroring the
    # template's own filter. A missing topics.json is fine (pre-namespace
    # state); a corrupt one is not.
    topics_path = ROOT / "topics.json"
    if topics_path.exists():
        try:
            topics_raw = json.loads(topics_path.read_text(encoding="utf-8"))
            topic_list = topics_raw["topics"]
            topic_intros = topics_raw.get("intros") or {}
        except (OSError, ValueError, KeyError) as exc:
            sys.exit(f"REFUSING TO BUILD SITEMAP: cannot read topics.json ({exc})")
        actives = [s for s in servers if s.get("status") == "active"]
        for tag in topic_list:
            members = sorted(
                (s for s in actives
                 if any(str(t).lower() == tag for t in (s.get("topics") or []))),
                key=lambda s: s["id"],
            )
            payload = {
                "template": tpl_topic,
                "tag": tag,
                "noindex": len(members) < 10,
                "members": [[m.get(f) for f in MEMBER_SIG_FIELDS] for m in members],
            }
            if topic_intros.get(tag):
                payload["intro"] = topic_intros[tag]
            out[f"/topics/{tag}"] = sig(payload)

    return out


def main() -> None:
    dataset = load_dataset()
    data_signatures = build_signatures(dataset)

    today = datetime.now(timezone.utc).date().isoformat()

    entries = []          # (loc, lastmod)
    signatures = {}       # loc -> signature
    seen = set()
    skipped_noindex = []

    for p in sorted(DIST.rglob("*.html")):
        if p.name in EXCLUDE_NAMES:
            continue
        loc = url_path(p)
        if loc in seen:
            continue
        html = p.read_bytes()
        if declares_noindex(html):
            skipped_noindex.append(loc)
            continue
        seen.add(loc)
        # Data-derived pages get a signature over the data. Everything else
        # (homepage, /categories, /data, /licensing) gets one over its own
        # rendered bytes, which is exact for hand-written pages and honest for
        # the few whose counts genuinely move nightly.
        signatures[loc] = data_signatures.get(loc) or byte_sig(html)

    for extra in EXTRA_PATHS:
        f = DIST / extra.lstrip("/")
        if f.exists() and extra not in seen:
            seen.add(extra)
            signatures[extra] = byte_sig(f.read_bytes())

    # --- lastmod state -----------------------------------------------------
    previous = {}
    prev_scheme = None
    bootstrap = True
    if STATE_PATH.exists():
        try:
            raw_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            previous = raw_state.get("urls", {})
            prev_scheme = raw_state.get("_scheme", 1)
            bootstrap = not previous
        except ValueError as exc:
            # A corrupt state file must not silently reset every date to today
            # and then fire 1,800 IndexNow submissions.
            sys.exit(f"REFUSING TO BUILD SITEMAP: {STATE_PATH} is unreadable ({exc})")

    # Changing how a signature is BUILT changes it for every page, which would
    # look identical to every page changing. On the run that first sees a new
    # scheme, recompute the old signatures too: a page whose old signature
    # still matches did not change, so it keeps its date and quietly adopts
    # the new one. A page that fails both is a genuine change and is reported
    # normally, so real edits are never masked by the migration.
    migrating = bool(previous) and prev_scheme != SIG_SCHEME
    legacy_signatures = build_signatures(dataset, legacy=True) if migrating else {}
    migrated = 0

    changed = []
    new_state = {}
    for loc, s in signatures.items():
        old = previous.get(loc)
        if old and old.get("sig") == s and old.get("lastmod"):
            lastmod = old["lastmod"]
        elif (migrating and old and old.get("lastmod")
              and old.get("sig") == legacy_signatures.get(loc)):
            lastmod = old["lastmod"]
            migrated += 1
        else:
            lastmod = today
            changed.append(loc)
        new_state[loc] = {"sig": s, "lastmod": lastmod}
        entries.append((loc, lastmod))

    if migrating:
        print(f"signature scheme {prev_scheme} -> {SIG_SCHEME}: "
              f"{migrated} URL(s) rescoped with their dates preserved")

    STATE_DIR.mkdir(exist_ok=True)
    # newline="\n" explicitly: this file is committed, .gitattributes pins the
    # repo to LF, and Python on Windows would otherwise write CRLF and make
    # every local run look like a change to git.
    STATE_PATH.write_text(
        json.dumps(
            {
                "_comment": (
                    "Per-URL content signatures behind sitemap lastmod. Written by "
                    "scripts/build_sitemap.py and committed by the nightly so dates "
                    "survive the rebuild. Deleting this file resets every lastmod to "
                    "the next build date. Deliberately carries no build timestamp: "
                    "the file has to be byte-identical when nothing changed, or the "
                    "nightly commits it every single night for no reason."
                ),
                "_scheme": SIG_SCHEME,
                "urls": dict(sorted(new_state.items())),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    # --- changed-URL list for IndexNow ------------------------------------
    if bootstrap:
        # First run with no prior state: every URL looks new. Submitting all of
        # them is exactly the flood this change exists to stop, and the sitemap
        # covers them anyway.
        changed_out = []
        note = "bootstrap run (no prior state) — IndexNow submission skipped"
    elif len(changed) > CHANGED_URL_CAP:
        changed_out = sorted(changed)[:CHANGED_URL_CAP]
        note = (f"{len(changed)} changed URLs exceeded the {CHANGED_URL_CAP} cap "
                f"— submitting the first {CHANGED_URL_CAP}")
    else:
        changed_out = sorted(changed)
        note = f"{len(changed_out)} changed URLs"

    # The IndexNow step reads this line by line; LF keeps it identical to what
    # CI produces, even though this one is gitignored.
    CHANGED_PATH.write_text(
        "".join(f"{BASE}{loc}\n" for loc in changed_out),
        encoding="utf-8",
        newline="\n",
    )

    # --- sitemap.xml -------------------------------------------------------
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

    print(f"wrote {out.relative_to(ROOT)} with {len(entries)} URLs")
    print(f"excluded {len(skipped_noindex)} noindex page(s)")
    for loc in skipped_noindex[:10]:
        print(f"  noindex  {loc}")
    if len(skipped_noindex) > 10:
        print(f"  ... and {len(skipped_noindex) - 10} more")
    print(f"IndexNow: {note}")
    for loc in changed_out[:25]:
        print(f"  changed  {loc}")
    if len(changed_out) > 25:
        print(f"  ... and {len(changed_out) - 25} more")


if __name__ == "__main__":
    main()
