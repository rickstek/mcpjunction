# Topic intros

Human-written orientation for `/topics/<tag>`, one paragraph each. This file is
the DRAFTING surface: approved text is copied into the `intros` map in
`topics.json`, which is what the site renders (HTML and the `.md` variant).
Nothing here is live until it has been moved there.

Same working model as `category-intros.md`: Claude drafts in batches from the
composition data, a human edits, nothing publishes without approval.

## House style — what is different about topics

Topics are owner-applied GitHub tags, imported verbatim and not curated. The
page already says so in a fixed sentence directly above the intro. That changes
what an intro is for:

- **Explain what the tag SIGNALS and how to read it, not "what this shelf is
  for."** A category is a curated subject; a tag is a claim an owner made. Most
  of the largest tags are compatibility declarations (`claude-code`, `cursor`),
  implementation languages (`typescript`), or provider names (`openai`) — none
  of which describe what a server does. Say so, and point the reader at the
  category for that.
- **Never restate the page's fixed sentence** ("Servers whose GitHub repository
  topics include…", "imported verbatim", "does not assign or curate").
- **Derive the reading from co-occurrence and category spread**, then check it.
  Whether a tag travels alone or with others, and how many categories it spans,
  is what tells you what owners mean by it. Every such claim in this file was
  measured against the dataset before drafting.
- Otherwise as for categories: 60–90 words, own words, no superlatives, no
  digits or proportions (counts render live and drift nightly), never imply
  review or endorsement.

## Status

Batch 1 — the twelve largest tags. Approved and live (commit `606ebb9`).

Batch 3 — the next twelve. Readings measured before drafting: `sqlite` sits
in one category and only a minority are query servers — most use SQLite as the
storage under memory and knowledge tools (a categorisation side effect worth
the taxonomy owner's eye: the `sqlite` match term files memory servers under
Databases); `react`, `nextjs`, and `electron` name the framework a product's
interface is built in, not a subject (few are about building with them);
`windsurf` co-occurs with `cursor` in all but one server; `opencode` travels
alone least of any client tag; `langchain` is applied far more often than
descriptions mention it; `ollama` is named in few descriptions and usually
sits beside a cloud provider. Audited; awaiting edit.

Batch 2 — the next twelve. Nine specific claims were checked before drafting
and four were overturned: `skills` is rarely a curated list (a handful of many)
and mostly platforms that host or run skills; `docker` never means "controls
Docker" here — not one description does — only "ships as a container";
`chatgpt` is not a class of chat interface (few are) but behaves like `openai`;
and `knowledge-graph` and `semantic-search` are both majority CODE tools, not
document tools. Also measured: `agent-memory` has three storage backends with
none dominant; `golang` is undercounted because owners split between it and a
bare `go` tag that is not an approved topic; `local-first` and `self-hosted`
rarely co-occur, so the contrast between them is real. Audited; awaiting edit.

Corrections the data forced before drafting: `self-hosted` servers mention
Docker in only a minority, so no "expect Docker"; `rag` is applied across the
whole stack (indexers, stores, and the agents that query them), so no "needs an
index you build".

---

## claude

The broadest tag in the directory and the least specific. Owners apply it to
mean at least three different things — built for Claude Code or Claude Desktop,
calls the Claude API as one provider among several, or simply developed with
Claude's help — and the tag alone does not say which. Treat it as a hint that
Claude is somewhere in the picture, then read the description to find out
where, and check the category for what the server actually does.

## claude-code

This tag says a server has been used from, or built for, the Claude Code
harness — and more often than not it sits beside `codex` or `cursor` too,
because most MCP servers speak to any client and owners tag the ones they
tested. So the tag is evidence of compatibility, not of purpose: what the
server does is in its category. What is worth checking is whether the README
shows a Claude Code configuration, since that is the part that differs between
clients.

## typescript

Usually, though not always, the language the server is written in — and for an
MCP server that mostly matters for how it runs. A TypeScript server generally
means a Node runtime and an `npx`-style install, with the package registry as
the trust boundary. It says nothing about what the server does; servers tagged
this way span nearly every category. The practical question is whether you want
a Node process on the machine that runs your agent.

