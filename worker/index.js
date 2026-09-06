/**
 * mcpjunction.ai Worker
 *
 * Two jobs:
 *   1. /mcp — a Model Context Protocol server exposing the directory as
 *      queryable tools (streamable HTTP transport, stateless mode).
 *   2. Everything else — falls through to the static assets binding, which
 *      preserves html_handling and the 404 page exactly as before this
 *      Worker existed.
 *
 * Design constraints (deliberate):
 *   - Zero npm dependencies. The whole MCP surface is small JSON-RPC; an SDK
 *     would add supply-chain risk to a Worker that fronts the entire domain.
 *   - Stateless: no session ids, no SSE stream. Each POST is a complete
 *     JSON-RPC exchange. Clients that want the directory get answers in one
 *     round trip — cheapest possible shape for metered agent fetchers.
 *   - Read-only over the SAME dataset the site is built from. No divergent
 *     "API view" of the data; /data/mcp_servers.json stays the single source
 *     of truth (Standing Rule: pages and tools render the dataset, never
 *     derive editorial content).
 */

const PROTOCOL_VERSION = "2025-06-18";
const SERVER_INFO = { name: "mcpjunction", version: "1.0.0" };
const ATTRIBUTION = "via mcpjunction.ai";
const LICENSE_URL = "https://mcpjunction.ai/licensing";

// Every surface that shows an install hint shows this beside it — the server
// page, the markdown variant, the dataset docs. The tool payload used to ship
// the command alone, so an agent asked "how do I install X" would relay a
// runnable command stripped of the one warning the HTML deems necessary.
// Wording tracks src/pages/servers/[id].astro; keep them in step.
const INSTALL_HINT_CAVEAT =
  "Best-effort hint inferred from the repository language, not a verified install " +
  "command. It never includes auto-confirm flags (-y, --yes): the package registry " +
  "name may be squatted by someone other than the repository owner. Check the " +
  "repository's own README before running it.";

// In-isolate dataset cache. Isolates persist across requests; the dataset
// changes once per day, so a short TTL keeps memory fresh without hitting
// the assets binding on every call.
//
// The cache holds the in-flight PROMISE, not the resolved value. Storing the
// value means that when the TTL expires under load, every concurrent request
// in the isolate independently fetches and parses the same 2.3 MB document —
// enough simultaneous misses to push the isolate toward its memory ceiling and
// take unrelated in-flight requests down with it. Sharing the promise collapses
// that to one fetch.
const DATASET_TTL_MS = 10 * 60 * 1000;
let datasetCache = { promise: null, data: null, fetchedAt: 0 };

/**
 * Attach a precomputed lowercase search haystack to each entry.
 *
 * Built once per dataset load rather than per request: search previously
 * rebuilt and lowercased a string for all ~1,800 entries on every single call,
 * which cost ~2.3 ms of CPU even for a one-word query.
 *
 * `_topics` exists for the same reason. The topic filter is an EXACT match, so
 * it cannot read `_hay` — that string also contains the description, and
 * `_hay.includes("claude")` is true for any server merely mentioning Claude.
 * GitHub normalizes topics to lowercase, but they are third-party strings
 * imported verbatim, so normalize rather than trust.
 */
function indexDataset(data) {
  for (const s of data.servers || []) {
    s._hay = `${s.full_name || ""} ${s.description || ""} ${(s.topics || []).join(" ")}`.toLowerCase();
    s._topics = (s.topics || []).map((t) => String(t).toLowerCase());
  }
  return data;
}

