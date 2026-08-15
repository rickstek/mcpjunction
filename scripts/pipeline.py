#!/usr/bin/env python3
"""
mcpjunction.ai data pipeline v0.2

Pulls MCP server repos from the GitHub REST API, normalizes them into directory
entries, MERGES with the previous dataset (preserving editorial fields), and
writes JSON + CSV into public/data/.

Compliance notes (do not remove):
- Official GitHub REST API only. No HTML scraping. Complies with GitHub ToS.
- Unauthenticated search = 10 req/min. In GitHub Actions the built-in
  ${{ secrets.GITHUB_TOKEN }} is passed as GITHUB_TOKEN and raises this to
  30 req/min, so the Action gets the full dataset.
- Sleeps between requests and backs off on 403/429 rate-limit responses.
- Public repo metadata only. The only personal data republished is public
  GitHub owner handles, with attribution and a takedown contact on-site.

v0.2 changes vs v0.1:
- Editorial fields (security_reviewed, verified_badge, sponsor_tier,
  editorial_notes) are read from the existing dataset and carried forward.
  The pipeline NEVER writes a truthy value into them. Standing rule:
  automation cannot grant a badge.
- Delisted repos are retained with status="archived_or_removed" for a 30-day
  grace window (timestamped via delisted_at), then dropped — stable URLs
  without unbounded dataset growth.
- Deterministic ordering so nightly diffs are readable in git.
"""

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"
JSON_PATH = DATA_DIR / "mcp_servers.json"
CSV_PATH = DATA_DIR / "mcp_servers.csv"
CATEGORIES_PATH = ROOT / "categories.json"
SUMMARIES_PATH = ROOT / "editorial" / "summaries.md"

CONTACT = "admin@mcpjunction.ai"
USER_AGENT = f"mcpjunction.ai-pipeline/0.2 (+https://mcpjunction.ai; {CONTACT})"

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
PAGES_PER_QUERY = int(os.environ.get("PAGES_PER_QUERY", "4"))
SLEEP = float(os.environ.get("REQUEST_SLEEP", "2.5" if TOKEN else "7.0"))
MIN_STARS = int(os.environ.get("MIN_STARS", "2"))

QUERIES = [
    "topic:mcp-server",
    "topic:model-context-protocol",
    "topic:mcp",
    '"mcp server" in:name,description',
    '"model context protocol" in:name,description,readme',
]

# Editorial fields: human-set only. Automation carries them forward, never sets.
EDITORIAL_FIELDS = {
    "security_reviewed": False,
    "security_notes": "",
    "verified_badge": False,
    "sponsor_tier": None,
    "editorial_notes": "",
}

# Categories come from categories.json at the repo root — human-owned taxonomy,
# NOT hardcoded here. First-match order is the order in that file. Automation
# only ASSIGNS; it never invents categories or terms.
def _load_category_rules():
    raw = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    rules = []
    for cat in raw["categories"]:
        slug = cat["slug"]
        terms = cat.get("match") or []
        if not terms:
            rules.append((slug, None))
            continue
        # Word-boundary-ish: don't match inside longer alphanumeric tokens.
        # Custom lookaround instead of \b because \b treats "_" as a word
        # character: "ros" must match inside "my_ros_pkg" (repo names use
        # underscores as separators) and \b would not. Must stay in sync with
        # the boundary rule used when the taxonomy was validated.
        escaped = [re.escape(t.lower()) for t in terms]
        pattern = r"(?<![a-z0-9])(?:" + "|".join(escaped) + r")(?![a-z0-9])"
        rules.append((slug, re.compile(pattern)))
    return rules