## python

Almost always the implementation language, and the practical consequence is
the runtime: a Python server wants an interpreter and an environment, typically
installed with `pip` or run with `uvx`. Python is also where much of the
retrieval and data-handling tooling lives, so this tag skews toward servers
that process documents and query stores rather than drive editors. Look at the
install hint for which package manager a server assumes.

## cursor

An owner tagging `cursor` is saying the server was tested with, or documented
for, the Cursor editor. In practice the tag rarely travels alone — the same
servers usually carry `claude-code` and often `windsurf` — because an MCP
server built for one IDE tends to work in the others with a different
configuration file. Read it as a compatibility note. What actually varies is
where the configuration lives and how the editor discovers the server.

## codex

Rarely tagged on its own: servers carrying `codex` almost always carry
`claude-code` too, and often `cursor`. That pattern reflects how owners tag —
they list the coding agents they tried — rather than anything Codex-specific
about the server. So the tag tells you the server has been run from OpenAI's
coding agent, not that it depends on it. Configuration is the part that differs
between agents; the server itself is usually the same.

## cli

Servers tagged `cli` overwhelmingly run as a local process on your own machine,
installed with a package manager and spoken to over standard input rather than
a network. That is the useful reading: the tag is about form factor, not
subject, and it spans nearly every category. A local process has your user's
permissions and filesystem, which is convenient and is also the risk — it is
worth knowing what a CLI server can reach before an agent drives it.

## openai

Most servers carrying this tag also carry another provider's — `claude`,
`gemini`, `deepseek` — which means the tag usually marks a server that can use
OpenAI's models among others, not a dedicated bridge to them. A server tagged
with a single provider is a different thing: a connector to that API
specifically. Decide which you want, then check whether a key is required at
all — many multi-provider servers work with whichever one you configure.

## anthropic

In practice this tag and `claude` travel together and mean much the same thing,
and most servers carrying it also name another provider. Read it as `openai` is
read: usually a server that can route to Anthropic's models rather than one
built only for them. Where the two tags differ in intent, `anthropic` leans
toward the API and `claude` toward the products — but owners do not apply that
distinction consistently, so the description settles it.

## rag

Retrieval-augmented generation covers a whole stack, and this tag is applied
across it: indexers that build a searchable store from your documents, the
stores themselves, and the agents and interfaces that query them at answer
time. A server tagged `rag` might be any of the three. The question to ask
first is whether it expects you to bring an existing index or builds one — that
determines the setup cost, and it is not something the tag tells you.

## self-hosted

A claim by the owner about where the software runs: on infrastructure you
control, with your data staying there. It spans most categories, from databases
to chat, and how you actually run it varies a great deal — some are a single
binary, others a stack of services. Two things the tag does not tell you:
whether the MCP server piece is itself self-hosted or a thin client to something
remote, and what the server phones home to. Check both.

## gemini

Mostly a provider tag, and mostly not alone — servers carrying `gemini` usually
carry `claude` or `openai` too, marking a server that can use Google's models
among others. A minority are dedicated Gemini bridges. A related but distinct
tag, `gemini-cli`, is a compatibility claim like `claude-code` — servers used
from Google's terminal agent, not servers that call its API. If you
specifically want Gemini, look for the model named in the description rather
than trusting the tag.

## local-first

A claim about where your data lives: on the machine running the agent, in
files or a local store, with no account and often no network needed. It is not
the same claim as `self-hosted` — that means you run a server; this means there
is no server. The tag clusters with memory and note-taking tools, which is
where it matters most: an agent's accumulated context is exactly the kind of
thing you may not want on someone else's infrastructure.

## skills

Marks servers built around the skills convention — packaged instructions and
tools an agent loads on demand — and it spans most categories because skills
are a way of shipping capability, not a kind of capability. The distinction to
make is whether a server provides skills for an agent to use, or is a platform
that hosts and runs them. The tag travels most often with `claude-code`, but is
not specific to it.

## rust

