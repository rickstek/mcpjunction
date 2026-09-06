# Operations

Everything needed to run, deploy, and troubleshoot mcpjunction.ai. For what the project
*is*, see the [README](../README.md).

## Deployment model

The site is a static Astro build served by a Cloudflare Worker.

- `astro build` renders `dist/`, which is the Worker's asset root
  (`assets.directory` in `wrangler.jsonc`).
- `public/` is passthrough only — `robots.txt`, `license.xml`, `llms.txt`, `_headers`, the
  IndexNow key, and `data/`. Astro copies it into `dist/` unchanged.
- `worker/index.js` runs ahead of the assets binding for `/mcp`, `/servers/*`, and
  `/categories/*` (`assets.run_worker_first`). It serves the MCP endpoint and handles
  `Accept: text/markdown` negotiation; everything else falls through to `env.ASSETS.fetch`.
- The Worker name in `wrangler.jsonc` must match the existing Worker exactly. Custom
  domains are attached in the Cloudflare dashboard, not in config.

## Secrets

Two repository secrets, under Settings → Secrets and variables → Actions:

| Secret | Where to get it |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com → My Profile → API Tokens → Create Token → *Edit Cloudflare Workers* template, scoped to this account and the mcpjunction.ai zone. Shown once. |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → Workers & Pages, right sidebar |

**No GitHub PAT is needed.** The workflow's built-in `GITHUB_TOKEN` authenticates the
GitHub API calls the pipeline makes and gives it the authenticated rate limit.

## The nightly workflow

`.github/workflows/nightly.yml` — *Nightly refresh and deploy*. Triggers: cron
`17 6 * * *` (06:17 UTC), any push to `main`, and manual dispatch. Concurrency group
`nightly-deploy` with `cancel-in-progress: false`, 25-minute timeout, Node 24, all actions
pinned to full SHAs.

One input: **`skip_data_refresh`** (default `false`). It gates only the pipeline step —
everything else, including the deploy, still runs.

Order of operations:

1. **Refresh dataset** — `scripts/pipeline.py` with `PAGES_PER_QUERY=6`, `REQUEST_SLEEP=2.5`
2. **Sanity check** — required files non-empty, then `scripts/verify_dataset.py`: dataset
   `count >= 200`, plus the data-shape invariants (see *Dataset invariants* below) or the
   run stops before the build
3. **Build** — `npm ci`, `astro build`, then `scripts/build_sitemap.py`
4. **Post-build verification** — 11 required files in `dist/`, more than 100 server pages,
   more than 5 category pages, a byte-identity `diff` of the five passthrough files
   between `public/` and `dist/`, and every category slug present in `llms.txt`
5. **Commit** refreshed data as `mcpjunction-bot` (adds `public/data` and
   `state/lastmod.json`, rebases, pushes)
6. **Deploy** via `cloudflare/wrangler-action`

Then six live verification gates. A failure in any of them means the deploy went out but
something is wrong at the edge — that is what each one is telling you:

| Gate | Fails when |
| --- | --- |
| Licensing surface + declared URL sample | A core URL redirects instead of returning 200 on the first hop, or a random 25-URL sitemap sample breaks |
| MCP endpoint | `initialize` doesn't return `serverInfo`, or `tools/list` is missing `search_servers` |
| AI agent access | One of 7 allowed user agents is blocked, or one of 4 training crawlers gets through |
| Markdown content negotiation | `Accept: text/markdown` doesn't return markdown, or a browser Accept doesn't return HTML |
| llms.txt declared URLs | Any URL advertised in `llms.txt` isn't a zero-redirect 200 |
| robots.txt at the edge | The live file is missing its `Sitemap:`, `License:`, or `Content-Signal:` lines |

IndexNow submission runs between them with `continue-on-error: true` — it is allowed to
fail without failing the run.

## Sitemap `lastmod` and `state/lastmod.json`

