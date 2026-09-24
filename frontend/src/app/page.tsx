"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { api, Creator, fmt } from "@/lib/api"

function StatusPill({ s }: { s: Creator["scrape_status"] }) {
  if (s === "scraping" || s === "pending")
    return (
      <span className="pill scraping">
        <span className="spin" />
        Scraping
      </span>
    )
  if (s === "ready") return <span className="pill ready">Ready</span>
  if (s === "failed") return <span className="pill failed">Failed</span>
  return <span className="pill pending">{s}</span>
}

function Avatar({ src, lg, name }: { src?: string; lg?: boolean; name?: string }) {
  const cls = `avatar${lg ? " lg" : ""}`
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img className={cls} src={src} alt="" />
  }
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?"
  return <div className={`${cls} avatar-fallback`}>{initial}</div>
}

export default function Dashboard() {
  const [creators, setCreators] = useState<Creator[]>([])
  const [loaded, setLoaded] = useState(false)
  const [view, setView] = useState<"grid" | "table">("grid")
  const [link, setLink] = useState("")
  const [adding, setAdding] = useState(false)
  const [err, setErr] = useState("")
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () =>
    api.list().then((d) => { setCreators(d); setLoaded(true) }).catch(() => setLoaded(true))

  useEffect(() => {
    load()
    timer.current = setInterval(load, 5000)
    return () => { if (timer.current) clearInterval(timer.current) }
  }, [])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    const v = link.trim()
    if (!v) return
    setAdding(true); setErr("")
    try { await api.add(v); setLink(""); await load() }
    catch (e) { setErr(e instanceof Error ? e.message.slice(0, 120) : String(e)) }
    finally { setAdding(false) }
  }

  const totalViews = creators.reduce((s, c) => s + (c.total_views || 0), 0)
  const totalPosts = creators.reduce((s, c) => s + (c.post_count || 0), 0)

  return (
    <div className="wrap">
      <div className="header">
        <div className="brand">
          <div className="logo">CI</div>
          <div>
            <h1 className="h1">Creator Insights</h1>
            <p className="sub">Paste an Instagram account — we pull their posts and engagement.</p>
          </div>
        </div>
        <div className="row" style={{ gap: 10 }}>
          {creators.length > 0 && (
            <a className="btn ghost" href={api.exportAllUrl()}>↓ Export all</a>
          )}
          <div className="toggle">
            <button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")}>Grid</button>
            <button className={view === "table" ? "active" : ""} onClick={() => setView("table")}>Table</button>
          </div>
        </div>
      </div>

      <form className="toolbar" onSubmit={add}>
        <div className="field">
          <span className="at">@</span>
          <input
            className="input"
            placeholder="instagram.com/username  ·  or  username"
            value={link}
            onChange={(e) => setLink(e.target.value)}
          />
        </div>
        <button className="btn" disabled={adding}>{adding ? "Adding…" : "+ Add creator"}</button>
        {err && <span className="err">{err}</span>}
      </form>

      {creators.length > 0 && (
        <div className="strip">
          <div><div className="k">Creators</div><div className="v">{fmt(creators.length)}</div></div>
          <div><div className="k">Posts tracked</div><div className="v">{fmt(totalPosts)}</div></div>
          <div><div className="k">Total views</div><div className="v green">{fmt(totalViews)}</div></div>
        </div>
      )}

      {!loaded ? (
        <div className="grid">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card skeleton" style={{ height: 150, border: "none" }} />
          ))}
        </div>
      ) : creators.length === 0 ? (
        <div className="empty">
          <div className="big">No creators yet</div>
          Paste an Instagram account link above to get started.
        </div>
      ) : view === "grid" ? (
        <div className="grid">
          {creators.map((c) => (
            <Link key={c.id} href={`/creator/${c.id}`} className="card">
              <div className="card-top">
                <div className="who">
                  <Avatar src={c.profile_pic_url} name={c.username} />
                  <div style={{ minWidth: 0 }}>
                    <div className="uname">@{c.username}</div>
                    <div className="fname">{c.full_name || " "}</div>
                  </div>
                </div>
                <StatusPill s={c.scrape_status} />
              </div>
              <div className="metrics">
                <div className="metric"><div className="mk">Posts</div><div className="mv">{fmt(c.post_count)}</div></div>
                <div className="metric"><div className="mk">Views</div><div className="mv green">{fmt(c.total_views)}</div></div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Creator</th><th>Status</th>
                <th className="num">Posts</th><th className="num">Total views</th><th className="num">Followers</th>
              </tr>
            </thead>
            <tbody>
              {creators.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/creator/${c.id}`} className="who">
                      <Avatar src={c.profile_pic_url} name={c.username} />
                      <span className="link" style={{ fontWeight: 600 }}>@{c.username}</span>
                    </Link>
                  </td>
                  <td><StatusPill s={c.scrape_status} /></td>
                  <td className="num">{fmt(c.post_count)}</td>
                  <td className="num" style={{ color: "var(--green-soft)" }}>{fmt(c.total_views)}</td>
                  <td className="num">{fmt(c.followers)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
