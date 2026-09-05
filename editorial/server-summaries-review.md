# Server summaries — review batch (2026-09-05)

DRAFTS FOR REVIEW. Nothing here is live. `summaries.md` is read by the pipeline
every night and anything under a heading there publishes at the next 06:17 UTC
refresh, so unapproved drafts must not go into it. On approval, each `##` entry
below is copied into `summaries.md` under its `# Category` header, and this
file is deleted.

## Why these eight

Selected by data, not by size. The Search Console export of 2026-09-05 shows
the site ranking on page 1 for exact-name lookups and on pages 5–9 for generic
intent queries. These eight server pages already receive impressions on
intent queries at positions 39–77 ("firecrawl mcp server", "n8n mcp server",
"remote mcp server", "linkedin mcp", "mcp proxy server", "quickbooks mcp",
"figma console mcp", "argocd mcp"). A summary here is the cleanest experiment
available: does a paragraph of real prose move a page Google already serves?
Measure by the position on exactly those queries in the next export.

## House style (from summaries.md)

40–80 words. What it does, who it is for, one thing that distinguishes it; a
caveat when true and useful. Own words — never paraphrase the GitHub
description, which renders on the same page. No superlatives, no marketing
voice. No facts that go stale: no counts, versions, or dates. Never imply
endorsement or security review. Every claim below was checked against the
repository README, not inferred from the description.

---

# Browser Automation  (browser-automation)

## firecrawl--firecrawl-mcp-server

<!--
  firecrawl/firecrawl-mcp-server  ·  JavaScript  ·  MIT
  https://github.com/firecrawl/firecrawl-mcp-server
  page: https://mcpjunction.ai/servers/firecrawl--firecrawl-mcp-server
  install hint: npx firecrawl-mcp-server
  GitHub says: Official Firecrawl MCP Server - Adds powerful web scraping and search to Cursor, Claude and any other LLM clients.
-->
Puts Firecrawl's scraping, crawling, and web search behind MCP tools, so an
agent gets a page as clean text or runs a site crawl instead of parsing raw
HTML itself. Two ways to run it: the hosted endpoint, where some tools work
without an account and the full set sits behind a key, or against your own
self-hosted Firecrawl. Retries and rate limiting are built in, which matters
once an agent starts crawling in loops.

# Developer Tools  (devtools)

## n8n-io--n8n

<!--
  n8n-io/n8n  ·  TypeScript  ·  fair-code (NOASSERTION)
  https://github.com/n8n-io/n8n
  page: https://mcpjunction.ai/servers/n8n-io--n8n
  install hint: npx n8n
  GitHub says: Fair-code workflow automation platform with native AI capabilities. Combine visual building with custom code, self-host or cloud, 400+ integrations.
-->
A whole platform, not a single server, and it speaks MCP in both directions: a
workflow can be published to agents as a set of tools through its MCP Server
Trigger, and a workflow can call other MCP servers through its MCP Client
node. That puts deterministic logic — with
human-approval steps where you want them — between an agent and your systems.
Expect to run the platform, self-hosted or in their cloud. Licensed fair-code,
not open source.

## ssut--remote-mcp

<!--
  ssut/Remote-MCP  ·  TypeScript  ·  MIT
  https://github.com/ssut/Remote-MCP
  page: https://mcpjunction.ai/servers/ssut--remote-mcp
  install hint: npx remote-mcp
  GitHub says: A type-safe solution to remote MCP communication, enabling effortless integration for centralized management of Model Context.
-->
Splits an MCP server in two: a thin local half your client talks to as usual,
and a remote half that holds the tools and data, joined over HTTP with typed
contracts between them. The point is sharing — one remote server serving
several machines or people instead of every laptop running its own copies. It
is plumbing, not a capability: you still bring the servers you want to expose,
and you now have a network hop to secure.

# AI Coding Assistants  (ai-coding)

## stickerdaniel--linkedin-mcp-server

