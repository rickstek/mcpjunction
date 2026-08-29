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
      "Data refreshes nightly from the public GitHub API.",
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
      "stars, category, and editorial fields.",
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
// belongs in code; a rate-limiting rule at the edge covers request floods.
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
  return { ...publicEntry(s), topics: s.topics, forks: s.forks, open_issues: s.open_issues, pushed_at: s.pushed_at, homepage: s.homepage, attribution: ATTRIBUTION };
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

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
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
      return res; // a real page that merely ends in .md — leave it alone
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