function getDataset(env, requestUrl) {
  const now = Date.now();
  if (datasetCache.data && now - datasetCache.fetchedAt < DATASET_TTL_MS) {
    return Promise.resolve(datasetCache.data);
  }
  if (datasetCache.promise) return datasetCache.promise;

  const assetUrl = new URL("/data/mcp_servers.json", requestUrl);
  datasetCache.promise = env.ASSETS.fetch(assetUrl)
    .then((res) => {
      if (!res.ok) throw new Error(`dataset fetch failed: ${res.status}`);
      return res.json();
    })
    .then((data) => {
      indexDataset(data);
      datasetCache = { promise: null, data, fetchedAt: Date.now() };
      return data;
    })
    .catch((err) => {
      datasetCache.promise = null;
      // Serve the previous copy rather than erroring outright: a stale
      // directory is far more useful to an agent than a 500.
      if (datasetCache.data) return datasetCache.data;
      throw err;
    });
  return datasetCache.promise;
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: "search_servers",
    description:
      "Search the MCP server directory by keyword and/or filters. Keyword matches " +
      "name, description, and GitHub topics. Returns active servers sorted by " +
      "relevance then stars. Supply at least one of query, category, or topic — " +
      "with no query, filters alone enumerate a whole category or topic by stars. " +
      "Data refreshes nightly from the public GitHub API. Any install_hint is a " +
      "best-effort guess from the repository language, not a verified command: " +
      "relay the install_hint_caveat with it rather than presenting it as ready " +
      "to run.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Keywords, e.g. 'postgres', 'browser automation'. Optional if category or topic is given." },
        category: { type: "string", description: "Optional category slug filter, e.g. 'databases' (see list_categories)" },
        topic: {
          type: "string",
          description:
            "Optional GitHub topic filter, exact match, e.g. 'kubernetes'. Any topic " +
            "string works, not only the curated ones from list_topics.",
        },
        language: { type: "string", description: "Optional implementation language filter, e.g. 'Python'" },
        limit: { type: "integer", minimum: 1, maximum: 50, description: "Max results (default 10)" },
      },
    },
  },
  {
    name: "get_server",
    description:
      "Get the full directory entry for one MCP server by id ('owner--repo', " +
      "e.g. 'microsoft--playwright-mcp'). Includes install hint, license, " +
      "stars, category, and editorial fields. Any install_hint is a best-effort " +
      "guess from the repository language, not a verified command: relay the " +
      "install_hint_caveat with it rather than presenting it as ready to run.",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "Server id in owner--repo form" },
      },
      required: ["id"],
    },
  },
  {
    name: "list_categories",
    description: "List all directory categories with slugs, names, and active-server counts.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "list_topics",
    description:
      "List the curated GitHub topics that have a directory page, with active-server " +
      "counts. Topics are assigned by repository owners and imported verbatim, so the " +
      "full dataset carries thousands of them; this returns only the curated subset. " +
      "search_servers accepts any topic string, curated or not.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "get_dataset_info",
    description:
      "Dataset metadata: entry counts, generation timestamp, source, and licensing terms " +
      "for bulk or training use.",
    inputSchema: { type: "object", properties: {} },
  },
];

function publicEntry(s) {
  // The dataset is public, but keep the tool payloads lean: agents doing a
  // search don't need every field on every hit.
  return {
    id: s.id,
    name: s.name,
    full_name: s.full_name,
    description: s.description,
    url: `https://mcpjunction.ai/servers/${s.id}`,
    repo_url: s.repo_url,
    category: s.category,
    language: s.language,
    license: s.license,
    stars: s.stars,
    install_hint: s.install_hint,
    security_reviewed: s.security_reviewed,
    status: s.status,
  };
}

// Search cost is O(#terms x #servers). Without these caps a single request can
// buy an unbounded amount of Worker CPU: 20,000 terms in a 176 KB body measured
// at ~1.7 s, and the endpoint is unauthenticated with CORS "*", so any web page
// could drive it from its visitors' browsers. Bounding the input is the fix that
// belongs in code, and these two caps are the part this file actually
// guarantees.
//
// Request FLOODS are handled at the edge, not here. Verified in the Cloudflare
// dashboard on 2026-09-06: a rate limiting rule named "MCP endpoint flood
// protection", expression
// `(http.request.uri.path eq "/mcp" or http.request.uri.path eq "/mcp/")`,
// counting per IP, 100 requests / 10 seconds, action Block, active. It runs
// ahead of this Worker, so blocked requests never become invocations.
//
// Three things about it that this file cannot tell you, in order of how much
// they matter:
//
//   - The threshold stops hammering, NOT quota exhaustion. 100 per 10s is
//     10 req/s sustained, which is 864,000 requests/day from a single IP that
//     never trips the rule — 8.6x the free plan's 100,000/day Worker limit,
//     exhausting it in under three hours. For scale, real /mcp traffic is
//     ~1,780/day total (0.02 req/s), the busiest single source IP is 550/day,
//     and the nightly workflow's own /mcp check is 2 requests. The count is
//     the only lever: the free plan locks Period to 10 seconds, so lengthening
//     the window to trade burst tolerance for a lower sustained ceiling is not
//     available. DECIDED 2026-09-06: lower it to 20/10s, a 172,800/day ceiling
//     (1.7x) that still allows an agent 20 calls in ten seconds — faster than
//     any real MCP session. 10/10s is the only setting under the quota and is
//     tight enough to risk blocking a legitimate burst. The decision is
//     recorded in scripts/verify_edge_rules.py, which reports the live rule as
//     looser than accepted until the dashboard change is actually made.
//   - It exists only in the dashboard. Nothing in this repository creates it,
//     and no gate in the nightly workflow proves it is still there — unlike
//     robots.txt, crawler allow/block and markdown negotiation, which are all
//     asserted against production on every run. It can be deleted or disabled
//     and nothing here would notice.
//   - It covers /mcp alone, while wrangler.jsonc sends /servers/*,
//     /categories/* and /topics/* through run_worker_first too. Those invoke
//     this Worker on every request and are not rate limited, so they reach the
//     same quota. Deliberate: this site exists to be crawled hard by search and
//     agent fetchers, and limiting /servers/* would risk the thing the whole
//     strategy depends on. The zone is on the free plan, which allows exactly
//     one rate limiting rule, so this is a choice between paths, not an
//     omission.
const MAX_QUERY_CHARS = 256;
const MAX_TERMS = 8;

