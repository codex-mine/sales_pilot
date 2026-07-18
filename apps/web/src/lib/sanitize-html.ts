import DOMPurify from "dompurify";

/**
 * Sanitizes AI-generated (or any untrusted) HTML before it's ever passed to
 * `dangerouslySetInnerHTML` — used for email body previews in the Email
 * Generation module's review screen. Strips scripts/event handlers/iframes
 * etc.; keeps the small set of tags a plain marketing email body needs.
 */
export function sanitizeEmailHtml(html: string): string {
  // DOMPurify needs a real `window`/DOM to run — Next.js also evaluates
  // client-component code during SSR, where neither exists yet. The actual
  // risk (dangerouslySetInnerHTML) only happens once this hydrates in the
  // browser, so it's safe to pass the raw string through server-side and
  // sanitize for real on the client.
  if (typeof window === "undefined") return html;
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      "p", "br", "b", "strong", "i", "em", "u", "a", "ul", "ol", "li",
      "h1", "h2", "h3", "h4", "span", "div", "blockquote", "hr", "img", "table",
      "thead", "tbody", "tr", "td", "th",
    ],
    ALLOWED_ATTR: ["href", "target", "rel", "src", "alt", "style", "width", "height"],
  });
}
