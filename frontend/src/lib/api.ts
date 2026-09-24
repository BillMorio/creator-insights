// API client for the creator-insights backend.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://creator-insights-api-yjx7.onrender.com"

export type Creator = {
  id: number
  username: string
  profile_url: string
  full_name: string
  followers: number
  media_count: number
  profile_pic_url: string
  is_private: boolean
  scrape_status: "pending" | "scraping" | "ready" | "failed"
  scrape_error: string
  last_scraped_at: string | null
  created_at: string
  post_count: number
  total_views: number
}

export type Post = {
  id: number
  shortcode: string
  url: string
  media_type: string
  views: number | null
  likes: number
  comments: number
  caption: string
  thumbnail_url: string
  posted_at: string | null
}

export type CreatorDetail = Creator & { posts: Post[] }

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}

export const api = {
  list: () => fetch(`${API_BASE}/api/creators`, { cache: "no-store" }).then((r) => j<Creator[]>(r)),
  get: (id: number) =>
    fetch(`${API_BASE}/api/creators/${id}`, { cache: "no-store" }).then((r) => j<CreatorDetail>(r)),
  add: (link: string) =>
    fetch(`${API_BASE}/api/creators`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link }),
    }).then((r) => j<Creator>(r)),
  refresh: (id: number) =>
    fetch(`${API_BASE}/api/creators/${id}/refresh`, { method: "POST" }).then((r) => j<Creator>(r)),
  remove: (id: number) => fetch(`${API_BASE}/api/creators/${id}`, { method: "DELETE" }),
  exportUrl: (id: number) => `${API_BASE}/api/creators/${id}/export`,
  exportAllUrl: () => `${API_BASE}/api/creators/export-all`,
}

export function fmt(n: number | null | undefined): string {
  if (n == null) return "—"
  return n.toLocaleString("en-US")
}
