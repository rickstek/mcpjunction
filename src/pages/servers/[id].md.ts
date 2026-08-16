import type { APIRoute } from 'astro';
import dataset from '../../../public/data/mcp_servers.json';
import categoriesFile from '../../../categories.json';

/**
 * Markdown representation of each server page.
 *
 * Emitted at /servers/<id>.md and served by the Worker at the canonical
 * /servers/<id> when the client sends `Accept: text/markdown`. Generated from
 * the dataset directly rather than converted from the rendered HTML — the
 * data is the source of truth, so there is no parser to get wrong.
 *
 * Cloudflare sells this as "Markdown for Agents" on the Pro plan. Building it
 * from our own data costs nothing and produces cleaner output.
 */

export function getStaticPaths() {
  return dataset.servers.map((s: any) => ({
    params: { id: s.id },
    props: { server: s },
  }));
}

const BASE = 'https://mcpjunction.ai';

// Table cells are pipe-delimited, and repo descriptions are arbitrary text
// from GitHub — an unescaped pipe silently splits the row into extra columns.
const cell = (v: unknown): string =>
  v === null || v === undefined || v === '' ? '—' : String(v).replace(/\|/g, '\\|');

export const GET: APIRoute = ({ props }) => {
  const server: any = (props as any).server;
  const categoryMeta: any = categoriesFile.categories.find((c: any) => c.slug === server.category);
  const categoryName = categoryMeta ? categoryMeta.name : server.category;
  const generatedAt = (dataset as any).generated_at;
  const canonical = `${BASE}/servers/${server.id}`;

  const related = (() => {
    if (server.status !== 'active') return [];
    const peers = dataset.servers
      .filter((s: any) => s.status === 'active' && s.category === server.category && s.id !== server.id)
      .sort((a: any, b: any) => (b.stars || 0) - (a.stars || 0));
    if (peers.length <= 5) return peers;
    let idx = peers.findIndex((s: any) => (s.stars || 0) <= (server.stars || 0));
    if (idx === -1) idx = peers.length;
    const start = Math.max(0, Math.min(idx - 2, peers.length - 5));
    return peers.slice(start, start + 5);
  })();

  const L: string[] = [];
  L.push(`# ${server.name}`);
  L.push('');
  L.push(`${server.full_name} — ${categoryName} — [${canonical}](${canonical})`);
  L.push('');

  if (server.status === 'archived_or_removed') {
    L.push(`> **Delisted.** This repository has been archived or removed from GitHub`);
    L.push(`> since ${server.delisted_at}. This entry stays published for a 30-day`);
    L.push(`> grace window so existing citations do not break, then returns 404.`);
    L.push('');
  }

  if (server.editorial_summary) {
    L.push('## Our summary');
    L.push('');
    L.push(server.editorial_summary);
    L.push('');
    L.push('*Independent of any sponsorship. A summary is not a security review.*');
    L.push('');
  }

  L.push('## Description from the repository');
  L.push('');
  L.push(server.description || '*No description provided.*');
  L.push('');
  L.push(`*Imported from public GitHub metadata for [${server.full_name}](${server.repo_url}). MCP Junction does not author or curate repository descriptions.*`);
  L.push('');

  L.push('## At a glance');
  L.push('');
  L.push('| Field | Value |');
  L.push('| --- | --- |');
  L.push(`| Owner | ${cell(server.owner)} |`);
  L.push(`| Category | ${cell(categoryName)} (${BASE}/categories/${server.category}) |`);
  L.push(`| Language | ${cell(server.language)} |`);
  L.push(`| License | ${cell(server.license)} |`);
  L.push(`| Stars | ${cell(server.stars)} |`);
  L.push(`| Forks | ${cell(server.forks)} |`);
  L.push(`| Open issues | ${cell(server.open_issues)} |`);
  L.push(`| Last pushed | ${cell(server.pushed_at)} |`);
  L.push(`| Repository | ${cell(server.repo_url)} |`);
  if (server.homepage) L.push(`| Homepage | ${cell(server.homepage)} |`);
  L.push(`| Security reviewed | ${server.security_reviewed ? 'yes' : 'no'} |`);
  L.push('');

  if (server.install_hint) {
    L.push('## Install hint');
    L.push('');
    L.push('```');
    L.push(server.install_hint);
    L.push('```');
    L.push('');
    L.push('*Best-effort hint inferred from the repository language. Deliberately excludes auto-confirm flags (`-y`, `--yes`): the package registry name may be held by someone other than the repository owner. Verify against the repository README before running.*');
    L.push('');
  }

  if (related.length) {
    L.push(`## Related servers in ${categoryName}`);
    L.push('');
    for (const s of related) {
      L.push(`- [${s.name}](${BASE}/servers/${s.id}) — ${s.owner} · ${s.stars} stars${s.description ? ` — ${s.description}` : ''}`);
    }
    L.push('');
  }

  L.push('## Cite this entry');
  L.push('');
  L.push(`- Canonical page: ${canonical}`);
  L.push(`- Dataset: ${BASE}/data/mcp_servers.json`);
  L.push(`- Dataset generated: ${generatedAt}`);
  L.push('- Attribution: via mcpjunction.ai');
  L.push(`- Licensing: ${BASE}/licensing — agent retrieval free during launch with attribution; bulk retrieval and AI training require a license.`);
  L.push('');

  return new Response(L.join('\n'), {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
};