`scripts/build_sitemap.py` gives every URL a content signature and stores it in
`state/lastmod.json`. A URL keeps its recorded `lastmod` until its signature moves. **That
file is committed by the nightly and is not a build artifact** — delete it and every
`lastmod` resets to the next build's date, which is the uniform-date state this replaced.

- Server-page signatures deliberately exclude `stars`, `forks`, `open_issues` and
  `pushed_at`. Measured across two consecutive nightlies, 940 of 1,830 servers changed a
  star count and 504 changed `pushed_at`, against 25 that changed anything a reader would
  call an edit. `lastmod` means last *significant* modification.
- Pages that are not data-derived (`/`, `/categories`, `/data`, `/licensing`) are signed
  over their rendered bytes.
- The URLs whose signature moved go to `state/changed_urls.txt` (gitignored) and that list —
  not the whole sitemap — is what gets submitted to IndexNow. A realistic night is around
  35 URLs. On a bootstrap run with no prior state, submission is skipped entirely rather
  than firing 1,800 URLs at once.

Any page emitting `<meta name="robots" content="noindex">` is left out of `sitemap.xml`
automatically — the template decides and the sitemap follows, so the two cannot disagree.
Today that is the 31 delisted servers and `/categories/uncategorized`.

## Adding a category means editing `llms.txt`

`public/llms.txt` enumerates every category URL by hand, because it is a passthrough file
rather than a generated one. A post-build gate fails the run if a slug in `categories.json`
is missing from it. So a new category is a three-file change: `categories.json`,
`public/llms.txt`, and whatever prose references the count.

### Manual dry run

Actions tab → *Nightly refresh and deploy* → Run workflow, with **`skip_data_refresh` =
true**. This deploys current files without touching the GitHub API, so a wrong Worker name
surfaces in about a minute with nothing at stake.

## Cloudflare managed robots.txt must stay OFF

`public/robots.txt` is self-contained and authoritative. It carries the Content Signals
policy text inline, the AI-crawler groups, **and** the `Sitemap:` and `License:` directives.

Cloudflare's "managed robots.txt" is documented as *prepending* its block to your file, but
the observed behaviour was that it **replaced** the file outright — silently dropping the
`License:` pointer to `license.xml`, which breaks RSL discovery, along with the `Sitemap:`
line. Turning it off costs nothing: the Content Signals policy is already in our file, and
actual enforcement comes from AI Crawl Control, a separate feature that stays enabled.

Verify after any Cloudflare bot-settings change:

```bash
curl -s https://mcpjunction.ai/robots.txt | tail -5
```

You should see the `Sitemap:` and `License:` lines. If the output ends at
`# END Cloudflare Managed Content`, managed robots.txt has been re-enabled.

The nightly workflow's last step checks this automatically, so a red run on
*Verify robots.txt directives survived the edge* usually means exactly this.

## Pipeline knobs

`scripts/pipeline.py` reads these from the environment:

| Variable | Default | Notes |
| --- | --- | --- |
| `GITHUB_TOKEN` | — | Without it the pipeline still runs, on the unauthenticated rate limit |
| `PAGES_PER_QUERY` | `4` | CI sets `6` |
| `REQUEST_SLEEP` | `2.5` with a token, `7.0` without | Seconds between API calls |
| `MIN_STARS` | `2` | Inclusion floor |
| `ALLOW_COLLAPSE` | unset | Set to `1` to override the collapse guard. Only when a large drop is known-good. |

The collapse guard aborts the run if the active count falls more than 10% against the
previous dataset, or if more than 50 servers would be newly delisted in a single run. An
unreadable previous dataset is fatal rather than a fresh start — a fresh crawl would still
clear the 200-server floor while silently erasing every editorial field.

## Editing curated fields

Two separate mechanisms. The pipeline preserves both across nightly runs and never writes
either.

