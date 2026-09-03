# Category intros

Human-written orientation for `/categories/<slug>`, one paragraph each. This
file is the DRAFTING surface: approved text is copied into the `intro` field of
the matching category in `categories.json`, which is what the site actually
renders. Nothing here is live until it has been moved there.

Same working model as `summaries.md`: Claude drafts in batches, a human edits,
nothing publishes without approval.

## House style

- 60–90 words. Orient the reader, give them one distinction that helps them
  choose, and add a caveat where one is honestly true.
- Your own words. Never restate the category `description` — it renders
  directly above the intro on the same page.
- No superlatives, no marketing voice. The directory's credibility is the
  product.
- No facts that go stale: no server counts, star counts, version numbers, or
  dates. Those render live from the dataset. That includes proportions — "half
  of these" drifts with every nightly.
- Never imply endorsement or security review. Listing is not vetting. Phrase
  this as a permanent truth ("listing here is not a review"), not a current
  state ("nothing here has been reviewed"), so it stays true after the first
  server is.
- Write about what the category is FOR. Membership is keyword-assigned and
  imperfect, so an intro must not claim every entry below it is a clean fit.
- Every claim about what the members do or need must be checked against the
  dataset before it ships. Batch 1 was audited this way and nine of ten drafts
  needed correction: two restated the description they sit under, and four
  asserted a distinction as central when the data showed it in a small
  minority of entries. Where the data undercuts a claim, the correction is
  usually to turn the finding itself into the caveat ("few descriptions say
  whether a server can write") rather than to drop the point.

## Status

Batch 1 — the ten largest categories. Drafted, audited against the dataset,
corrected. Awaiting edit.

---

## browser-automation

Browser automation servers let an agent act on pages a plain HTTP fetch cannot
reach — anything behind a login, rendered by JavaScript, or gated by a click.
The distinction worth checking when choosing: some drive a full browser engine,
which is heavier but survives dynamic pages, while others fetch and parse HTML
directly and cost far less per page. Sites that fingerprint automated traffic
will defeat a naive setup, so look at how a server handles detection before
committing.

## ai-coding

These servers sit alongside a coding assistant rather than replacing it,
extending what it can reach from inside the editor or terminal. Many advertise
support for several assistants; others are written against exactly one. So the
first thing to check is whether a server actually speaks to the client you use —
one built for a single harness often needs a configuration shim before another
will load it, and that detail rarely makes it into the description.

## databases

Database servers let an agent inspect a schema and run queries without a person
pasting results into a chat window. Before connecting one to anything real,
find out whether it can write as well as read — few descriptions say, and the
difference is the difference between a useful assistant and an unreviewed
migration. Check what the connection itself grants and take into consideration: a server inherits
whatever its credentials carry, which is easy to over-scope by accident.

## search

Retrieval servers answer what a model cannot answer from its own weights. Most
here are retrieval over a corpus you supply — RAG pipelines and semantic search
that need an index you build and keep current. A smaller set wrap a commercial
web-search API and need a key. The cost profiles differ sharply: one spends disk
and setup time before it answers anything, the other bills per query and knows
nothing about your documents.

## ai-agents

Servers here deal in scaffolding rather than a single capability: orchestration,
memory that outlives a session, planning loops, and coordination between several
agents. Many are frameworks first and MCP servers second, so it is worth reading
what a project actually exposes over the protocol before assuming its headline
features are reachable from your client. The gap between what a framework does
and what it serves over MCP can be wide.

## security

Security servers hand an agent tooling built for people who already knew what
they were doing: scanners, secret stores, reverse-engineering suites, identity
providers. That combination deserves care, because an agent driving a scanner
generates real traffic against real hosts. Being listed here is not a security
review. Look at what a server is permitted to reach before connecting it, and
prefer ones that state their scope rather than inheriting your whole
environment.

## communication

These servers connect an agent to the places people actually talk — chat
platforms, email, and messaging APIs. Two things decide whether one fits:
whether it can send as well as read, and how it authenticates. The platforms
behind them almost all require an OAuth grant or a bot token scoped to a
workspace you control, whatever the server's own description says. Read access
is the safer place to start. Anything that can post is acting under your name.

## cloud-devops

The question to ask of any server here is whether it only reads state —
listing resources, pulling logs, describing a cluster — or can also change it.
Read-only access is genuinely useful for diagnosis and costs little when an
agent misunderstands. Anything that can apply a plan, scale a deployment, or
restart a service belongs behind a role whose limits you set deliberately,
because an agent will do exactly what it was told and not what you meant.

## mcp-infrastructure

Come here to build or operate MCP itself rather than to add a capability to an
agent. If you are writing a server, start with an official SDK; if you run many
servers, a gateway or proxy puts one endpoint in front of them. The
specification is still moving and the official SDKs follow it closely — so a
gateway or client pinned to an older version can quietly drop capabilities a
newer server advertises.

## design-tools

Three kinds of server share this category: integrations that drive a design or
modelling application, generators that produce diagrams and charts from text,
and bridges into UI component libraries. The practical question for the first
kind is whether it talks to a cloud API or to software on your machine — the
latter usually means installing a plugin and leaving the app open. Reading a
document's structure is common; producing finished artwork faithfully is not.
