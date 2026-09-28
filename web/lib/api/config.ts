/** Public backend origin. Empty means the API is served from the same origin as the web app. */
export const ATLAS_API_BASE_URL = (process.env.NEXT_PUBLIC_ATLAS_API_BASE_URL ?? "").replace(/\/$/, "");
