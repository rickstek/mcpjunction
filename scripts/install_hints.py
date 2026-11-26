#!/usr/bin/env python3
"""Verified install hints.

Until 2026-11 every registry-style install hint was `<runner> <repo name>`,
guessed from GitHub's language field. Measured on 2026-11-26 across all 1,364
such hints: 573 named a package nobody had published (anyone could register it
and receive installs from our pages), 239 named a package that belongs to a
different repository -- 228 of them a different owner, so the published command
ran a stranger's code -- and 160 named a package whose registry entry points at
no repository at all. 392 were correct.

The rule now: a registry-style hint is published only when the registry's own
metadata for that package names the listed repository. Otherwise the field is
null and the page hides the section (the path documentation and notebook repos
already take). Never fabricate.

Candidate package names come from the repository's own manifest first
(package.json, pyproject.toml, Cargo.toml, composer.json, pubspec.yaml) and the
repository name second. A manifest is the author declaring a package; the repo
name is our guess. Both must still pass the registry check -- the manifest is
where a name comes from, never a substitute for confirming it.

Not checked here, deliberately:
  - `go install github.com/<owner>/<repo>@latest` names the repository itself,
    so there is no separate package identity anyone could squat.
  - `git clone <repo url>` hints are not package claims.
  - Whether the package *runs* as an MCP server. This verifies identity, not
    behaviour, and is not a security review.

Results are kept on each entry as `install_verified`, a machine field that no
page renders: {"checked": "YYYY-MM-DD"} plus, when verified, "registry",
"package" and "source". Unverified outcomes record only the date -- never the
rejected name or the reason -- so the published dataset cannot double as a list
of unclaimed package names worth squatting.

Rechecked when older than RECHECK_DAYS or when the repository has been pushed
since the last check (its manifest may have changed). A registry outage, rate
limit or timeout keeps the previous decision instead of nulling the hint, so a
bad night at npm cannot strip 600 pages.

CLI (read-only): python3 scripts/install_hints.py --dry-run [--csv out.csv]
re-verifies every active entry in the committed dataset and prints what would
change, without writing anything.
"""

import json
import re
import sys
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

RECHECK_DAYS = 7
UA = "mcpjunction.ai-pipeline/0.2 (+https://mcpjunction.ai; admin@mcpjunction.ai)"
GH_REPO = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)

# Per-registry concurrency. crates.io asks crawlers for one request per second.
LIMITS = {"npm": 6, "pypi": 6, "crates": 1, "rubygems": 2, "packagist": 2,
          "pub.dev": 2, "raw": 6}
_sems = {k: threading.Semaphore(v) for k, v in LIMITS.items()}

# Which registry a language publishes to. Languages absent here keep whatever
# pipeline.guess_install() produced (go install / git clone / None).
REGISTRY_FOR_LANG = {
    "typescript": "npm", "javascript": "npm",
    "python": "pypi",
    "rust": "crates",
    "ruby": "rubygems",
    "php": "packagist",
    "dart": "pub.dev",
}


class Transient(Exception):
    """Registry or network trouble: keep the previous decision."""