function toolSearchServers(dataset, args) {
  const raw = String(args.query || "").trim();

  const category = args.category ? String(args.category).toLowerCase().trim() : null;
  const topic = args.topic ? String(args.topic).toLowerCase().trim() : null;
  const language = args.language ? String(args.language).toLowerCase().trim() : null;
  const limit = Math.min(Math.max(parseInt(args.limit, 10) || 10, 1), 50);

  // A filter alone is a legitimate search ("every server tagged kubernetes"),
  // so `query` is no longer unconditionally required — but an empty call is
  // still an error rather than a dump of the whole directory.
  if (!raw && !category && !topic) {
    return { error: "supply at least one of: query, category, topic" };
  }

  const truncated = raw.length > MAX_QUERY_CHARS;
  const query = raw.slice(0, MAX_QUERY_CHARS).toLowerCase();
  const allTerms = query.split(/\s+/).filter(Boolean);
  const terms = allTerms.slice(0, MAX_TERMS);

  const scored = [];
  for (const s of dataset.servers) {
    if (s.status !== "active") continue;
    if (category && s.category !== category) continue;
    if (language && String(s.language || "").toLowerCase() !== language) continue;
    // Exact membership, matching how /topics/<tag> pages are built: topics
    // report what owners tagged, they don't interpret it.
    if (topic && !(s._topics || []).includes(topic)) continue;
    let score = 0;
    if (terms.length) {
      const hay = s._hay || "";
      for (const t of terms) if (hay.includes(t)) score += 1;
      if (score === 0) continue;
    }
    scored.push([score, s.stars || 0, s]);
  }
  // With no keyword every hit scores 0 and this collapses to a stars sort,
  // which is the right ranking for "show me everything in this topic".
  scored.sort((a, b) => b[0] - a[0] || b[1] - a[1]);

  const out = {
    query: raw ? raw.slice(0, MAX_QUERY_CHARS) : null,
    filters: { category, topic, language },
    total_matches: scored.length,
    returned: Math.min(limit, scored.length),
    results: scored.slice(0, limit).map(([, , s]) => publicEntry(s)),
    attribution: ATTRIBUTION,
  };
  // Once per response, not once per entry: a 50-result search would otherwise
  // repeat ~240 characters fifty times for a caveat that is identical each
  // time. Emitted only when a returned entry actually carries a hint.
  if (out.results.some((r) => r.install_hint)) {
    out.install_hint_caveat = INSTALL_HINT_CAVEAT;
  }
  // Say so rather than silently returning results for a different query than
  // the one asked — an agent needs to know its input was clipped.
  if (truncated || allTerms.length > terms.length) {
    out.notice =
      `Query was truncated to ${MAX_QUERY_CHARS} characters and ${MAX_TERMS} terms. ` +
      `Searched: ${terms.join(" ")}`;
  }
  // An unknown topic and a topic with no active members are indistinguishable
  // in the result shape (both empty), so name the likely cause.
  if (topic && scored.length === 0) {
    out.notice =
      `No active servers carry the topic '${topic}'. Topics are exact matches on ` +
      `owner-assigned GitHub tags; call list_topics for the curated ones.`;
  }
  return out;
}

