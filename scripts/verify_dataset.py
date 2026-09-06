#!/usr/bin/env python3
"""Data-shape gate for the published dataset.

Runs in the nightly workflow BEFORE the build, so a dataset that violates an
invariant never becomes a site and never reaches the deploy step -- the
previously deployed version stays live and the failure is loud.

Every check here corresponds to a guarantee something downstream already
relies on. The pipeline enforces these at write time; this file re-checks them
at publish time, because the dataset is rebuilt nightly from ~1,900
third-party repositories and the pipeline is not the only thing that can put a
value in it (a merge path, a carried-forward field, or a hand edit can all
land a value the writer never saw).

Deliberately NOT checked: the content of repository descriptions. They are
arbitrary third-party prose, republished as such and labelled as such on every
surface. Pattern-matching them for "suspicious" text would produce a gate that
cries wolf nightly and gets switched off within a week.

Usage:  python3 scripts/verify_dataset.py
Exit 0 = publishable. Exit 1 = do not deploy.
"""

import csv
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "public" / "data" / "mcp_servers.json"
CSV_PATH = ROOT / "public" / "data" / "mcp_servers.csv"
CATEGORIES_PATH = ROOT / "categories.json"
TOPICS_PATH = ROOT / "topics.json"

MIN_SERVERS = 200

# `id` is the URL path segment for /servers/<id> and the lookup key for
# get_server over MCP. A separator or a dot-segment here would be a path
# traversal primitive at three separate layers (the asset store, the Worker's
# markdown rewrite, the sitemap).
ID_RE = re.compile(r"^[a-z0-9._+-]+--[a-z0-9._+-]+$")

# Approved topics become /topics/<tag> URLs.
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# install_hint is rendered inside a fenced code block for a human to copy and
# paste into a shell. Our own CLONE_NOTE annotations legitimately contain "&&"
# but only after the "#" comment marker, so the command half is what matters.
SHELL_METACHARS = re.compile(r"[;&|`$><]")

# Fields the pipeline is allowed to emit. An unexpected key means an internal
# value leaked into the published artifact -- `_hay` and `_topics` are the two
# precomputed search fields that must never persist.
ALLOWED_FIELDS = {
    "archived", "category", "created_at", "delisted_at", "description",
    "editorial_notes", "editorial_summary", "first_seen", "forks",
    "full_name", "github_repo_id", "homepage", "id", "install_hint",
    "language", "license", "name", "open_issues", "owner", "pushed_at",
    "repo_url", "security_notes", "security_reviewed", "source",
    "sponsor_tier", "stars", "status", "topics", "verified_badge",
}
REQUIRED_FIELDS = {"id", "full_name", "owner", "category", "status"}

# Trust signals. No automated path may introduce one, and no automated path may
# drop one a human set. They are compared against the committed dataset rather
# than asserted empty, so a deliberate human edit (committed, therefore already
# in HEAD) passes while the pipeline inventing or losing one fails.
# editorial_summary is excluded on purpose: it is sourced from
# editorial/summaries.md and is SUPPOSED to change during a refresh.
FROZEN_FIELDS = ("security_reviewed", "verified_badge", "sponsor_tier",
                 "security_notes", "editorial_notes")

STATUSES = {"active", "archived_or_removed"}

failures = []
notes = []


def fail(check, detail):
    failures.append("{}: {}".format(check, detail))


def command_half(hint):
    """The runnable part of an install hint, minus our own trailing note."""
    return str(hint or "").split("   #", 1)[0]


