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

Batch 1 — the ten largest categories. Approved and live (commit `4faa316`).

Batch 2 — the remaining twelve. Composition data was pulled BEFORE drafting
this time; audited; awaiting edit. One taxonomy note surfaced by the data, for
the human owner rather than for prose: `embedded` is the top match term in
`iot-hardware` and most of its hits are software ("embedded code search",
"embedded component framework"), not hardware. Narrowing it to
`embedded-systems` / `embedded-hardware` would clean that shelf without an
override.

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

## finance

Research and trading set the tone here rather than bookkeeping — servers that
read prices, run analysis, and manage positions, with the payments-and-ledgers
side a smaller presence. Anything that can place an order or move funds is a
different class of risk from anything that only reads, and an agent cannot tell
the difference unless the server enforces it. Almost none advertise a
paper-trading or read-only mode, so assume a server is live until you have
confirmed otherwise.

## storage

The bulk of this category handles documents rather than storage back ends:
reading and converting PDFs, spreadsheets, and office files so an agent can work
with their contents, with cloud-drive and object-storage connectors a smaller
group. A server that reads a format well does not necessarily write it back in
the same format, and a description that mentions reading does not promise
writing. Decide whether you need extraction or a round trip before assuming a
server does both.

## home-automation

A small category, and one hub accounts for much of it: several servers wrap the
same platform from different angles, alongside a few that speak to specific
device lines or network gear directly. With physical devices the question is not
read versus write but blast radius — a wrong instruction can unlock a door or
switch off the heating. Prefer servers that expose a narrow set of entities you
choose over ones that hand the agent everything the hub can see.

## iot-hardware

A thin and varied shelf: single-board computers and microcontrollers, IoT
devices, and robot middleware share it, with no single platform dominating. What
unites them is that an agent's command reaches a motor, a relay, or a radio with
no undo. Look for a simulation or dry-run mode before connecting anything that
moves, and keep hardware credentials on a device you are willing to have
misbehave while you learn how a server interprets instructions.

## gaming

Nearly everything here is a bridge into a game engine's editor, so an agent can
build scenes, edit scripts, and run the project rather than only discuss it.
These typically need a package installed inside the editor and kept in step
with the engine version, which is where they break: an engine upgrade can
silently strand the server. Check which releases a server actually tracks, and expect the
player-facing tools to be a much smaller group than the editor bridges.

## monitoring

Two kinds of observability meet here and are easy to confuse. One is
infrastructure monitoring — metrics, logs, and traces from running systems, read
by an agent for diagnosis. The other is observability of agents and models
themselves: tracing what an LLM pipeline did and why. A server built for one is
rarely useful for the other, and their descriptions often use the same words.
Decide which you are debugging first, then read past the label.

## productivity

The centre of gravity here is knowledge rather than task lists: notes, wikis,
documentation, and knowledge graphs an agent can read and extend, with
project-management and calendar connectors a smaller share. The useful
distinction is whether the knowledge lives in a tool's cloud or in files you
own — local-first notes are simpler to connect and leave no third party holding
your context. For anything that writes, check whether it appends or overwrites;
an agent tidying a wiki can erase more than it adds.

## ai-media

Media servers give an agent a way to produce or interpret images, speech, and
video rather than only text. The split that matters in practice is generation
versus recognition: turning a prompt into a picture or a voice, or turning audio
and images into text an agent can reason over. Generation nearly always means
either a paid API key or a GPU you run yourself, and which one a server assumes
is worth establishing before anything else.

## ai-models

These servers put a model provider behind the protocol so an agent can call
another model — for a second opinion, a cheaper draft, or a capability its own
model lacks. Much of the shelf is bridges to a single hosted provider, with a
scattering for local runtimes and other APIs. The thing to check is cost and
data handling: every call leaves your environment unless the server points at a
runtime on your own machine, and not every description says which.

## desktop-automation

These servers hand an agent the whole machine rather than one application:
keyboard and mouse, open applications, the clipboard, native scripting, and
control of phones and simulators. That reach is the point and the hazard — an
agent with the mouse can do anything you can, including things you would not.
Run these in a session or account you do not mind losing, and prefer servers
that expose named actions over raw pointer control.

## social-media

These servers read from and post to platforms where the platform, not you, sets
the rules. Reading a feed is usually safe; posting or messaging under an account
is where terms of service and rate limits bite, and several platforms actively
resist automation. A noticeable share of this shelf targets Chinese platforms,
where official APIs are scarce and servers often work through unofficial routes.
Check how a server authenticates — that tells you how long it is likely to keep
working.

## devtools

The sharpest tools in the directory live here: servers that run shell commands,
drive a terminal, or wrap a CLI so an agent can execute what you would type.
Beside them sit OpenAPI bridges that turn any documented HTTP service into
callable tools, and the inspectors and harnesses for building MCP servers
themselves. Scope anything that executes commands to a sandbox or a container
you can discard, and read exactly what a server passes to the shell before
trusting it.
