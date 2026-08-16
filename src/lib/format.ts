/**
 * Locale-pinned number formatting.
 *
 * Bare `toLocaleString()` formats using the BUILD MACHINE's locale, which is
 * not a property of the content and is not stable across machines. A developer
 * box resolving to es-UY renders 36,136 stars as "36.136" — which reads as
 * thirty-six-point-one to an English speaker, and gets extracted as a fact by
 * the answer engines this site is built to feed. It passed unnoticed because
 * CI happens to run en-US.
 *
 * Every number rendered on this site is a count, so one shared formatter is
 * enough. Import this instead of calling toLocaleString directly.
 */
const NUMBER_FORMAT = new Intl.NumberFormat('en-US');

export function fmt(value: unknown): string {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? NUMBER_FORMAT.format(n) : '—';
}
