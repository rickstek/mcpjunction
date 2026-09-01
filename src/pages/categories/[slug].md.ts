import type { APIRoute } from 'astro';
import dataset from '../../../public/data/mcp_servers.json';
import categoriesFile from '../../../categories.json';

/** Markdown representation of each category page. See servers/[id].md.ts. */

export function getStaticPaths() {
  return categoriesFile.categories.map((c: any) => ({
    params: { slug: c.slug },
    props: { category: c },
  }));
}

const BASE = 'https://mcpjunction.ai';

export const GET: APIRoute = ({ props }) => {
  const category: any = (props as any).category;
  const generatedAt = (dataset as any).generated_at;

  const members = dataset.servers
    .filter((s: any) => s.status === 'active' && s.category === category.slug)
    .sort((a: any, b: any) => (b.stars || 0) - (a.stars || 0));

  const L: string[] = [];
  L.push(`# ${category.name}`);
  L.push('');
  L.push(category.description);
  L.push('');
  if (category.intro) {
    L.push(category.intro);
    L.push('');
  }
  L.push(`${members.length} server${members.length === 1 ? '' : 's'} · updated ${generatedAt} · [${BASE}/categories/${category.slug}](${BASE}/categories/${category.slug})`);
  L.push('');

  if (!members.length) {
    L.push('*No servers currently listed in this category.*');
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