def _fetch(url, kind):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with _sems[kind]:
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                body = resp.read().decode("utf-8", "replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            status, body = e.code, ""
        except Exception as e:  # noqa: BLE001
            raise Transient(f"{url}: {e}")
        finally:
            if kind == "crates":
                time.sleep(1.0)
    if status in (404, 410):
        return None
    if status != 200:
        raise Transient(f"{url}: HTTP {status}")
    return body


def _repos_named(*texts):
    out = set()
    for t in texts:
        for o, r in GH_REPO.findall(str(t or "")):
            r = re.sub(r"\.git$", "", r)
            out.add(f"{o}/{r}".lower())
    return out


# --- registry adapters: (exists, repos_named, extra) ---------------------------
def _npm(name):
    body = _fetch("https://registry.npmjs.org/" + urllib.parse.quote(name, safe="@/")
                  + "/latest", "npm")
    if body is None:
        return False, set(), {}
    j = json.loads(body)
    rep = j.get("repository")
    rep = rep.get("url") if isinstance(rep, dict) else rep
    bugs = j.get("bugs")
    bugs = bugs.get("url") if isinstance(bugs, dict) else bugs
    return True, _repos_named(rep, j.get("homepage"), bugs), {"bin": bool(j.get("bin"))}


def _pypi(name):
    body = _fetch(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json", "pypi")
    if body is None:
        return False, set(), {}
    i = json.loads(body).get("info") or {}
    return True, _repos_named(i.get("home_page"), json.dumps(i.get("project_urls") or {})), {}


def _crates(name):
    body = _fetch(f"https://crates.io/api/v1/crates/{urllib.parse.quote(name)}", "crates")
    if body is None:
        return False, set(), {}
    c = json.loads(body).get("crate") or {}
    return True, _repos_named(c.get("repository"), c.get("homepage"), c.get("documentation")), {}


def _gems(name):
    body = _fetch(f"https://rubygems.org/api/v1/gems/{urllib.parse.quote(name)}.json", "rubygems")
    if body is None:
        return False, set(), {}
    j = json.loads(body)
    return True, _repos_named(j.get("source_code_uri"), j.get("homepage_uri"), j.get("bug_tracker_uri")), {}


def _packagist(name):
    if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", name):
        return False, set(), {}
    body = _fetch(f"https://repo.packagist.org/p2/{name}.json", "packagist")
    if body is None:
        return False, set(), {}
    pk = (json.loads(body).get("packages") or {}).get(name) or [{}]
    return True, _repos_named(json.dumps(pk[0].get("source") or {}), pk[0].get("homepage")), {}


def _pubdev(name):
    body = _fetch(f"https://pub.dev/api/packages/{urllib.parse.quote(name)}", "pub.dev")
    if body is None:
        return False, set(), {}
    p = (json.loads(body).get("latest") or {}).get("pubspec") or {}
    return True, _repos_named(p.get("repository"), p.get("homepage"), p.get("issue_tracker")), {}


ADAPTERS = {"npm": _npm, "pypi": _pypi, "crates": _crates, "rubygems": _gems,
            "packagist": _packagist, "pub.dev": _pubdev}


# --- candidate names from the repository's own manifest ------------------------
def _raw(full_name, path):
    return _fetch(f"https://raw.githubusercontent.com/{full_name}/HEAD/{path}", "raw")


def manifest_name(full_name, registry):
    """The package name the repository declares, or None. Transient on fetch trouble."""
    try:
        if registry == "npm":
            body = _raw(full_name, "package.json")
            if body:
                j = json.loads(body)
                # "private": true means the author has declared it unpublishable.
                if not j.get("private") and isinstance(j.get("name"), str):
                    return j["name"].strip()
        elif registry == "pypi":
            body = _raw(full_name, "pyproject.toml")
            if body:
                t = tomllib.loads(body)
                n = (t.get("project") or {}).get("name") \
                    or ((t.get("tool") or {}).get("poetry") or {}).get("name")
                if isinstance(n, str):
                    return n.strip()
        elif registry == "crates":
            body = _raw(full_name, "Cargo.toml")
            if body:
                n = (tomllib.loads(body).get("package") or {}).get("name")
                if isinstance(n, str):
                    return n.strip()
        elif registry == "packagist":
            body = _raw(full_name, "composer.json")
            if body:
                n = json.loads(body).get("name")
                if isinstance(n, str):
                    return n.strip().lower()
        elif registry == "pub.dev":
            body = _raw(full_name, "pubspec.yaml")
            if body:
                m = re.search(r"(?m)^name:\s*([A-Za-z0-9_]+)\s*$", body)
                if m:
                    return m.group(1)
    except (ValueError, tomllib.TOMLDecodeError):
        return None  # unparseable manifest: no declared name, not an outage
    return None


def _repo_name_candidate(entry, registry):
    name = (entry.get("name") or "").lower()
    if registry == "packagist":
        owner = (entry.get("owner") or "").lower()
        return f"{owner}/{name}" if owner and name else None
    return name or None


def format_hint(registry, package, extra):
    if registry == "npm":
        # npx runs a package's executable; a package without one cannot be npx'd.
        return f"npx {package}" if extra.get("bin") else f"npm install {package}"
    if registry == "pypi":
        return f"uvx {package}" if "-" in package else f"pip install {package}"
    if registry == "crates":
        return f"cargo install {package}"
    if registry == "rubygems":
        return f"gem install {package}"
    if registry == "packagist":
        return f"composer require {package}"
    if registry == "pub.dev":
        return f"dart pub global activate {package}"
    raise ValueError(registry)


def verify_entry(entry):
    """Return (hint_or_None, install_verified). Raises Transient on outage."""
    registry = REGISTRY_FOR_LANG.get((entry.get("language") or "").lower())
    today = date.today().isoformat()
    listed = (entry.get("full_name") or "").lower()
    candidates = []
    declared = manifest_name(entry.get("full_name") or "", registry)
    if declared:
        candidates.append((declared, "manifest"))
    fallback = _repo_name_candidate(entry, registry)
    if fallback and fallback not in {c for c, _ in candidates}:
        candidates.append((fallback, "repo-name"))
    for package, source in candidates:
        exists, repos, extra = ADAPTERS[registry](package)
        if exists and listed in repos:
            return format_hint(registry, package, extra), {
                "checked": today, "registry": registry,
                "package": package, "source": source}
    return None, {"checked": today}


def _due(entry, prev_verified):
    if not prev_verified or not prev_verified.get("checked"):
        return True
    try:
        checked = date.fromisoformat(prev_verified["checked"])
    except ValueError:
        return True
    if (date.today() - checked).days >= RECHECK_DAYS:
        return True
    pushed = (entry.get("pushed_at") or "")[:10]
    return bool(pushed) and pushed > prev_verified["checked"]


def apply(entries, previous_by_id, force=False, log=print):
    """Decide install_hint/install_verified for every active registry-language entry.

    Mutates entries in place. Returns a Counter-like dict of outcomes.
    """
    stats = {"verified": 0, "unverified": 0, "carried": 0, "transient_kept": 0,
             "not_registry": 0}
    todo = []
    for e in entries:
        if e.get("status") != "active":
            # Delisted pages stay up for 30 days; they must not keep showing a
            # registry hint that was never verified.
            if (REGISTRY_FOR_LANG.get((e.get("language") or "").lower())
                    and not (e.get("install_verified") or {}).get("package")):
                e["install_hint"] = None
            continue
        registry = REGISTRY_FOR_LANG.get((e.get("language") or "").lower())
        if not registry:
            e.pop("install_verified", None)
            stats["not_registry"] += 1
            continue
        prev = previous_by_id.get(e["id"]) or {}
        same_repo = (not prev.get("github_repo_id") or not e.get("github_repo_id")
                     or prev.get("github_repo_id") == e.get("github_repo_id"))
        prev_v = prev.get("install_verified") if same_repo else None
        if not force and not _due(e, prev_v):
            e["install_verified"] = prev_v
            e["install_hint"] = prev.get("install_hint") if prev_v.get("package") else None
            stats["carried"] += 1
            continue
        todo.append((e, prev if same_repo else {}, prev_v))

    def work(item):
        e, prev, prev_v = item
        try:
            return item, verify_entry(e), None
        except Transient as err:
            return item, None, err

    with ThreadPoolExecutor(16) as ex:
        for (e, prev, prev_v), result, err in ex.map(work, todo):
            if err is not None:
                # Keep yesterday's decision. With no previous decision there is
                # nothing verified to keep, so publish nothing.
                if prev_v:
                    e["install_verified"] = prev_v
                    e["install_hint"] = prev.get("install_hint") if prev_v.get("package") else None
                else:
                    e["install_verified"] = None
                    e["install_hint"] = None
                stats["transient_kept"] += 1
                continue
            hint, verified = result
            e["install_hint"] = hint
            e["install_verified"] = verified
            stats["verified" if hint else "unverified"] += 1
    log(f"install hints: {stats['verified']} verified, {stats['unverified']} "
        f"unverified (hidden), {stats['carried']} carried from last check, "
        f"{stats['transient_kept']} kept on registry trouble, "
        f"{stats['not_registry']} not registry-based")
    return stats


def _dry_run(argv):
    import csv
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = json.load(open(os.path.join(root, "public", "data", "mcp_servers.json"),
                          encoding="utf-8"))
    before = {e["id"]: e.get("install_hint") for e in data["servers"]}
    entries = [dict(e) for e in data["servers"]]
    t0 = time.time()
    apply(entries, {}, force=True)
    rows, counts = [], {}
    for e in entries:
        if e.get("status") != "active" or e.get("id") not in before:
            continue
        old, new = before[e["id"]], e.get("install_hint")
        if old == new:
            kind = "unchanged" if old else "unchanged-none"
        elif old and not new:
            kind = "removed"
        elif new and not old:
            kind = "added"
        else:
            kind = "changed"
        counts[kind] = counts.get(kind, 0) + 1
        if kind in ("changed", "added", "removed"):
            rows.append((e.get("stars") or 0, e["id"], kind, old, new,
                         (e.get("install_verified") or {}).get("source", "")))
    print(f"\nDRY RUN ({time.time()-t0:.0f}s) -- nothing written. Active entries by outcome:")
    for k in ("unchanged", "changed", "added", "removed", "unchanged-none"):
        print(f"  {counts.get(k, 0):5d}  {k}")
    if "--csv" in argv:
        out = argv[argv.index("--csv") + 1]
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["stars", "id", "outcome", "hint_before", "hint_after", "name_source"])
            for r in sorted(rows, reverse=True):
                w.writerow(r)
        print("CSV:", out)
    return 0


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        sys.exit(_dry_run(sys.argv))
    print(__doc__)
