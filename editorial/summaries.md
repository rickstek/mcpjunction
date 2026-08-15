# Editorial summaries

Human-written summaries, one per server. This file is the source of truth:
`scripts/pipeline.py` reads it on every nightly run and copies each entry into
the dataset's `editorial_summary` field. Automation only ever READS this file —
nothing writes into it. Deleting an entry here removes it from the site on the
next run.

## Format

One `##` heading per server, containing the server id exactly as it appears in
the URL (`owner--repo`, lowercase, double hyphen). Everything until the next
heading is the summary. Line breaks inside an entry are fine — they get folded
into one paragraph.

Only headings containing `--` are read as entries, which is why these
documentation headings are ignored. Copy the id from the server's URL:
`https://mcpjunction.ai/servers/microsoft--playwright-mcp` → `microsoft--playwright-mcp`.

    ## microsoft--playwright-mcp

    Two to four sentences of plain prose. No markdown formatting inside the
    entry — it renders as a single paragraph.

An id that matches no server prints a warning during the nightly run and is
skipped, so typos are visible rather than silent.

## House style

- 40–80 words. Say what it does, who it's for, and one thing that
  distinguishes it. A caveat is welcome when it's true and useful.
- Your own words. Never paraphrase the GitHub description — that text already
  appears on the page, attributed to the repo, and duplicating it defeats the
  purpose of writing these.
- No superlatives, no "best", no marketing voice. This directory's credibility
  is the product.
- No facts that go stale: no star counts, version numbers, or dates. The
  dataset already carries those and renders them live.
- Never imply endorsement or security review. The reviewed badge is set only
  by manual review, and this field must not read like one.

<!-- Entries begin below this line. Keep them alphabetical by id. -->
