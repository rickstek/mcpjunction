import type { APIRoute } from 'astro';
import dataset from '../../../public/data/mcp_servers.json';
import topicsFile from '../../../topics.json';

/** Markdown representation of each topic page. See servers/[id].md.ts. */

export function getStaticPaths() {
  return topicsFile.topics.map((tag: string) => ({
    params: { tag },
    props: { tag },
  }));
}

const BASE = 'https://mcpjunction.ai';

export const GET: APIRoute = ({ props }) => {
  const tag: string = (props as any).tag;
  const generatedAt = (dataset as any).generated_at;

  const members = dataset.servers
    .filter((s: any) => s.status === 'active'
      && Array.isArray(s.topics)
      && s.topics.some((t: string) => String(t).toLowerCase() === tag))
    .sort((a: any, b: any) => (b.stars || 0) - (a.stars || 0));

  const L: string[] = [];
  L.push(`# ${tag} MCP servers`);
  L.push('');
  L.push(`Servers whose GitHub repository topics include \`${tag}\`. Topics are repository-owner strings imported verbatim; MCP Junction does not assign or curate them.`);
  L.push('');
  const intro: string | undefined = (topicsFile as any).intros?.[tag];
  if (intro) {
    L.push(intro);
    L.push('');
  }
  L.push(`${members.length} server${members.length === 1 ? '' : 's'} · updated ${generatedAt} · [${BASE}/topics/${tag}](${BASE}/topics/${tag})`);
  L.push('');

  if (!members.length) {
    L.push('*No active servers currently carry this topic.*');
  } else {
    for (const s of members) {
      const bits = [s.owner, s.language || 'language n/a', `${s.stars} stars`];
      if (s.security_reviewed) bits.push('reviewed');
      L.push(`- [${s.name}](${BASE}/servers/${s.id}) — ${bits.join(' · ')}${s.description ? ` — ${s.description}` : ''}`);
    }
  }
  L.push('');
  L.push('---');
  L.push('');
  L.push(`Full dataset: ${BASE}/data/mcp_servers.json · Licensing: ${BASE}/licensing · Attribution: via mcpjunction.ai`);
  L.push('');

  return new Response(L.join('\n'), {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
};