<!--
  stickerdaniel/linkedin-mcp-server  ·  Python  ·  Apache-2.0
  https://github.com/stickerdaniel/linkedin-mcp-server
  page: https://mcpjunction.ai/servers/stickerdaniel--linkedin-mcp-server
  install hint: uvx linkedin-mcp-server
  GitHub says: Open-source MCP server for LinkedIn. Give Claude and any MCP-compatible AI agent access to profiles, companies, jobs, and messages.
-->
Reads LinkedIn by driving your own logged-in browser session rather than an
official API — which is why it works, and why it is fragile: pages change, and
LinkedIn actively discourages automation. It sees what your account sees, and
some tools act rather than read, such as sending connection requests, so scope
what the agent may do. An independent community project,
not affiliated with LinkedIn; a hosted commercial service sponsors it and is
offered as the managed alternative.

# Infrastructure & SDKs  (mcp-infrastructure)

## tbxark--mcp-proxy

<!--
  tbxark/mcp-proxy  ·  Go  ·  MIT
  https://github.com/tbxark/mcp-proxy
  page: https://mcpjunction.ai/servers/tbxark--mcp-proxy
  install hint: go install github.com/tbxark/mcp-proxy@latest
  GitHub says: An MCP proxy server that aggregates and serves multiple MCP resource servers through a single HTTP server.
-->
One endpoint in front of many servers: point a client at the proxy and it
presents the combined tools, prompts, and resources of everything configured
behind it, whichever transport each speaks — stdio, SSE, or streamable HTTP.
Useful when several people or machines should share one curated set, or when a
client only accepts one connection. It can also hold an OAuth token for a
downstream server once, so callers need not each authorise. Go binary; Docker
image available.

# Finance & Commerce  (finance)

## intuit--quickbooks-online-mcp-server

<!--
  intuit/quickbooks-online-mcp-server  ·  TypeScript  ·  Apache-2.0
  https://github.com/intuit/quickbooks-online-mcp-server
  page: https://mcpjunction.ai/servers/intuit--quickbooks-online-mcp-server
  install hint: npx quickbooks-online-mcp-server
  GitHub says: The QuickBooks MCP Server lets AI assistants access QuickBooks data via a standard interface. It uses the Model Context Protocol to expose QBO features as callable tools…
-->
Intuit's own server for QuickBooks Online: create, read, update, and search the
accounting entities, and pull the standard financial reports, from an agent.
Setup is the real work — register an app on Intuit's developer portal and
finish a browser OAuth handshake before anything runs, and production needs
a public HTTPS callback for that first step. After that it runs locally as a
stdio process. Because it can write to your books, decide deliberately which
tools the agent gets.

# Design Tools  (design-tools)

## southleft--figma-console-mcp

<!--
  southleft/figma-console-mcp  ·  TypeScript  ·  MIT
  https://github.com/southleft/figma-console-mcp
  page: https://mcpjunction.ai/servers/southleft--figma-console-mcp
  install hint: npx figma-console-mcp
  GitHub says: Your design system as an API. Connect AI to Figma for extraction, creation, and debugging.
-->
A two-way bridge between an agent and Figma: read a file's structure,
variables, and components; create and edit nodes; and sync design tokens in
both directions. It runs against Figma's cloud API or, for creation and
debugging, through a companion plugin inside the running desktop app — the two
modes have different capabilities, so check which one a task needs. Built for
teams that keep a design system in Figma and want code and design to stop
drifting apart.

# Cloud & DevOps  (cloud-devops)

## argoproj-labs--mcp-for-argocd

<!--
  argoproj-labs/mcp-for-argocd  ·  TypeScript  ·  Apache-2.0
  https://github.com/argoproj-labs/mcp-for-argocd
  page: https://mcpjunction.ai/servers/argoproj-labs--mcp-for-argocd
  install hint: npx mcp-for-argocd
  GitHub says: An implementation of Model Context Protocol (MCP) server for Argo CD.
-->
Operates your own Argo CD from an agent: list and inspect applications, read
resource trees, workload logs, and events, trigger syncs, run resource actions
— and create, update, and delete applications. That last group can change a
cluster, so scope the API token you give it. It lives under the Argo project's
labs organisation rather than the core project; treat it as adjacent to Argo
CD, not part of it. Speaks stdio locally and HTTP streaming remotely.