**Summaries** live in `editorial/summaries.md`, keyed by `## owner--repo` headings. That
file is the source of truth: deleting an entry removes it from the site on the next run.
House style is documented at the top of the file — 40 to 80 words, original wording, no
superlatives, and never any implication that a security review took place. An id with no
matching dataset entry prints a warning during the run.

**Flags** live in `public/data/mcp_servers.json` itself: `security_reviewed`,
`security_notes`, `verified_badge`, `sponsor_tier`, `editorial_notes`. Edit by hand and
commit; `merge()` carries them forward. They are dropped deliberately if the repository's
numeric GitHub id changes under the same `owner--repo` id, which covers renames and
released usernames.

Those five are **frozen fields**: `verify_dataset.py` compares them against the copy in
`HEAD` on every run and fails the build if any changed. A hand edit passes because it is
committed first, so `HEAD` already agrees. What cannot pass is automation introducing a
trust signal or silently losing one — the pipeline claiming a server is
`security_reviewed`, or a carry-forward regression wiping a `sponsor_tier`. Two things
follow from this: **commit the JSON edit before the next run**, and note that
`security_notes` and `editorial_notes` are published in the dataset but rendered on no
page — they are world-readable and permanent in git history, so write them as if a repo
owner will read them, because one can.

## Taxonomy

`categories.json` at the repo root — 24 categories, each with a slug, name, description,
and `match` keyword list. Assignment is **first match in file order**, so ordering is
policy: domain integrations deliberately precede the `ai-*` family, which is why a Postgres
MCP server for Cursor lands in `databases` rather than `ai-coding`.

Slugs are URLs, so they are permanent once published. Adding a slug is free; retiring one
needs a redirect. Delisted entries are re-categorised on every run so a retired slug cannot
leave a broken `/categories/<slug>` link behind.

## Weekly maintenance

Five minutes. Nothing here is automated, because each item ends in a judgement call.

**1. Glance at the `uncategorized` count.**

```bash
curl -s https://mcpjunction.ai/data/mcp_servers.json \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['categories'].get('uncategorized',0), 'of', d['count'])"
```

It sat at 200 of 1,808 (11%) at launch. Rising share means the taxonomy is drifting
behind the ecosystem — read the top entries by stars and decide whether they justify a
new category or just need `match` terms added to an existing one. Note that
`uncategorized` is the bucket the *canonical* MCP repo landed in, so a high count is not
only cosmetic: it means real authority is parked on a page that says nothing. The page
now carries `noindex` (set via `"noindex": true` in `categories.json`) and is held out of
the sitemap. That is a stopgap, not a fix — it stops the thin page competing for the
directory's own terms; it does not get those servers categorised.

**2. Check the robotics split trigger.** Robotics terms (`ros`, `ros2`, `moveit`,
`gazebo`, `drone`, `uav`, `robot`, `robotics`, `embodied-ai`) are deliberately folded
into `iot-hardware` because only ~3 servers matched cleanly at launch — a category page
with three entries reads abandoned. When clean robotics matches cross roughly **15**,
split `robotics` into its own slug. Adding a slug is free; retiring one needs a redirect,
which is why the trigger errs late.

**3. Skim the newest entries.** Sort the dataset by `first_seen` and read the top few.
This is the only routine check on inclusion quality — the pipeline's filter is keyword
based and will occasionally admit something that merely mentions MCP. Note that
`first_seen` falls back to `created_at` for any entry the pipeline has not seen before,
and every entry in the dataset currently has the two equal — so this sorts by repository
creation date, not by when we listed it. The homepage's "Newest repositories" block is
labelled accordingly.

**4. Confirm the nightlies are green.** Actions tab. A red run after a *successful*
deploy means an edge verification gate failed, not that the site is down — the table
above says which. Two consecutive greens is the health bar.

