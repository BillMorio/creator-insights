"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { api, CreatorDetail, fmt } from "@/lib/api"

export default function CreatorPage() {
  const { id } = useParams<{ id: string }>()
  const cid = Number(id)
  const router = useRouter()
  const [c, setC] = useState<CreatorDetail | null>(null)
  const [err, setErr] = useState("")
  const [sort, setSort] = useState<"views" | "likes" | "comments" | "date">("views")
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => api.get(cid).then(setC).catch((e) => setErr(String(e)))

  useEffect(() => {
    load()
    timer.current = setInterval(() => {
      // keep polling while a scrape is in flight
      api.get(cid).then((d) => {
        setC(d)
        if (d.scrape_status !== "scraping" && d.scrape_status !== "pending" && timer.current) {
          clearInterval(timer.current)
        }
      }).catch(() => {})
    }, 5000)
    return () => {
      if (timer.current) clearInterval(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cid])

  if (err) return <div className="wrap"><p style={{ color: "#f87171" }}>{err}</p></div>
  if (!c) return <div className="wrap"><p className="muted">Loading…</p></div>

  const posts = [...c.posts].sort((a, b) => {
    if (sort === "date") return (b.posted_at || "").localeCompare(a.posted_at || "")
    const k = sort
    return (Number(b[k] ?? 0)) - (Number(a[k] ?? 0))
  })

  return (
    <div className="wrap">
      <Link href="/" className="muted" style={{ fontSize: 13 }}>← All creators</Link>

      <div className="row spread" style={{ marginTop: 14 }}>
        <div className="row">
          {c.profile_pic_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img className="avatar" src={c.profile_pic_url} alt="" style={{ width: 56, height: 56 }} />
          ) : (
            <div className="avatar" style={{ width: 56, height: 56 }} />
          )}
          <div>
            <h1 className="h1">@{c.username}</h1>
            <div className="sub">
              {fmt(c.post_count)} posts · {fmt(c.total_views)} views · {fmt(c.followers)} followers
              {c.scrape_status === "scraping" && <> · <span style={{ color: "#fbbf24" }}>scraping…</span></>}
              {c.scrape_status === "failed" && <> · <span style={{ color: "#f87171" }}>failed: {c.scrape_error}</span></>}
            </div>
          </div>
        </div>
        <div className="row">
          <a className="btn ghost" href={api.exportUrl(c.id)}>Download CSV</a>
          <button className="btn ghost" onClick={() => api.refresh(c.id).then(load)}>Refresh</button>
          <button
            className="btn ghost"
            onClick={async () => {
              if (confirm(`Delete @${c.username}?`)) {
                await api.remove(c.id)
                router.push("/")
              }
            }}
          >
            Delete
          </button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Post</th>
            <th>Type</th>
            <th className="num" style={{ cursor: "pointer" }} onClick={() => setSort("views")}>Views</th>
            <th className="num" style={{ cursor: "pointer" }} onClick={() => setSort("likes")}>Likes</th>
            <th className="num" style={{ cursor: "pointer" }} onClick={() => setSort("comments")}>Comments</th>
            <th style={{ cursor: "pointer" }} onClick={() => setSort("date")}>Posted</th>
          </tr>
        </thead>
        <tbody>
          {posts.map((p) => (
            <tr key={p.id}>
              <td>
                <a className="link" href={p.url} target="_blank" rel="noopener noreferrer">
                  {p.url.replace("https://www.instagram.com", "")}
                </a>
              </td>
              <td className="muted">{p.media_type || "—"}</td>
              <td className="num">{fmt(p.views)}</td>
              <td className="num">{fmt(p.likes)}</td>
              <td className="num">{fmt(p.comments)}</td>
              <td className="muted">{p.posted_at ? p.posted_at.slice(0, 10) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {posts.length === 0 && <p className="muted" style={{ marginTop: 20 }}>No posts yet — scrape may still be running.</p>}
    </div>
  )
}