Usually the implementation language, and the consequence for you is a single
compiled binary: no interpreter, no runtime to install, typically fetched with
`cargo` or as a prebuilt release. That also means these servers tend to be fast
to start and light to run, which matters for a local process an agent spawns
often. A share of them are desktop applications with an MCP server inside
rather than standalone servers — check which you are getting.

## openclaw

A compatibility declaration for another agent runtime, one that owners list
alongside `claude-code` and `codex` in the same breath — and the tag often
appears with one of those. Read it the way you would read them: the server has
been run from this runtime, not built for it or dependent on it. What the
server does is in its category; what differs between runtimes is the
configuration that connects them.

## chatgpt

A product name attached to servers, not a description of them. Few of these are
chat interfaces or clones; the tag mostly appears on tools that list every
model family they can talk to, and it travels with `claude` and `gemini` far
more than it travels alone. So it tells you OpenAI's models are supported, not
that they are preferred or required. For the API-level question — is this
server built for one provider or does it route to many — the `openai` page is
the one to read.

## docker

Owners use this tag to say the server ships as a container, or runs alongside
a self-hosted service that does — not that it controls Docker. It clusters with
`self-hosted` and `kubernetes` and sits mostly on the infrastructure and
database shelves. A container is usually one option rather than the only one,
and these servers typically also install as an ordinary local process. Choose
the container
when the server has service dependencies you would rather not set up by hand.

## golang

The implementation language, and the practical result is a single static
binary that runs anywhere without a runtime — the lightest kind of local
process an agent can spawn. Two things to know: owners split between this tag
and a plain `go` tag, so this page undercounts Go servers; and Go is common in
infrastructure and database tooling, which is where many of these sit. Fetch
with `go install` or a release binary.

## agent-memory

A genuine subject: persistent memory an agent carries between sessions, so it
stops forgetting what it learned yesterday. What "memory" is built on varies
more than the tag suggests — vector stores, knowledge graphs, and plain files
on disk are all represented, with no single approach dominant — and that choice
decides everything about portability and cost. The tag sits in a cluster with
`rag`, `knowledge-graph`, and `semantic-search`; a server often carries more
than one.

## deepseek

Almost never alone: servers carrying `deepseek` nearly always carry `openai`,
`claude`, or `gemini` as well, which marks a provider-agnostic server that can
route to DeepSeek's models among others. Read it as a signal that a server
supports open-weight model options, not as a dedicated integration. The single-provider case is rare here; when you find one, it is
the bridge, and everything else is a router.

## knowledge-graph

The name suggests notes and documents, but most servers carrying this tag build
graphs of code — functions, files, and their relationships — for agents that
need to understand a repository rather than a wiki. The rest are knowledge and
note graphs in the older sense. Both kinds cluster with `agent-memory`, `rag`,
and `semantic-search`. Check which kind a server is before assuming it will map
your documents; the tag alone will not tell you.

## macos

Some servers tagged `macos` are genuinely Mac-specific — written in Swift,
driving AppleScript or native frameworks — and others list macOS as one of
several platforms they run on; the tag does not separate the two. The reading
that helps: check whether `windows` or `linux` appears beside it. If they do,
this is a portability note. If `macos` stands alone, expect Mac-only automation,
with the reach into your desktop that implies.

## semantic-search

Search by meaning rather than by keyword, which needs an embedding model —
either one running locally or an API you pay per call — and that dependency is
the first thing to establish. As with `knowledge-graph`, most servers here point
it at code rather than prose: finding the function that does a thing across a
repository. It sits in the same cluster as `rag` and `agent-memory`, and a
server tagged with one often carries another.

## claude-desktop

The compatibility declaration for Anthropic's desktop app rather than its
coding harness, which shifts the audience: a chat window reached by people who
may never open a terminal. A server tagged this way is one its owner expects to
be configured by hand in a local settings file and used conversationally. It
travels with `claude-code` and `cursor` often enough that the tag is rarely
exclusive; what it does tell you is that the server has run in the plainest
local setup there is.

## nodejs