CATEGORY_RULES = _load_category_rules()
MCP_HINT = re.compile(r"mcp|model[\s-]context[\s-]protocol")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def api_get(url, attempt=1):
    """GET the GitHub API with auth if available, backing off on rate limits."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (403, 429) and attempt <= 4:
            reset = e.headers.get("X-RateLimit-Reset")
            wait = 60
            if reset:
                try:
                    wait = max(5, int(reset) - int(time.time()) + 2)
                except ValueError:
                    pass
            wait = min(wait, 180)
            print(f"  rate limited ({e.code}); sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            return api_get(url, attempt + 1)
        print(f"  HTTP {e.code} on {url}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001 - network errors shouldn't kill the run
        print(f"  error on {url}: {e}", file=sys.stderr)
        return None


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------

def categorize(repo):
    haystack = " ".join([
        repo.get("full_name") or "",
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
    ]).lower()
    for name, pattern in CATEGORY_RULES:
        if pattern is None:
            continue
        if pattern.search(haystack):
            return name
    return "uncategorized"


def guess_install(repo):
    """Best-effort install hint inferred from language. NEVER emit auto-confirm
    flags (npx -y, pipx --yes, etc.): the package registry name may be squatted
    by someone other than the repo owner, and a directory built on security
    review must not publish commands that execute unverified packages without
    a prompt. Hints are labeled as unverified in the dataset disclaimer."""
    lang = (repo.get("language") or "").lower()
    name = (repo.get("name") or "").lower()
    if lang in ("python",):
        return f"uvx {name}" if "-" in name else f"pip install {name}"
    if lang in ("typescript", "javascript"):
        return f"npx {name}"
    if lang in ("go",):
        return f"go install {repo.get('html_url','').replace('https://','')}@latest"
    if lang in ("rust",):
        return f"cargo install {name}"
    return None


def normalize(repo):
    owner = (repo.get("owner") or {}).get("login") or ""
    entry = {
        "id": (repo.get("full_name") or "").lower().replace("/", "--"),
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "owner": owner,
        "description": (repo.get("description") or "").strip(),
        "repo_url": repo.get("html_url"),
        "homepage": repo.get("homepage") or None,
        "category": categorize(repo),
        "topics": sorted(repo.get("topics") or []),
        "language": repo.get("language"),
        "license": ((repo.get("license") or {}).get("spdx_id")
                    if repo.get("license") else None),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "archived": bool(repo.get("archived")),
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "install_hint": guess_install(repo),
        "status": "active",
        "source": "github-api",
    }
    entry.update(EDITORIAL_FIELDS)
    return entry


def load_editorial_summaries():
    """Parse editorial/summaries.md into {server_id: summary}.

    That file — not the previous dataset — is the source of truth, so a
    summary deleted there disappears from the site on the next run, and every
    change is reviewable as a git diff. This is the ONLY path by which
    editorial_summary gets a value; automation never authors one (Standing
    Rule: the template displays editorial fields, it never derives them).

    Format is '## <server-id>' followed by prose until the next heading.

    Only headings that look like a server id (owner--repo, containing the
    double hyphen) are treated as entries. That discriminator is what keeps
    the file's own documentation headings — '## Format', '## House style' —
    from parsing as servers, which they otherwise silently do.
    """
    heading = re.compile(r"^##\s+([a-z0-9][a-z0-9._-]*--[a-z0-9._-]+)\s*$",
                         re.IGNORECASE)
    if not SUMMARIES_PATH.exists():
        return {}
    text = SUMMARIES_PATH.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    summaries = {}
    current = None
    buf = []

    def flush():
        if current and buf:
            body = " ".join(" ".join(buf).split())
            if body:
                summaries[current] = body

    for line in text.splitlines():
        m = heading.match(line)
        if m:
            flush()
            current = m.group(1).strip().lower()
            buf = []
        elif current is not None:
            buf.append(line.strip())
    flush()
    return summaries


def looks_like_mcp_server(repo):
    """Filter out the noise that 'mcp' as a bare topic drags in."""
    if repo.get("stargazers_count", 0) < MIN_STARS:
        return False
    blob = " ".join([
        repo.get("full_name") or "",
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
    ]).lower()
    return bool(MCP_HINT.search(blob))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def fetch_all():
    found = {}
    for q in QUERIES:
        print(f"query: {q}")
        for page in range(1, PAGES_PER_QUERY + 1):
            params = urllib.parse.urlencode({
                "q": q, "sort": "stars", "order": "desc",
                "per_page": 100, "page": page,
            })
            data = api_get(f"https://api.github.com/search/repositories?{params}")
            if not data:
                break
            items = data.get("items") or []
            kept = 0
            for repo in items:
                if not looks_like_mcp_server(repo):
                    continue
                fn = repo.get("full_name")
                if fn and fn not in found:
                    found[fn] = repo
                    kept += 1
            print(f"  page {page}: {len(items)} returned, {kept} new")
            if len(items) < 100:
                break
            time.sleep(SLEEP)
        time.sleep(SLEEP)
    return found


def merge(new_entries, previous):
    """Carry editorial fields forward; retain delisted repos for one cycle."""
    prev_by_id = {e["id"]: e for e in previous}
    merged = {}

    for e in new_entries:
        old = prev_by_id.get(e["id"])
        if old:
            for f in EDITORIAL_FIELDS:
                if f in old:
                    e[f] = old[f]
            e["first_seen"] = old.get("first_seen") or e.get("created_at")
        else:
            e["first_seen"] = e.get("created_at")
        merged[e["id"]] = e

    # Repos that vanished from the API: keep them (status=archived_or_removed)
    # for a 30-day grace window so published URLs don't die overnight, then
    # drop them for good. Without the timestamp check they'd be carried
    # forward every night forever and the dataset would grow unbounded.
    now = datetime.now(timezone.utc)
    for old_id, old in prev_by_id.items():
        if old_id in merged:
            continue
        old = dict(old)
        if old.get("status") != "archived_or_removed":
            old["status"] = "archived_or_removed"
            old["delisted_at"] = now.isoformat(timespec="seconds")
        else:
            stamp = old.get("delisted_at")
            if not stamp:  # legacy entry with no timestamp: start clock now
                old["delisted_at"] = now.isoformat(timespec="seconds")
            else:
                try:
                    age = now - datetime.fromisoformat(stamp)
                    if age.days > 30:
                        continue  # grace expired — drop
                except ValueError:
                    old["delisted_at"] = now.isoformat(timespec="seconds")
        # Recategorize delisted entries against the current taxonomy so
        # retired slugs (e.g. "ai-ml", "files") don't linger in the dataset
        # and produce broken /categories/<slug> URLs.
        old["category"] = categorize({
            "full_name": old.get("full_name"),
            "description": old.get("description"),
            "topics": old.get("topics") or [],
        })
        merged[old_id] = old

    return sorted(merged.values(), key=lambda e: (-int(e.get("stars") or 0),
                                                  e.get("full_name") or ""))


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    previous = []
    if JSON_PATH.exists():
        try:
            raw = json.loads(JSON_PATH.read_text())
            # Tolerate the v0.1 shape (bare list) and the v0.2 shape (envelope).
            if isinstance(raw, list):
                previous = raw
            else:
                previous = raw.get("servers") or raw.get("data") or []
            previous = [e for e in previous if isinstance(e, dict) and e.get("id")]
            # Migration guard: v0.1 used "__" as the owner/repo separator,
            # v0.2 uses "--". When the format changed, every v0.1 id looked
            # like a vanished repo and got carried forward as a false
            # "delisted" ghost — 454 of them duplicating live entries. Server
            # pages were never published under v0.1 ids, so there are no
            # external URLs to protect: drop them outright. (GitHub usernames
            # cannot contain underscores, so every real v0.2 id contains "--";
            # a v0.1 ghost id never does.)
            ghosts = [e for e in previous
                      if "__" in e["id"] and "--" not in e["id"]]
            if ghosts:
                print(f"dropping {len(ghosts)} v0.1-format ghost entries")
                previous = [e for e in previous
                            if not ("__" in e["id"] and "--" not in e["id"])]
            print(f"previous dataset: {len(previous)} servers")
        except Exception as e:  # noqa: BLE001
            print(f"could not read previous dataset ({e}); starting fresh")

    print(f"auth: {'token' if TOKEN else 'UNAUTHENTICATED (slow, capped)'}")
    repos = fetch_all()
    print(f"\nunique repos matched: {len(repos)}")

    entries = merge([normalize(r) for r in repos.values()], previous)

    # Apply human-written summaries. Set on EVERY entry (empty string when
    # absent) so the field always exists in the published schema.
    summaries = load_editorial_summaries()
    known_ids = {e["id"] for e in entries}
    for e in entries:
        e["editorial_summary"] = summaries.get(e["id"], "")
    orphans = sorted(set(summaries) - known_ids)
    if orphans:
        print(f"WARNING: {len(orphans)} summary id(s) match no server "
              f"(typo? delisted?): {', '.join(orphans[:8])}")
    print(f"editorial summaries applied: {len(summaries) - len(orphans)}")

    active = [e for e in entries if e.get("status") == "active"]

    categories = {}
    for e in active:
        categories[e["category"]] = categories.get(e["category"], 0) + 1

    payload = {
        "dataset": "mcpjunction.ai MCP server directory",
        "url": "https://mcpjunction.ai/data/mcp_servers.json",
        "license": "https://mcpjunction.ai/licensing",
        "attribution": "via mcpjunction.ai",
        "source": "GitHub REST API (public repository metadata) + editorial review",
        "disclaimer": ("Not affiliated with Anthropic or the Model Context "
                       "Protocol project. Install hints are best-effort and "
                       "should be verified against each repo's own README."),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(active),
        "count_including_delisted": len(entries),
        "categories": dict(sorted(categories.items(), key=lambda kv: -kv[1])),
        "servers": entries,
    }

    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    cols = ["id", "full_name", "owner", "description", "category", "language",
            "license", "stars", "forks", "pushed_at", "repo_url",
            "install_hint", "security_reviewed", "verified_badge",
            "sponsor_tier", "status"]

    def csv_safe(v):
        """OWASP CSV-injection guard. Descriptions come from arbitrary GitHub
        repos; a value starting with = + - @ (or tab/CR) executes as a formula
        when the published CSV is opened in Excel/Sheets. Prefix with ' to
        neutralize."""
        if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + v
        return v

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for e in entries:
            w.writerow({k: csv_safe(e.get(k)) for k in cols})

    print(f"\nwrote {JSON_PATH.relative_to(ROOT)} ({len(active)} active, "
          f"{len(entries)} total)")
    print(f"wrote {CSV_PATH.relative_to(ROOT)}")
    print("categories: " + ", ".join(f"{k} {v}" for k, v in
                                     payload["categories"].items()))


if __name__ == "__main__":
    main()
