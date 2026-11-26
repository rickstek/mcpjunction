#!/usr/bin/env python3
"""Find out what actually happened to repositories the nightly crawl did not return.

The crawl is five GitHub searches, each capped at the top 600 results by stars
(PAGES_PER_QUERY=6). Until 2026-11 every previously listed repository missing from
those results was marked `archived_or_removed`, and its page said the repository
"has been archived or removed from GitHub". Measured on 2026-11-26 across all 252
such entries, that sentence was true for 32: 189 were live MCP projects that had
merely fallen below the star cutoff (1,623 stars for `topic:mcp` by then), 21 had
been renamed, 7 no longer described themselves as MCP, and 3 were missed by a
transient search failure.

A search not returning a repository is not evidence about the repository. This
module asks GitHub directly, through GraphQL so that one request covers 40
repositories (measured cost: 1 rate-limit point per batch, against the 1,000
points an hour the workflow's GITHUB_TOKEN gets).

resolve() returns, per entry id, one of:
  ("live", repo)     exists, same repository, not archived
  ("moved", repo)    GraphQL followed a rename/transfer; repo is the new identity
  ("archived", repo) archived by its owner
  ("removed", None)  NOT_FOUND, or the name now belongs to a different repository
  ("error", None)    the lookup itself failed -- callers must not treat this as
                     evidence of anything

`repo` is shaped like a REST search item so pipeline.normalize() accepts it.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BATCH = 40
RETRIES = 3
FIELDS = (
    "databaseId nameWithOwner name owner{login} description url homepageUrl "
    "isArchived stargazerCount forkCount createdAt pushedAt primaryLanguage{name} "
    "licenseInfo{spdxId} repositoryTopics(first:20){nodes{topic{name}}} "
    "issues(states:OPEN){totalCount} pullRequests(states:OPEN){totalCount}"
)


def _as_rest(n):
    """GraphQL repository node -> the REST search-item shape normalize() reads."""
    lic = n.get("licenseInfo")
    return {
        "id": n.get("databaseId"),
        "full_name": n.get("nameWithOwner"),
        "name": n.get("name"),
        "owner": {"login": (n.get("owner") or {}).get("login")},
        "description": n.get("description"),
        "html_url": n.get("url"),
        "homepage": n.get("homepageUrl"),
        "archived": bool(n.get("isArchived")),
        "stargazers_count": n.get("stargazerCount", 0),
        "forks_count": n.get("forkCount", 0),
        # REST's open_issues_count counts open pull requests too.
        "open_issues_count": ((n.get("issues") or {}).get("totalCount", 0)
                              + (n.get("pullRequests") or {}).get("totalCount", 0)),
        "created_at": n.get("createdAt"),
        "pushed_at": n.get("pushedAt"),
        "language": (n.get("primaryLanguage") or {}).get("name"),
        # REST reports an unrecognised license as NOASSERTION; match it so a
        # retained entry's license field does not flip and churn its page.
        "license": ({"spdx_id": lic.get("spdxId") or "NOASSERTION"} if lic else None),
        "topics": [t["topic"]["name"] for t in
                   ((n.get("repositoryTopics") or {}).get("nodes") or [])],
    }


def _post(query, token, user_agent):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent,
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve(entries, token, user_agent):
    """entries: dicts with id, full_name, optional github_repo_id. Returns {id: (kind, repo)}."""
    out = {e["id"]: ("error", None) for e in entries}
    if not token:
        print("vanished: no GITHUB_TOKEN; cannot look anything up -- every listed "
              "entry the crawl missed stays as it was", file=sys.stderr)
        return out
    cost = 0
    for start in range(0, len(entries), BATCH):
        batch = entries[start:start + BATCH]
        parts = []
        for i, e in enumerate(batch):
            owner, _, name = (e.get("full_name") or "").partition("/")
            if not owner or not name:
                continue
            parts.append(f"r{i}: repository(owner: {json.dumps(owner)}, "
                         f"name: {json.dumps(name)}) {{ {FIELDS} }}")
        if not parts:
            continue
        j = None
        for attempt in range(RETRIES):
            try:
                j = _post("query { rateLimit { cost } " + " ".join(parts) + " }",
                          token, user_agent)
                break
            except (urllib.error.URLError, OSError, ValueError) as err:
                # Measured 2026-11-26: a whole batch failed once and succeeded
                # on an immediate retry. Transient, so retry before giving up.
                print(f"vanished: batch {start // BATCH} attempt {attempt + 1} "
                      f"failed ({err})", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        if j is None:
            print(f"vanished: batch {start // BATCH} gave up; its entries stay "
                  f"as they were", file=sys.stderr)
            continue
        data = j.get("data") or {}
        cost += (data.get("rateLimit") or {}).get("cost", 0)
        not_found = {err.get("path", [None])[0] for err in (j.get("errors") or [])
                     if err.get("type") == "NOT_FOUND"}
        for i, e in enumerate(batch):
            key = f"r{i}"
            node = data.get(key)
            if node is None:
                out[e["id"]] = ("removed", None) if key in not_found else ("error", None)
                continue
            repo = _as_rest(node)
            old_gh = e.get("github_repo_id")
            if old_gh and repo["id"] and old_gh != repo["id"]:
                # The name now belongs to a different repository: the one we
                # listed is gone. Never hand its page to the newcomer.
                out[e["id"]] = ("removed", None)
            elif repo["archived"]:
                out[e["id"]] = ("archived", repo)
            elif (repo["full_name"] or "").lower() != (e.get("full_name") or "").lower():
                out[e["id"]] = ("moved", repo)
            else:
                out[e["id"]] = ("live", repo)
    kinds = {}
    for k, _ in out.values():
        kinds[k] = kinds.get(k, 0) + 1
    print(f"vanished: looked up {len(entries)} listed repos the crawl missed "
          f"({cost} GraphQL points): {kinds}")
    if kinds.get("error"):
        print(f"::warning::vanished: {kinds['error']} lookups failed; those entries "
              f"were left unchanged rather than delisted on no evidence")
    return out