Almost the same servers as `typescript`, seen from the runtime side: the tag
says a Node process is what runs, whichever language it was written in. That is
the practical fact — you need Node installed on the machine your agent uses,
and installs come through the package registry. Where the two tags differ is
intent: `typescript` describes how a server was written, `nodejs` what it needs
to run, and most owners apply both without meaning a distinction.

## opencode

Of all the client tags, this one travels alone least: nearly every server
carrying it also carries `claude-code`, and most carry `codex` as well. So it
is not a signal that a server targets this runtime — it is one entry in a list
of the coding agents an owner has run it from. Read the list, not the tag. If a
server truly depended on one client, its owner would have had no reason to name
three.

## react

Not a tag about React development. It marks projects whose own interface is
built in React — database clients, knowledge bases, desktop workspaces — with
an MCP server exposed alongside. So the tag tells you about the product's front
end, not the server's function, and the two can be far apart. If you are
looking for a server that helps you build React applications, this tag will
mostly disappoint; the category pages are a better route to that.

## sqlite

Nearly all of these land in the Databases category, yet only a minority are
servers for querying a SQLite database. Most use SQLite as the storage
underneath something else — an agent's memory, a knowledge store, a local
index — because it is a single file, needs no service, and travels with the
project. Read the tag as "keeps its state in a local file" first, and as "lets
you query your database" only when the description says so.

## copilot

A compatibility note for GitHub's assistant in VS Code, and one that almost
never stands alone — it appears beside `cursor` more often than not, and often
beside `claude-code` too. That pattern says owners are listing the editors they
tested rather than describing a Copilot-specific server. The one place the tag
carries extra meaning is game development, where several engine bridges name it
because the engine's own editor integrates with it. Elsewhere, treat it as one
item in a compatibility list.

## ollama

A runtime you host rather than a vendor you pay, which makes this the tag to
look for when you want an agent's model calls to stay on your own hardware. But
do not assume local-only: many of the servers carrying it also list a cloud
provider, and Ollama is one option among several. Often the tag is the only
evidence — the description never names it — so check the configuration for how
a model endpoint is chosen before relying on the local path.

## electron

The framework, not the function: servers tagged `electron` live inside a
desktop application built with it — a workspace, a terminal, a knowledge tool —
and the MCP server is a feature of that app rather than a standalone process.
Expect to install and open the application, and expect it to keep running while
the agent uses it. The tag overlaps with `desktop-app`; the difference is that
this one also tells you the app carries a bundled browser engine and the
footprint that implies.

## windsurf

In this directory the tag is almost inseparable from `cursor`: virtually every
server tagged for one editor is tagged for the other, and fewer of their
descriptions mention either than the tags suggest. That makes it a paired
declaration — works in the two Cursor-style editors — rather than a signal
about Windsurf specifically. What differs between them is configuration
location and discovery, not the server. If you use Windsurf, read the `cursor`
guidance and expect the same setup shape.

## nextjs

Owners tag the framework their web layer is built on, and Next.js is a common
one for platforms that ship a hosted interface — agent builders, knowledge
tools, dashboards — with an MCP server as part of the package. So the tag
describes the product's web tier, not what the server does, and it can mark a
whole self-hostable platform rather than a small server you add to a client.
Weigh the footprint accordingly: you may be deploying an application to get a
tool.

## langchain

An ecosystem-membership tag more than a description: a project built with or
alongside LangChain and LangGraph, applied by owners far more often than their
descriptions mention either name. Servers here skew toward agent frameworks,
retrieval pipelines, and observability for them, plus a scattering of learning
material. The tag does not mean a server requires LangChain to use — many are
ordinary MCP servers whose authors work in that ecosystem. Check whether it
exposes tools or expects you to be inside a LangGraph graph.

## desktop-app

A form-factor tag: the MCP server ships inside a desktop application you install
and open, most often a workspace for driving coding agents or an assistant
client. That has two consequences. The app must be running for the server to
answer, and the server inherits whatever the app can reach on your machine.
Sibling tags `electron` and `tauri` tell you what the app is built with; this
one tells you only that there is an app. Prefer ones that let you scope what
the agent can touch.
