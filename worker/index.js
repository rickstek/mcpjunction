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
const DATASET_TTL_MS = 10 * 60 * 1000;
let datasetCache = { data: null, fetchedAt: 0 };

async function getDataset(env, requestUrl) {
  const now = Date.now();
  if (datasetCache.data && now - datasetCache.fetchedAt < DATASET_TTL_MS) {
    return datasetCache.data;
  }
  const assetUrl = new URL("/data/mcp_servers.json", requestUrl);
  const res = await env.ASSETS.fetch(assetUrl);
  if (!res.ok) throw new Error(`dataset fetch failed: ${res.status}`);
  const data = await res.json();
  datasetCache = { data, fetchedAt: now };
  return data;
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: "search_servers",
    description:
      "Search the MCP server directory by keyword. Matches name, description, " +
      "and GitHub topics. Returns active servers sorted by relevance then stars. " +
      "Data refreshes nightly from the public GitHub API.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Keywords, e.g. 'postgres', 'browser automation'" },
        category: { type: "string", description: "Optional category slug filter, e.g. 'databases' (see list_categories)" },
        language: { type: "string", description: "Optional implementation language filter, e.g. 'Python'" },
        limit: { type: "integer", minimum: 1, maximum: 50, description: "Max results (default 10)" },
      },
      required: ["query"],
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

function toolSearchServers(dataset, args) {
  const query = String(args.query || "").toLowerCase().trim();
  if (!query) return { error: "query is required" };
  const terms = query.split(/\s+/).filter(Boolean);
  const category = args.category ? String(args.category).toLowerCase() : null;
  const language = args.language ? String(args.language).toLowerCase() : null;
  const limit = Math.min(Math.max(parseInt(args.limit, 10) || 10, 1), 50);

  const scored = [];
  for (const s of dataset.servers) {
    if (s.status !== "active") continue;
    if (category && s.category !== category) continue;
    if (language && String(s.language || "").toLowerCase() !== language) continue;
    const hay = `${s.full_name} ${s.description || ""} ${(s.topics || []).join(" ")}`.toLowerCase();
    let score = 0;
    for (const t of terms) if (hay.includes(t)) score += 1;
    if (score === 0) continue;
    scored.push([score, s.stars || 0, s]);
  }
  scored.sort((a, b) => b[0] - a[0] || b[1] - a[1]);

  return {
    query: args.query,
    total_matches: scored.length,
    returned: Math.min(limit, scored.length),
    results: scored.slice(0, limit).map(([, , s]) => publicEntry(s)),
    attribution: ATTRIBUTION,
  };
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

  let msg;
  try {
    msg = await request.json();
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
              "list_categories to browse. Data refreshes nightly. " +
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
    return jsonResponse(rpcError(id, -32603, `Internal error: ${e.message}`), 500);
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
      if (res.ok) {
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
    return env.ASSETS.fetch(request);
  },
};
