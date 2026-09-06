/**
 * Escaping for third-party text embedded in the markdown variants.
 *
 * Repository descriptions are arbitrary text written by anyone who can create
 * a GitHub repository, and they are emitted into documents that agents read as
 * structure. GitHub itself renders a description as PLAIN TEXT — it does not
 * process markdown there — so rendering it as markdown is not just a risk, it
 * is unfaithful to the source. This makes the output match what the source
 * actually is.
 *
 * What that prevents, in order of how much it would matter:
 *
 *   - Section forgery. A description containing a newline and "## Our summary"
 *     would render an editorial-summary heading that MCP Junction did not
 *     write, on a page whose whole value is that the two are kept apart. The
 *     same trick forges "## Install hint" with a command of the author's
 *     choosing, directly under our name.
 *   - Raw HTML. Angle brackets pass through markdown into whatever renders it.
 *   - List and table corruption. A leading "- " turns prose into a list item;
 *     an unescaped pipe splits a table row into extra columns.
 *
 * Today's dataset contains no description with a newline, a markdown link, or
 * a leading block marker, and only three containing "<". That is a statement
 * about today's 1,800 repositories, not a property of the input: the set is
 * rebuilt nightly from whatever the API returns, and a description can be
 * changed by its owner at any time without anything here changing.
 *
 * Escaping renders identically to the original in any CommonMark renderer —
 * `\*` displays as `*` — so this costs nothing visually.
 */

// ASCII punctuation that carries inline meaning in markdown. Backslash must be
// first in the character class or it escapes the escapes we just added.
// `(` and `)` are absent deliberately: they are only meaningful directly after
// a `]`, which is itself escaped, and escaping them makes URLs in prose noisy.
const INLINE_SPECIALS = /([\\`*_[\]<>|#~])/g;

// Block constructs open only at the start of a line. `#` and `>` are already
// covered above; these are the rest, and they are handled separately because
// escaping every hyphen and digit in a sentence would be absurd.
const LEADING_BLOCK = /^([-+=]|\d+[.)])/;

/**
 * Render untrusted text as literal markdown.
 *
 * Folds all whitespace to single spaces first: block constructs can only open
 * at the start of a line, so collapsing to one line removes that entire class
 * of injection before any escaping happens, and keeps a multi-line value from
 * breaking out of a list item or table row it was interpolated into.
 */
export function mdText(value: unknown): string {
  if (value === null || value === undefined) return '';
  const folded = String(value).replace(/\s+/g, ' ').trim();
  if (!folded) return '';
  return folded.replace(INLINE_SPECIALS, '\\$1').replace(LEADING_BLOCK, '\\$1');
}
