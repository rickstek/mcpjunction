/**
 * Why a server page is delisted, in words that are true.
 *
 * Until 2026-11 every delisted page said the repository "has been archived or
 * removed from GitHub". Measured against GitHub on 2026-11-26 that was true for
 * 32 of 252 pages; the rest were live repositories the capped nightly search
 * had simply stopped returning. The pipeline now asks GitHub what happened
 * (scripts/vanished.py) and records it as `delisted_reason`; this turns the
 * reason into the sentence each surface shows.
 */

export interface Delisting {
  /** Lower-case clause, e.g. "its owner archived the repository on GitHub". */
  reason: string;
  /** For a move: where the repository went, and where to send the reader. */
  moved?: { label: string; href: string };
}

export function describeDelisting(server: any, listedIds: Set<string>): Delisting {
  switch (server.delisted_reason) {
    case 'removed':
      return { reason: 'the repository was deleted or made private on GitHub' };
    case 'archived':
      return { reason: 'its owner archived the repository on GitHub' };
    case 'no_longer_matches':
      return {
        reason:
          'the repository no longer describes itself as an MCP project, so it ' +
          "no longer meets this directory's inclusion rule",
      };
    case 'moved': {
      const to = String(server.moved_to || '');
      const id = to.toLowerCase().replace('/', '--');
      // Send readers to our page for the new name when we list it, otherwise
      // to the repository itself -- never to a URL that would 404.
      const href = listedIds.has(id) ? `/servers/${id}` : `https://github.com/${to}`;
      return { reason: 'the repository moved on GitHub to', moved: { label: to, href } };
    }
    default:
      return { reason: 'it is no longer listed in this directory' };
  }
}