function toolGetServer(dataset, args) {
  const id = String(args.id || "").toLowerCase().trim();
  const s = dataset.servers.find((e) => e.id === id);
  if (!s) {
    return { error: `no server with id '${id}'`, hint: "ids are owner--repo, lowercase; try search_servers" };
  }
  const entry = { ...publicEntry(s), topics: s.topics, forks: s.forks, open_issues: s.open_issues, pushed_at: s.pushed_at, homepage: s.homepage, attribution: ATTRIBUTION };
  if (entry.install_hint) entry.install_hint_caveat = INSTALL_HINT_CAVEAT;
  return entry;
}

function toolListCategories(dataset) {
  return {
    categories: Object.entries(dataset.categories || {}).map(([slug, count]) => ({
      slug,
      count,
      url: `https://mcpjunction.ai/categories/${slug}`,
    })),
    attribution: ATTRIBUTION,
  };
}

function toolListTopics(dataset) {
  // Absent only on a dataset generated before the pipeline learned to emit the
  // aggregate. Degrade with an explanation rather than an empty list, which
  // would read as "this directory has no topics".
  if (!dataset.topics) {
    return {
      error: "topic index unavailable",
      hint:
        "This dataset predates the topics aggregate; it appears after the next " +
        "nightly refresh. search_servers already accepts a topic filter.",
    };
  }
  return {
    topics: Object.entries(dataset.topics).map(([slug, count]) => ({
      slug,
      count,
      url: `https://mcpjunction.ai/topics/${slug}`,
    })),
    note:
      "Curated subset only — these are the topics with a directory page. Topics " +
      "are owner-assigned GitHub tags imported verbatim, and search_servers " +
      "accepts any topic string, listed here or not.",
    attribution: ATTRIBUTION,
  };
}

function toolGetDatasetInfo(dataset) {
  return {
    dataset: dataset.dataset,
    generated_at: dataset.generated_at,
    active_servers: dataset.count,
    total_including_delisted: dataset.count_including_delisted,
    source: dataset.source,
    data_url: dataset.url,
    license: LICENSE_URL,
    terms:
      "Agent/inference-time retrieval is free during launch with attribution " +
      `('${ATTRIBUTION}'). Bulk retrieval and AI training require a license: ${LICENSE_URL}`,
  };
}

// ---------------------------------------------------------------------------
// JSON-RPC plumbing
// ---------------------------------------------------------------------------

// 64 KB. The largest legitimate request this API receives is a tools/call with
// a short query; anything approaching this is either broken or hostile.
const MAX_BODY_BYTES = 64 * 1024;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept, MCP-Protocol-Version, Mcp-Session-Id",
  "Access-Control-Max-Age": "86400",
};

function rpcResult(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function rpcError(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

// public/_headers applies the site's security headers to everything the ASSET
// server returns — but /mcp is answered by this Worker, which builds its
// headers from scratch, so none of them were reaching it. nosniff is the one
// that matters here: this endpoint returns attacker-influenced repository text
// as application/json, with CORS "*", to any origin that asks. A browser that
// content-sniffs a JSON body into HTML is the whole reason that header exists.
// The rest mirror _headers so the two surfaces do not drift.
const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
  "X-Frame-Options": "DENY",
};

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...SECURITY_HEADERS,
      ...CORS_HEADERS,
    },
  });
}

