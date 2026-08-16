# mcpjunction.ai

**A directory of Model Context Protocol servers, rebuilt nightly from public GitHub
metadata.** Roughly 1,800 servers across 20 categories, published as a website, a
downloadable dataset, and an MCP endpoint your agent can query directly.

[mcpjunction.ai](https://mcpjunction.ai) · [Dataset](https://mcpjunction.ai/data) ·
[Categories](https://mcpjunction.ai/categories) · [Licensing](https://mcpjunction.ai/licensing)

> Not affiliated with Anthropic or the Model Context Protocol project.

This repository is the whole thing: the pipeline that builds the dataset, the Astro site
that renders it, and the Cloudflare Worker that serves it.

## Use the data

Three ways in, all public and all free to read.

**Bulk download.** The full directory, regenerated nightly with a `generated_at` timestamp.

```bash
curl -O https://mcpjunction.ai/data/mcp_servers.json
```

- [`mcp_servers.json`](https://mcpjunction.ai/data/mcp_servers.json) — ~2.3 MB, 28 fields
  per server plus a dataset envelope with counts and per-category totals
- [`mcp_servers.csv`](https://mcpjunction.ai/data/mcp_servers.csv) — the same data as 16
  flat columns

**Query it from an agent.** `/mcp` is itself an MCP server — streamable HTTP, stateless
JSON-RPC over POST, protocol version `2025-06-18`, no authentication.

```bash
claude mcp add --transport http mcpjunction https://mcpjunction.ai/mcp
```

| Tool | What it does |
| --- | --- |
| `search_servers` | Free-text search, optionally filtered by `category` and `language` |
| `get_server` | One server by id (`owner--repo`, e.g. `microsoft--playwright-mcp`) |
| `list_categories` | The 20 categories with active counts |
| `get_dataset_info` | Counts, `generated_at`, source, and licensing terms |

`GET /mcp` returns 405 by design; POST your JSON-RPC messages. JSON-RPC batching is not
supported — it was removed in protocol `2025-06-18`.

**Read it as markdown.** Every server and category page has a clean markdown twin with no
navigation or styling to strip. Either negotiate for it:

```bash
curl -H 'Accept: text/markdown' https://mcpjunction.ai/servers/microsoft--playwright-mcp
```

…or just append `.md` to the canonical URL —
[`/servers/microsoft--playwright-mcp.md`](https://mcpjunction.ai/servers/microsoft--playwright-mcp.md),
[`/categories/databases.md`](https://mcpjunction.ai/categories/databases.md). Each HTML page
advertises its twin via `<link rel="alternate" type="text/markdown">`.

Machine-readable entry points are collected in
[`llms.txt`](https://mcpjunction.ai/llms.txt).

## How a server gets listed

Listing is automatic. There is no submission form, and none is planned — the pipeline runs
five GitHub search queries (`topic:mcp-server`, `topic:model-context-protocol`,
`topic:mcp`, and two name/description phrase searches), then keeps repositories that clear
a 2-star floor and match a Model Context Protocol name/topic heuristic. If your server is
on GitHub and meets that bar, it will appear on the next nightly run.

**Corrections, removals, and licensing:** <licensing@mcpjunction.ai>, acknowledged within
three business days. Please don't open pull requests against `public/data/` — that file is
regenerated nightly and your edit would be overwritten.

## How the data is kept honest

A directory other people cite has to fail safe. These are the constraints the code
actually enforces:

- **Automation cannot promote anything.** `security_reviewed`, `verified_badge`,
  `sponsor_tier`, `editorial_notes`, and `editorial_summary` are set by hand and only
  carried forward by the pipeline — never written by it. A machine cannot grant a badge or
  a security clearance here. These fields are currently unset across the entire dataset; a
  written summary, when one exists, is a description and **not** a security review.
- **Collapse guard.** A run aborts if the active server count falls more than 10% against
  the previous dataset, or if more than 50 servers would be newly delisted at once. A
  separate check refuses to deploy below 200 servers. A bad day at the GitHub API should
  not silently gut the directory.
- **Delisted repositories persist 30 days** as `status: archived_or_removed` with a
  `delisted_at` timestamp, then drop. Stable URLs, without unbounded growth.
- **Identity guard.** If a repository's numeric GitHub id changes under the same
  `owner--repo` name — a rename, or a released username claimed by someone else — the
  editorial state is dropped rather than inherited.
- **CSV injection is neutralised.** Cells beginning `=`, `+`, `-`, or `@` are quote-prefixed
  before publication. Repository descriptions are attacker-controllable: anyone can name a
  GitHub repo.
- **Install hints never auto-confirm.** No `npx -y`, no `--yes`. The registry package
  sharing a repository's name may belong to someone else entirely, so hints are published
  as unverified suggestions.
- **No dead links.** The sitemap lists only files present on disk at build time.
- **One source, used as documented.** The official GitHub REST API, authenticated and
  rate-limit aware, public repository metadata only.

## How it's built

```
src/              Astro static site — pages, layouts, components
worker/           Cloudflare Worker — the /mcp server and markdown negotiation
scripts/          pipeline.py (GitHub API → dataset), build_sitemap.py
categories.json   Taxonomy: 20 categories, first match in file order wins
editorial/        Human-written server summaries (summaries.md)
public/           Passthrough assets — robots.txt, license.xml, llms.txt, _headers, data/
dist/             Build output and the Worker's asset root (not committed)
```

Every night a GitHub Action runs `pipeline.py`, builds the site with Astro, generates the
sitemap, commits the refreshed dataset, deploys the Worker, and then verifies the live
result — licensing surface, `/mcp` handshake, crawler access rules, and markdown
negotiation — before it calls the run a success.

Locally:

```bash
npm ci && npm run dev
```

The pipeline needs Python 3 and a `GITHUB_TOKEN`; deploys need Cloudflare credentials. See
[`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Licensing

**The code is MIT.** `src/`, `worker/`, `scripts/`, and the configuration are yours to
reuse — see [`LICENSE`](LICENSE).

**The dataset is not.** `public/data/**` is excluded from the MIT grant and governed by the
RSL terms in [`public/license.xml`](public/license.xml): search indexing is free, agent and
inference-time use is free site-wide with attribution during the launch phase, and AI
training requires a license. Bulk `/data/` retrieval carries stricter terms. Details at
[mcpjunction.ai/licensing](https://mcpjunction.ai/licensing); see also [`NOTICE`](NOTICE).

Citing us is easy and appreciated: *via mcpjunction.ai*.