def committed_dataset():
    """The dataset as of HEAD, or None if it cannot be read.

    Never fatal on its own: a first commit, a detached tree or a checkout
    without history is a legitimate reason for this to be unavailable, and a
    missing baseline must not be able to block a deploy by itself.
    """
    try:
        raw = subprocess.run(
            ["git", "show", "HEAD:public/data/mcp_servers.json"],
            cwd=str(ROOT), capture_output=True, check=True,
        ).stdout.decode("utf-8")
        return json.loads(raw)
    except Exception as exc:                    # noqa: BLE001 - advisory only
        notes.append("frozen-field check skipped (no baseline in HEAD: %s)" % exc)
        return None


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    servers = data["servers"]
    count = data.get("count", 0)
    categories = {c["slug"] for c in json.loads(
        CATEGORIES_PATH.read_text(encoding="utf-8"))["categories"]}
    topics = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))["topics"]

    # --- volume ------------------------------------------------------------
    # The GitHub API having a bad night must not silently publish a gutted
    # directory over a good one.
    if count < MIN_SERVERS:
        fail("volume", "only %d active servers (expected %d+)" % (count, MIN_SERVERS))

    # --- per-entry invariants ----------------------------------------------
    bad_ids, bad_cats, bad_home, bad_hints, bad_status = [], [], [], [], []
    stray_fields, missing_fields = {}, []

    for s in servers:
        sid = s.get("id", "<no id>")

        if not isinstance(sid, str) or not ID_RE.match(sid):
            bad_ids.append(repr(sid))

        if s.get("category") not in categories:
            bad_cats.append("%s -> %r" % (sid, s.get("category")))

        home = s.get("homepage")
        if home is not None and not re.match(r"^https?://", str(home), re.I):
            bad_home.append("%s -> %r" % (sid, home))

        cmd = command_half(s.get("install_hint"))
        if SHELL_METACHARS.search(cmd):
            bad_hints.append("%s -> %r" % (sid, cmd))

        if s.get("status") not in STATUSES:
            bad_status.append("%s -> %r" % (sid, s.get("status")))

        extra = set(s) - ALLOWED_FIELDS
        if extra:
            stray_fields[sid] = sorted(extra)
        absent = REQUIRED_FIELDS - set(s)
        if absent:
            missing_fields.append("%s missing %s" % (sid, sorted(absent)))

    if bad_ids:
        fail("id shape", "%d outside owner--repo: %s" % (len(bad_ids), bad_ids[:5]))
    if bad_cats:
        fail("category", "%d not in categories.json: %s" % (len(bad_cats), bad_cats[:5]))
    if bad_home:
        fail("homepage", "%d not http(s): %s" % (len(bad_home), bad_home[:5]))
    if bad_hints:
        fail("install_hint", "%d contain shell metacharacters: %s"
                             % (len(bad_hints), bad_hints[:5]))
    if bad_status:
        fail("status", "%d unknown: %s" % (len(bad_status), bad_status[:5]))
    if stray_fields:
        fail("field allowlist", "%d entries carry unexpected fields: %s"
                                % (len(stray_fields), list(stray_fields.items())[:5]))
    if missing_fields:
        fail("required fields", "%d: %s" % (len(missing_fields), missing_fields[:5]))

    # --- topics become URLs -------------------------------------------------
    bad_topics = [t for t in topics if not TOPIC_RE.match(str(t))]
    if bad_topics:
        fail("topic slug", "not URL-safe: %s" % bad_topics[:5])

    # --- trust signals may only move by human commit ------------------------
    baseline = committed_dataset()
    if baseline:
        was = {s["id"]: tuple(s.get(f) for f in FROZEN_FIELDS)
               for s in baseline.get("servers", []) if "id" in s}
        drifted = []
        for s in servers:
            prev = was.get(s.get("id"))
            if prev is None:
                continue                          # new entry tonight
            now = tuple(s.get(f) for f in FROZEN_FIELDS)
            if now != prev:
                drifted.append("%s: %s -> %s" % (s["id"], prev, now))
        if drifted:
            fail("frozen editorial fields",
                 "%d changed with no human commit (set or dropped by "
                 "automation): %s" % (len(drifted), drifted[:5]))

    # --- CSV injection guard actually applied -------------------------------
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        unguarded = [
            "%s.%s" % (row.get("id"), key)
            for row in csv.DictReader(fh)
            for key, val in row.items()
            if val and str(val)[:1] in ("=", "+", "-", "@", "\t", "\r")
        ]
    if unguarded:
        fail("csv formula guard",
             "%d cells start with a formula character and were not prefixed: %s"
             % (len(unguarded), unguarded[:5]))

    # --- report -------------------------------------------------------------
    for note in notes:
        print("note: %s" % note)
    if failures:
        print("\nREFUSING TO DEPLOY -- %d dataset invariant(s) violated:\n"
              % len(failures))
        for f in failures:
            print("  ::error::%s" % f)
        return 1

    print("dataset OK: %d active servers, %d total, generated %s"
          % (count, len(servers), data.get("generated_at")))
    print("  invariants held: id shape, category membership, homepage scheme, "
          "install-hint safety, status enum, field allowlist, topic slugs, "
          "frozen editorial fields, CSV formula guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
