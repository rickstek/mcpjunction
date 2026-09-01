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
TOPICS_PATH = ROOT / "topics.json"
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

def _load_category_overrides(valid_slugs):
    """Human-set category assignments, from `overrides` in categories.json.

    For the handful of repos where keyword matching is wrong and no rule change
    fixes it. Three strategies were measured against the live dataset before
    this existed — the shipping first-match matcher, a topics-first pass, and
    weighted scoring — and first-match won. The residual errors are not an
    algorithm problem: they are very large, general-purpose projects whose long
    descriptions collide with several categories, plus repos their own owners
    tagged misleadingly (a Java study guide carrying `mysql` and `redis` lands
    in Databases under every strategy). Those repos sort to the top of a
    category page by stars, so a dozen bad rows do outsized damage.

    Automation still never INVENTS a category: an override may only name a slug
    that already exists in categories.json.
    """
    # object_pairs_hook, not the parsed dict: JSON permits duplicate keys and
    # every parser silently keeps the last, so a hand-edited list that names the
    # same server twice with two different categories "works" while quietly
    # ignoring one of the two decisions. Catch it instead of guessing which was
    # meant.
    def _no_dupes(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                sys.exit(f"REFUSING TO RUN: categories.json names '{k}' twice "
                         f"(as '{seen[k]}' and '{v}'). JSON keeps only the last, "
                         f"so remove one.")
            seen[k] = v
        return seen

    raw = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"),
                     object_pairs_hook=_no_dupes)
    out = {}
    for server_id, slug in (raw.get("overrides") or {}).items():
        key = str(server_id).strip().lower()
        if slug not in valid_slugs:
            sys.exit(f"REFUSING TO RUN: categories.json sets an override for "
                     f"'{key}' naming unknown category '{slug}'. Overrides may "
                     f"only point at a slug that already exists.")
        out[key] = slug
    return out


CATEGORY_RULES = _load_category_rules()
CATEGORY_OVERRIDES = _load_category_overrides({slug for slug, _ in CATEGORY_RULES})
# Ids that actually matched an entry this run. An override whose id is
# misspelled is silently inert -- the slug is validated but the key is not, and
# a hand-edited file WILL eventually carry a typo or an id for a repo that has
# since been renamed or delisted. main() reports the unused ones.
CATEGORY_OVERRIDES_USED = set()
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

# Separator between haystack fields and between individual topics. No match
# term may contain it, so no term can match across a boundary. Joining with a
# plain space let two adjacent topics manufacture a phrase that neither one
# holds: Windows-MCP's topics are [ai, desktop, mcp, tools, windows, ...],
# which reads as "mcp tools" once joined, and GitHub returns topics
# alphabetically -- so which phrases existed at all was an accident of the
# alphabet. Changing this moved zero servers when it landed; it is preventive,
# and it makes natural multi-word terms ("task management", "google drive")
# safe to write instead of forcing the hyphenated spelling.
HAYSTACK_SEP = " | "