**5. Glance at AI Crawl Control → Security.** New crawlers appear in that table
regularly and default to allowed. Check that anything new in the *AI Crawler* category
is blocked and anything in *AI Assistant* is not, and watch the robots.txt-violations
column — a crawler ignoring the published policy is a licensing-enforcement lead, not
just a nuisance. Note that Cloudflare miscategorises `Claude-User` as an AI Crawler; it
is a user-initiated fetcher and must stay allowed.

## Honouring a takedown request

`exclusions.json` at the repo root. This is the mechanism behind the promise made in the
site footer, the README, `/licensing`, `/badge` and `/data` — the last of which commits to
**3 business days**, so treat that as the clock.

Deleting the entry from `public/data/mcp_servers.json` by hand does **nothing lasting**.
Every run rebuilds the dataset from the GitHub API, so the repository reappears the same
night. The removal has to be recorded in a file the run reads.

```json
{
  "ids":    [{ "id": "owner--repo", "reason": "owner takedown request", "date": "2026-09-06" }],
  "owners": [{ "owner": "someone",  "reason": "erasure request",        "date": "2026-09-06" }]
}
```

**`ids` removes one repository. `owners` removes every repository from that account.** Use
`owners` for an erasure request: the request is about the handle, and a public GitHub owner
handle is the only personal data this directory republishes, so honouring one properly
cannot mean chasing repo names one at a time.

Keep `reason` and `date` filled in. This file is the record that a request was honoured,
and it is the first thing to read if the same repository is ever proposed for re-listing.

What happens on the next run: the entry is dropped from the carried-forward set *and*
after the merge, so it leaves the JSON, the CSV, the sitemap, `/mcp` and every page, and
`/servers/<id>` returns 404. It does **not** get the 30-day delisting grace window — that
window exists to keep citations alive, which is the opposite of what was asked for. The
exclusion is re-applied every night, so it holds permanently.

To publish inside the 3-day window rather than waiting for 06:17 UTC, commit and push:
every push to `main` runs the full refresh and deploy.

A malformed id or handle **fails the run** rather than being skipped. A typo that silently
excluded nothing would leave a request unhonoured while the file said otherwise.

## Security maintenance

Calibrate against what is actually at risk. This site has no accounts, no sessions, no
database, no PII collected and no payments — there is nothing to breach in the usual
sense. The exposure is exactly two things: **the credentials in the Actions environment**,
and **defacement through the nightly pipeline**, which performs roughly 365 unattended
production deploys a year from ~1,900 third-party repositories.

That is why there is no scanner on a schedule. Scanning code that has not changed on a
calendar is theatre. What belongs on a calendar is only what **decays on its own** —
credentials, third-party advisories, dashboard configuration, upstream data shape. Code
review is event-driven.

| Cadence | What | Owner |
| --- | --- | --- |
| Every run | `scripts/verify_dataset.py` — dataset invariants, before the build | automated |
| Continuous | Dependabot (`.github/dependabot.yml`) for `npm` and `github-actions` | automated; review PRs |
| Monthly, ~15 min | Cloudflare API token scope and expiry; `permissions:` in `nightly.yml` still `contents: write` and nothing more; Cloudflare rules still match what the code claims — **including the rate-limit rule** | human |
| Quarterly, ~2 hrs | Full review: rotate `CLOUDFLARE_API_TOKEN`, re-run the data scanner, and re-read every public claim (footer, README, licensing, badge) against what the code actually does | human |
| On change | Any edit to `worker/index.js`, `scripts/pipeline.py`, `nightly.yml`, or a new public surface | human |

The quarterly **claims-versus-code** pass is the highest-value item and the one nobody
schedules. Copy gets written faster than code, and nothing in CI checks prose against
behaviour. The 2026-09-06 review found two instances, both since closed, and they are worth
keeping as worked examples of the two ways this drift resolves:

- The footer, README, `/licensing`, `/data` and `/badge` all promised that takedown
  requests are honoured — `/data` commits to **3 business days** — while the pipeline had
  no exclusion mechanism, so a hand-deleted entry returned on the next refresh. Fixed by
  making the claim true: see *Honouring a takedown request* below.
