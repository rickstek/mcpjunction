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

Batch 1 — the twelve largest tags. Drafted from measured co-occurrence and
category spread; audited; awaiting edit.

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