async function handleMcp(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }
  if (request.method !== "POST") {
    // Stateless server: no SSE stream to GET. 405 per spec.
    return jsonResponse(rpcError(null, -32600, "Method not allowed; POST JSON-RPC messages to this endpoint"), 405);
  }

  // Refuse oversized bodies before buffering them. Every legitimate call to
  // this API is well under a kilobyte; Cloudflare would otherwise happily
  // buffer up to 100 MB for us to parse.
  const declaredLength = parseInt(request.headers.get("Content-Length") || "0", 10);
  if (declaredLength > MAX_BODY_BYTES) {
    return jsonResponse(
      rpcError(null, -32600, `Request body too large (max ${MAX_BODY_BYTES} bytes)`),
      413
    );
  }

  let msg;
  try {
    // Content-Length can be absent (chunked). Read the body ourselves so an
    // unheadered stream cannot slip past the check above.
    const body = await request.text();
    if (body.length > MAX_BODY_BYTES) {
      return jsonResponse(
        rpcError(null, -32600, `Request body too large (max ${MAX_BODY_BYTES} bytes)`),
        413
      );
    }
    msg = JSON.parse(body);
  } catch {
    return jsonResponse(rpcError(null, -32700, "Parse error"), 400);
  }
  if (Array.isArray(msg)) {
    // JSON-RPC batching was removed in protocol 2025-06-18.
    return jsonResponse(rpcError(null, -32600, "Batching is not supported"), 400);
  }

  const { id, method, params } = msg || {};

  // Notifications (no id) get a 202 with no body.
  if (id === undefined || id === null) {
    return new Response(null, { status: 202, headers: CORS_HEADERS });
  }

  try {
    switch (method) {
      case "initialize":
        return jsonResponse(
          rpcResult(id, {
            protocolVersion: PROTOCOL_VERSION,
            capabilities: { tools: { listChanged: false } },
            serverInfo: SERVER_INFO,
            instructions:
              "Queryable index of the mcpjunction.ai MCP server directory. " +
              "Use search_servers to find servers, get_server for one entry, " +
              "list_categories and list_topics to browse. Categories are a " +
              "curated single-assignment taxonomy; topics are owner-assigned " +
              "GitHub tags, many per server. Data refreshes nightly. " +
              `Attribution: ${ATTRIBUTION}.`,
          })
        );
      case "ping":
        return jsonResponse(rpcResult(id, {}));
      case "tools/list":
        return jsonResponse(rpcResult(id, { tools: TOOLS }));
      case "tools/call": {
        const name = params?.name;
        const args = params?.arguments || {};
        const dataset = await getDataset(env, request.url);
        let payload;
        if (name === "search_servers") payload = toolSearchServers(dataset, args);
        else if (name === "get_server") payload = toolGetServer(dataset, args);
        else if (name === "list_categories") payload = toolListCategories(dataset);
        else if (name === "list_topics") payload = toolListTopics(dataset);
        else if (name === "get_dataset_info") payload = toolGetDatasetInfo(dataset);
        else return jsonResponse(rpcError(id, -32602, `Unknown tool: ${name}`));
        return jsonResponse(
          rpcResult(id, {
            content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
            structuredContent: payload,
            isError: Boolean(payload && payload.error),
          })
        );
      }
      default:
        return jsonResponse(rpcError(id, -32601, `Method not found: ${method}`));
    }
  } catch (e) {
    // Log the detail, return a generic message: the raw text leaks internal
    // shape ("dataset fetch failed: 503", stack-derived property names) to any
    // unauthenticated caller.
    console.error("mcp handler error:", e && e.stack ? e.stack : e);
    return jsonResponse(rpcError(id, -32603, "Internal error"), 500);
  }
}

// ---------------------------------------------------------------------------
// Markdown content negotiation
// ---------------------------------------------------------------------------

/**
 * True only when the client EXPLICITLY asks for markdown. Browsers send
 * "text/html,...,*\/*" — matching the wildcard would serve markdown to
 * humans, so the check is for the literal type only.
 */
function wantsMarkdown(request) {
  const accept = request.headers.get("Accept") || "";
  return /(^|[\s,])text\/markdown\b/i.test(accept);
}

/**
 * Canonical page path -> its emitted markdown asset path.
 *
 * Note the deliberate absence of a general "has an extension, skip it" rule.
 * Server ids are derived from repo names, and real repos are called things
 * like `video-db/call.md`, `cyberchitta/llm-context.py`, and
 * `triggerdotdev/trigger.dev` — 14 of them in the current dataset. Their
 * canonical pages legitimately end in what looks like a file extension, and
 * their markdown variants are simply that path plus `.md`. Only the genuine
 * data endpoints are excluded.
 */