- `worker/index.js` asserted in a comment that an edge rate-limiting rule covered request
  floods. Nothing in this repository configures one and no gate proves one exists. Fixed
  the other way — by correcting the claim, since the infrastructure half is a Cloudflare
  dashboard question that the repo cannot answer. **If you add that rule, update the
  comment and add a gate.**

Quarterly is roughly how fast new public claims accumulate.

Not worth doing: DAST, penetration testing, WAF tuning. There is no input the site accepts,
no session to hijack and no query to inject for them to find.

### Dataset invariants

`scripts/verify_dataset.py` runs in step 2, before the build, so a violation never becomes
a site and never reaches the deploy step — the previously deployed version stays live.
Each check backs a guarantee something downstream already assumes:

| Invariant | What it protects |
| --- | --- |
| `count >= 200` | A bad night at the GitHub API cannot publish a gutted directory over a good one |
| id matches `^[a-z0-9._+-]+--[a-z0-9._+-]+$` | `id` is a URL path segment on three surfaces (asset store, the Worker's markdown rewrite, the sitemap); a separator or dot-segment is a traversal primitive |
| Category is in `categories.json` | A retired slug cannot leave a broken `/categories/<slug>` link |
| Homepage is `http(s)://` or null | `javascript:` and scheme-less values never reach an `href` |
| Install hint has no shell metacharacters in the command half | The hint renders in a code block for a human to paste into a shell. Our own `CLONE_NOTE` annotations contain `&&`, but only after the `#` marker, which is why only the command half is checked |
| Status in `{active, archived_or_removed}` | Catches an invented state such as `sponsored` |
| Field allowlist | `_hay` and `_topics` are precomputed search fields that must never persist into the published artifact |
| Topic slugs URL-safe | Approved topics become `/topics/<tag>` |
| Frozen editorial fields match `HEAD` | Automation can neither invent a trust signal nor drop one a human set — see *Editing curated fields* |
| No excluded id or owner is published | A takedown that silently regressed would show only as a repo quietly reappearing, and nobody watches for that — see *Honouring a takedown request* |
| CSV formula guard applied | Every cell starting `= + - @ \t \r` is actually `'`-prefixed, not just supposed to be |

**Deliberately not checked: the content of repository descriptions.** They are arbitrary
third-party prose, republished as such and labelled as such on every surface.
Pattern-matching them for "suspicious" text would produce a gate that cries wolf nightly
and gets switched off within a week.

Run it locally against the current data with:

```bash
python3 scripts/verify_dataset.py
```

## Troubleshooting

**A run failed at "Sanity check dataset before build."** Either the GitHub API returned too
little data, or a dataset invariant was violated — the log names which and prints up to
five offending entries. The previous dataset is untouched and the live site is unchanged.
For a volume failure, re-run rather than intervening. For an invariant failure, read the
named entries first: the gate is asserting something downstream depends on, so a "fix" that
loosens the check needs the downstream consumer checked too.

**A run failed at "Post-build verification."** Either Astro produced fewer pages than
expected, or a `public/` file no longer matches its `dist/` copy. Check the `diff` output in
the log.

**`/mcp` verification failed but the site is up.** The Worker deployed but
`run_worker_first` may not be matching. Confirm the `assets.run_worker_first` list in
`wrangler.jsonc` still contains `/mcp` and `/mcp/*`.

**Numbers render as `36.136` instead of `36,136`.** Locale leakage. `src/lib/format.ts`
pins `Intl.NumberFormat('en-US')` for this reason — don't call `toLocaleString()` directly.

## Note on `scripts/pull_live.sh`

A one-time bootstrap from before the Astro migration, kept for reference. It mirrors the
live site into `public/` and fetches files such as `index.html` and `licensing.html` that
are now generated into `dist/` by Astro. **Do not run it** — it would write stale artifacts
into the passthrough directory.