def categorize(repo):
    # Same derivation as the entry's own "id" field, so overrides are keyed by
    # the id that appears in the URL.
    server_id = (repo.get("full_name") or "").lower().replace("/", "--")
    override = CATEGORY_OVERRIDES.get(server_id)
    if override:
        CATEGORY_OVERRIDES_USED.add(server_id)
        return override
    haystack = HAYSTACK_SEP.join([
        repo.get("full_name") or "",
        repo.get("description") or "",
        HAYSTACK_SEP.join(repo.get("topics") or []),
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


def safe_homepage(value):
    """Return the homepage only if it is a plain http(s) URL, else None.

    GitHub does not normalize this field: it is free text, and the live dataset
    contains values with no scheme at all ("www.funasr.com"), which render as
    RELATIVE links and 404. The same absence of validation is what would let a
    "javascript:..." value reach an href attribute on every page that lists the
    repo. Astro escapes the value so it cannot break out of the attribute, but
    escaping does not make a javascript: URL safe to click.

    Validating here rather than in the template means the JSON, the CSV, the
    HTML and the markdown all inherit the guarantee.
    """
    if not value:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    # Reject control characters and whitespace outright: they are the classic
    # way to smuggle a scheme past a naive prefix check ("java\tscript:").
    if any(ch.isspace() or ord(ch) < 0x20 for ch in candidate):
        return None
    if not re.match(r"^https?://[^\s/]+", candidate, re.IGNORECASE):
        return None
    return candidate


def normalize(repo):
    owner = (repo.get("owner") or {}).get("login") or ""
    entry = {
        "id": (repo.get("full_name") or "").lower().replace("/", "--"),
        # GitHub's immutable numeric repo id. The "id" above is derived from
        # owner/repo, which is MUTABLE: repos get renamed, and a deleted
        # account's username is released for anyone to re-register. Editorial
        # state is carried forward by id, so without a stable identity a new
        # owner of a recycled owner/repo would silently inherit the previous
        # holder's security_reviewed flag, sponsor_tier and hand-written
        # summary. See merge().
        "github_repo_id": repo.get("id"),
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "owner": owner,
        "description": (repo.get("description") or "").strip(),
        "repo_url": repo.get("html_url"),
        "homepage": safe_homepage(repo.get("homepage")),
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
        if line.lstrip().startswith("#"):
            # ANY markdown heading ends the current entry. Only an id-shaped
            # one starts a new entry; everything else (category groupings,
            # notes-to-self) is a section break. Without this, a '# Databases'
            # grouping line silently became the body of the entry above it.
            flush()
            m = heading.match(line)
            current = m.group(1).strip().lower() if m else None
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

    hijacked = []
    for e in new_entries:
        old = prev_by_id.get(e["id"])

        # Same owner/repo, different GitHub repo id => this is not the same
        # project. Either the original was deleted and someone re-registered
        # the name, or the slot changed hands. Carrying editorial state across
        # that boundary would hand a stranger a security-reviewed badge, a
        # sponsor slot, or our own written summary. Treat it as a new entry.
        # (Only compare when both ids are known: entries written before this
        # field existed have none, and must not all be treated as hijacked.)
        if old is not None:
            old_gh = old.get("github_repo_id")
            new_gh = e.get("github_repo_id")
            if old_gh and new_gh and old_gh != new_gh:
                hijacked.append((e["id"], old_gh, new_gh))
                old = None

        if old:
            for f in EDITORIAL_FIELDS:
                if f in old:
                    e[f] = old[f]
            e["first_seen"] = old.get("first_seen") or e.get("created_at")
        else:
            e["first_seen"] = e.get("created_at")
        merged[e["id"]] = e

    if hijacked:
        print(f"\nIDENTITY CHANGE on {len(hijacked)} entr(y/ies) — editorial "
              f"state NOT carried forward:", file=sys.stderr)
        for eid, old_gh, new_gh in hijacked[:10]:
            print(f"  {eid}: github id {old_gh} -> {new_gh}", file=sys.stderr)

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
            # encoding is explicit, not incidental. 459 entries carry non-ASCII
            # descriptions and the file is written with ensure_ascii=False, so
            # on any box whose default is not UTF-8 (Windows/cp1252, for one)
            # this read raises UnicodeDecodeError.
            raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
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
            # external URLs to protect: drop them outright.
            #
            # Why this test is safe: every v0.2 id is full_name.replace("/","--")
            # and a full_name always contains exactly one "/", so a v0.2 id
            # ALWAYS contains "--". The condition therefore cannot match a real
            # entry. (Note it is not about underscores being illegal — repo
            # names may contain them, and 34 current ids do.)
            ghosts = [e for e in previous
                      if "__" in e["id"] and "--" not in e["id"]]
            if ghosts:
                print(f"dropping {len(ghosts)} v0.1-format ghost entries")
                previous = [e for e in previous
                            if not ("__" in e["id"] and "--" not in e["id"])]
            print(f"previous dataset: {len(previous)} servers")
        except Exception as e:  # noqa: BLE001
            # FATAL, deliberately. "Starting fresh" silently discards every
            # carried-forward security_reviewed, verified_badge, sponsor_tier,
            # security_notes, editorial_notes and first_seen — and the CI
            # collapse guard would not notice, because a fresh full crawl still
            # returns 1,800+ servers. Losing the editorial layer must stop the
            # run, not be a line of log output.
            sys.exit(f"FATAL: could not read previous dataset ({e}). "
                     f"Refusing to run: continuing would silently erase all "
                     f"editorial fields. Fix or restore "
                     f"{JSON_PATH.relative_to(ROOT)} and re-run.")

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
        # Re-assert the homepage invariant over EVERY entry, not just the ones
        # normalize() just built. Carried-forward and delisted entries predate
        # this validation, and the published dataset should hold the guarantee
        # uniformly rather than depending on which code path produced a row.
        e["homepage"] = safe_homepage(e.get("homepage"))
    orphans = sorted(set(summaries) - known_ids)
    if orphans:
        print(f"WARNING: {len(orphans)} summary id(s) match no server "
              f"(typo? delisted?): {', '.join(orphans[:8])}")
    print(f"editorial summaries applied: {len(summaries) - len(orphans)}")

    active = [e for e in entries if e.get("status") == "active"]

    # ---------------------------------------------------------------------
    # Collapse guard (relative). The CI check downstream only refuses to
    # publish below an ABSOLUTE floor of 200 servers, which a partial GitHub
    # outage sails straight past: a run that returns 900 of 1,800 repos would
    # deploy happily and publish ~900 false "Delisted" notices — visible,
    # public, and wrong for a day, on exactly the stable URLs that citers rely
    # on. Compare against the previous run instead of a constant.
    # ---------------------------------------------------------------------
    prev_active_ids = {e["id"] for e in previous if e.get("status") == "active"}
    newly_delisted = [
        e for e in entries
        if e.get("status") == "archived_or_removed" and e["id"] in prev_active_ids
    ]
    allow_collapse = os.environ.get("ALLOW_COLLAPSE") == "1"

    if prev_active_ids:
        ratio = len(active) / len(prev_active_ids)
        problems = []
        if ratio < 0.90:
            problems.append(
                f"active servers fell {(1 - ratio) * 100:.1f}% "
                f"({len(prev_active_ids)} -> {len(active)})")
        if len(newly_delisted) > 50:
            problems.append(
                f"{len(newly_delisted)} servers would be newly delisted in a "
                f"single run")
        if problems:
            msg = ("REFUSING TO PUBLISH — this looks like a partial API "
                   "failure, not a real change:\n  - " + "\n  - ".join(problems))
            if allow_collapse:
                print(f"{msg}\n(ALLOW_COLLAPSE=1 set; continuing anyway)",
                      file=sys.stderr)
            else:
                sys.exit(f"{msg}\n\nThe previous dataset is untouched and the "
                         f"live site keeps serving it. If this drop is "
                         f"genuine, re-run with ALLOW_COLLAPSE=1.")
    if newly_delisted:
        print(f"newly delisted this run: {len(newly_delisted)}")

    categories = {}
    for e in active:
        categories[e["category"]] = categories.get(e["category"], 0) + 1

    # Topic counts, restricted to the APPROVED list in topics.json — the same
    # human-owned file the /topics/<tag> pages are minted from. Deliberately not
    # every tag in the data: there are ~5,000 distinct third-party topic strings,
    # and only the approved ones have pages. Emitting a count for an unapproved
    # tag would invite consumers (notably the /mcp tools) to build a
    # /topics/<tag> URL that 404s.
    #
    # Counted the same way the topic pages compute membership: exact match on a
    # server's topics array, active servers only. If the two ever disagree, the
    # page is right and this is wrong.
    approved_topics = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))["topics"]
    topic_counts = {}
    for e in active:
        for t in e.get("topics") or []:
            key = str(t).lower()
            topic_counts[key] = topic_counts.get(key, 0) + 1
    topics = {t: topic_counts.get(t, 0) for t in approved_topics}

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
        "topics": dict(sorted(topics.items(), key=lambda kv: -kv[1])),
        "servers": entries,
    }

    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")

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
    unused = sorted(set(CATEGORY_OVERRIDES) - CATEGORY_OVERRIDES_USED)
    if unused:
        print(f"WARNING: {len(unused)} categories.json override(s) matched no "
              f"entry and did nothing — check for a typo, a renamed repo, or "
              f"one that has aged out: " + ", ".join(unused), file=sys.stderr)
    thin = [k for k, v in payload["topics"].items() if v < 10]
    print(f"topics: {len(payload['topics'])} approved"
          + (f", {len(thin)} below 10 members (noindex on site): "
             + ", ".join(thin) if thin else ""))


if __name__ == "__main__":
    main()
