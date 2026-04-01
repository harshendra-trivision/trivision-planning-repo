/**
 * Returns the item slug from .../forecast/editor/<slug>/, or '' when at the editor root.
 * Handles scenario-prefixed paths (e.g. /scenario2/forecast/editor/) where a naive
 * split would yield '/' instead of an empty segment.
 */
export function forecastEditorItemSlug() {
  const raw = window.location.pathname.split("/editor/")[1] || "";
  return raw.replace(/^\/+|\/+$/g, "");
}