function markdownPathFor(pathname) {
  if (pathname === "/") return null; // homepage has no .md variant
  // The return value is resolved with `new URL(mdPath, url)`, and a path
  // beginning with two slashes is protocol-relative: "//evil.com/x" resolves
  // to "https://evil.com/x.md", which would then be handed to
  // env.ASSETS.fetch(). Confirmed by replication, along with "///evil.com/y"
  // and "/..//evil.com/z".
  //
  // It is NOT currently reachable in production — Cloudflare normalises the
  // path and answers with a 307 before this Worker runs, verified with a live
  // probe against an IANA-reserved domain. This guard exists because that is a
  // property of the edge, not of this code: it holds only as long as the
  // binding behaves that way, and nothing here would notice if it stopped.
  // A single leading slash, no dot-segments.
  if (!/^\/(?!\/)/.test(pathname) || pathname.split("/").some((seg) => seg === "..")) {
    return null;
  }
  const clean = pathname.replace(/\/$/, "");
  if (/\.(json|csv|xml|txt|ico|png|jpg|svg|webmanifest)$/i.test(clean)) return null;
  return `${clean}.md`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/mcp" || url.pathname === "/mcp/") {
      return handleMcp(request, env);
    }

    // Agent asked for markdown at a canonical URL: serve the .md variant if
    // one was emitted, otherwise fall through to HTML. No X-Robots-Tag here —
    // the URL being served IS the canonical one, so marking it noindex would
    // deindex the page itself.
    const mdPath = wantsMarkdown(request) ? markdownPathFor(url.pathname) : null;
    if (mdPath) {
      const res = await env.ASSETS.fetch(new URL(mdPath, url));
      // The content-type check is load-bearing, not belt-and-braces. Asset
      // resolution is html_handling: auto-trailing-slash, so a request for
      // /servers/<id>.md can resolve to <id>.md.html — the HTML page of a repo
      // whose NAME ends in .md. Without this guard, /servers/video-db--call
      // returned that page's HTML relabelled text/markdown to agents, on a URL
      // that 404s for browsers. Only serve what is genuinely a markdown asset.
      const contentType = res.headers.get("Content-Type") || "";
      if (res.ok && !contentType.includes("text/html")) {
        const headers = new Headers(res.headers);
        headers.set("Content-Type", "text/markdown; charset=utf-8");
        // Caches must not hand this body to a client that wanted HTML.
        headers.set("Vary", "Accept");
        headers.set("Link", `<${url.origin}${url.pathname}>; rel="canonical"`);
        return new Response(res.body, { status: 200, headers });
      }
    }

    // Direct hit on a .md URL. Two very different things land here:
    //
    //   /servers/foo.md          -> the markdown VARIANT of /servers/foo
    //   /servers/video-db--call.md -> the canonical HTML PAGE of a repo whose
    //                                 name really is "call.md"
    //
    // Serving the second as markdown-and-noindex would deindex a real page
    // and point its canonical at a URL that 404s. The assets binding already
    // knows the difference: it returns text/html for a page and
    // text/markdown (or octet-stream) for our emitted variant.
    if (url.pathname.endsWith(".md")) {
      const res = await env.ASSETS.fetch(request);
      const contentType = res.headers.get("Content-Type") || "";
      if (res.ok && !contentType.includes("text/html")) {
        const headers = new Headers(res.headers);
        headers.set("Content-Type", "text/markdown; charset=utf-8");
        headers.set("X-Robots-Tag", "noindex");
        headers.set(
          "Link",
          `<${url.origin}${url.pathname.replace(/\.md$/, "")}>; rel="canonical"`
        );
        return new Response(res.body, { status: res.status, headers });
      }
      // A real page that merely ends in .md — leave the body alone, but this
      // URL still has two representations. /servers/video-db--call.md is the
      // canonical page of a repo named "call.md", AND the branch above serves
      // markdown at the same URL from <id>.md.md when Accept asks for it. The
      // markdown side already sets Vary: Accept; without it here the HTML side
      // could be cached with no Vary and then reused for a markdown request,
      // which is the exact failure the comment below this block describes.
      // One id matches today (video-db--call).
      const htmlHeaders = new Headers(res.headers);
      htmlHeaders.set("Vary", "Accept");
      return new Response(res.body, {
        status: res.status,
        statusText: res.statusText,
        headers: htmlHeaders,
      });
    }

    // Everything else: static assets, with html_handling and the 404 page
    // applied by the assets binding exactly as before this Worker existed.
    //
    // The HTML variant carries Vary: Accept too. Per RFC 9111 a stored
    // response with no Vary is reused for ANY request to that URI, so marking
    // only the markdown side left the common case — HTML cached first — able
    // to satisfy a later markdown request from cache. Both representations of
    // a negotiated URL have to declare what they varied on.
    const assetRes = await env.ASSETS.fetch(request);
    if (markdownPathFor(url.pathname)) {
      const headers = new Headers(assetRes.headers);
      headers.set("Vary", "Accept");
      return new Response(assetRes.body, {
        status: assetRes.status,
        statusText: assetRes.statusText,
        headers,
      });
    }
    return assetRes;
  },
};
