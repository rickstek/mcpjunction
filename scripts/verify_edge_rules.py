#!/usr/bin/env python3
"""Assert that the edge rate limiting rule protecting /mcp still exists.

Why this file exists
--------------------
Every other edge-policy claim this project makes is proven against production
on every run: robots.txt directives, the crawler allow/block split, markdown
content negotiation. The rate limiting rule was the one exception -- it lives
only in the Cloudflare dashboard, and a comment in worker/index.js described
it. That comment was wrong twice in one day: it first asserted the rule
covered floods (unverified), was then corrected to say no such rule was known
to exist (also wrong -- it did), and only a screenshot settled it.

Reasoning about a dashboard from inside a repository does not work. This reads
the actual configuration through the API instead.

What it checks, and why the split
---------------------------------
HARD FAIL (the rule is gone, off, or no longer blocks):
  - a rate limiting rule matching /mcp exists in the zone
  - it is enabled
  - its action is block

WARN ONLY (the threshold is a judgement call, not a correctness property):
  - the sustained ceiling the threshold permits, versus the Workers daily
    request quota. A loose threshold is a trade-off someone may have made
    deliberately; failing a deploy over it would be this script overruling a
    human decision. Printing it every run keeps it visible instead.

Credentials
-----------
Needs CLOUDFLARE_READ_TOKEN: a token separate from the deploy token, scoped to
this zone with Zone->WAF->Read (and Zone->Zone->Read unless CLOUDFLARE_ZONE_ID
is set). It is deliberately NOT the deploy token: reading configuration does
not require the ability to deploy, and the deploy token should not gain scope
it has no use for.

Without the token this script SKIPS rather than fails. A gate that breaks the
nightly deploy the moment a secret is missing would be removed within a week,
and the deploy itself is not what this protects. It says so loudly, and the
monthly check asks whether it is armed.

Usage:  python3 scripts/verify_edge_rules.py
Exit 0 = verified, or skipped for want of a token. Exit 1 = the rule is not
what it should be.
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.cloudflare.com/client/v4"
ZONE_NAME = "mcpjunction.ai"

# Cloudflare Workers free plan. If the plan changes, change this -- the
# arithmetic below is only meaningful relative to the real quota.
WORKERS_DAILY_QUOTA = 100_000

# The threshold as reviewed on 2026-09-06: 100 requests per 10 seconds per IP.
# The warning fires when the live rule is LOOSER than this, not when it falls
# short of some ideal. That distinction is the whole point: no setting available
# on the free plan keeps a single source under the Workers quota except 10/10s,
# which is tight enough to risk blocking a legitimate agent burst. A gate that
# warned on every acceptable configuration would be noise, and noise gets
# ignored -- so it warns only when someone has widened the gap since it was last
# thought about. Tightening the rule is expected to make this constant stale;
# lower it to match and the check keeps its meaning.
ACCEPTED_REQUESTS = 100
ACCEPTED_PERIOD = 10

TOKEN = os.environ.get("CLOUDFLARE_READ_TOKEN", "").strip()
ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "").strip()


def api_get(path):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        sys.exit(f"::error::Cloudflare API {path} -> HTTP {exc.code}: {body}")
    except Exception as exc:                       # noqa: BLE001
        sys.exit(f"::error::Cloudflare API {path} unreachable: {exc}")

    if not payload.get("success"):
        errs = "; ".join(str(e.get("message")) for e in payload.get("errors") or [])
        sys.exit(f"::error::Cloudflare API {path} returned success=false: {errs}")
    return payload["result"]


def resolve_zone_id():
    if ZONE_ID:
        return ZONE_ID
    zones = api_get(f"/zones?name={ZONE_NAME}")
    if not zones:
        sys.exit(f"::error::no zone named {ZONE_NAME} visible to this token. "
                 f"Check the token is scoped to that zone, or set "
                 f"CLOUDFLARE_ZONE_ID to skip this lookup (it needs "
                 f"Zone->Zone->Read).")
    return zones[0]["id"]


def main():
    if not TOKEN:
        print("=" * 72)
        print("NOTICE: edge rule verification SKIPPED -- CLOUDFLARE_READ_TOKEN is unset.")
        print()
        print("The rate limiting rule on /mcp is therefore unverified: it could")
        print("have been deleted or disabled and nothing here would know. This")
        print("check is inert until the secret exists.")
        print()
        print("To arm it: create a Cloudflare API token scoped to the")
        print(f"{ZONE_NAME} zone with Zone->WAF->Read and Zone->Zone->Read, then")
        print("add it as the repository secret CLOUDFLARE_READ_TOKEN.")
        print("See docs/OPERATIONS.md, 'Security maintenance'.")
        print("=" * 72)
        return 0

    zone_id = resolve_zone_id()
    ruleset = api_get(f"/zones/{zone_id}/rulesets/phases/http_ratelimit/entrypoint")
    rules = ruleset.get("rules") or []

    # Match on the expression rather than the rule name: a name is a label
    # someone can change while the rule keeps working, and renaming a rule
    # should not fail a deploy. What matters is that /mcp is covered.
    mcp_rules = [r for r in rules if "/mcp" in str(r.get("expression", ""))]

    if not mcp_rules:
        print(f"::error::No rate limiting rule covering /mcp in zone {ZONE_NAME}.")
        print(f"  The zone has {len(rules)} rate limiting rule(s), none matching /mcp.")
        print("  worker/index.js documents this rule as the flood protection for")
        print("  an unauthenticated, CORS-* endpoint. If it was removed on purpose,")
        print("  update that comment and this check together.")
        return 1

    failed = False
    for rule in mcp_rules:
        name = rule.get("description") or rule.get("ref") or "(unnamed)"
        enabled = rule.get("enabled", False)
        action = str(rule.get("action", "")).lower()
        rl = rule.get("ratelimit") or {}
        requests = rl.get("requests_per_period")
        period = rl.get("period")
        chars = ", ".join(rl.get("characteristics") or []) or "(unspecified)"

        print(f"rate limiting rule: {name}")
        print(f"  expression      : {rule.get('expression')}")
        print(f"  enabled         : {enabled}")
        print(f"  action          : {action}")
        print(f"  threshold       : {requests} requests / {period}s per [{chars}]")

        if not enabled:
            print(f"::error::rule '{name}' exists but is DISABLED")
            failed = True
        if action != "block":
            print(f"::error::rule '{name}' action is '{action}', expected 'block'")
            failed = True

        # Advisory. See the module docstring for why this does not fail.
        if requests and period:
            per_second = requests / period
            ceiling = per_second * 86400
            ratio = ceiling / WORKERS_DAILY_QUOTA
            hours = WORKERS_DAILY_QUOTA / per_second / 3600
            accepted_ceiling = ACCEPTED_REQUESTS / ACCEPTED_PERIOD * 86400
            print(f"  sustained ceiling: {ceiling:,.0f} requests/day from one source "
                  f"({ratio:.1f}x the {WORKERS_DAILY_QUOTA:,}/day Workers quota; "
                  f"quota gone in {hours:.1f}h at that rate)")

            if ceiling > accepted_ceiling:
                print(f"::warning::threshold has been LOOSENED since review: "
                      f"{requests}/{period}s permits {ceiling:,.0f} req/day from a "
                      f"single source, against {ACCEPTED_REQUESTS}/{ACCEPTED_PERIOD}s "
                      f"({accepted_ceiling:,.0f}/day) as reviewed. run_worker_first "
                      f"means exhausting the Worker quota takes /servers/* down with "
                      f"/mcp. Tighten it, or update ACCEPTED_REQUESTS in this file to "
                      f"record the new decision.")
            elif ceiling < accepted_ceiling:
                print(f"  note: tighter than the {ACCEPTED_REQUESTS}/{ACCEPTED_PERIOD}s "
                      f"recorded in this script — update ACCEPTED_REQUESTS to keep the "
                      f"drift check meaningful.")

    if failed:
        return 1
    print("edge rules OK: /mcp is rate limited, enabled, blocking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
