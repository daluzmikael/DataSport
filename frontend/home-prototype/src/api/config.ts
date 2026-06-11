/** Empty string uses the Vite dev proxy (/api/staging → localhost:8000). */
export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? ""

export const USE_STAGING_API = (import.meta.env.VITE_USE_STAGING_API as string | undefined) !== "false"
