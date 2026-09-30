// Single source for the user-facing brand name.
// docs/components/index.html mirrors this value manually (static file).
export const BRAND_NAME = "Task Matrix";

// Four-quadrant matrix mark. One active cell uses the app accent green.
const FAVICON_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
  '<rect x="1" y="1" width="30" height="30" rx="6" fill="#e6e9ee" stroke="#8b949e" stroke-width="2"/>' +
  '<rect x="7" y="7" width="8" height="8" rx="1.5" fill="#1f883d"/>' +
  '<rect x="17" y="7" width="8" height="8" rx="1.5" fill="#8b949e"/>' +
  '<rect x="7" y="17" width="8" height="8" rx="1.5" fill="#8b949e"/>' +
  '<rect x="17" y="17" width="8" height="8" rx="1.5" fill="#8b949e"/>' +
  "</svg>";

export const FAVICON_HREF = `data:image/svg+xml,${encodeURIComponent(FAVICON_SVG)}`;
