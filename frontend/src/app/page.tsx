"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { api, Creator, fmt } from "@/lib/api"

function StatusPill({ s }: { s: Creator["scrape_status"] }) {
  if (s === "scraping" || s === "pending")
    return (
      <span className="pill scraping">
        <span className="spin" /> &nbsp;Scraping
      </span>
    )
  if (s === "ready") return <span className="pill ready">Ready</span>
  if (s === "failed") return <span className="pill failed">Failed</span>
  return <span className="pill pending">{s}</span>
}

export default function Dashboard() {
  const [creators, setCreators] = useState<Creator[]>([])
  const [view, setView] = useState<"grid" | "table">("grid")
  const [link, setLink] = useState("")
  const [adding, setAdding] = useState(false)
  const [err, setErr] = useState("")
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => api.list().then(setCreators).catch(() => {})

  useEffect(() => {
    load()
    timer.current = setInterval(load, 5000) // keep scraping cards fresh
    return () => {
      if (timer.current) clearInterval(timer.current)
    }
  }, [])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    const v = link.trim()
    if (!v) return
    setAdding(true)
    setErr("")
    try {
      await api.add(v)
      setLink("")
      await load()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="wrap">
      <div className="row spread">
        <div>
          <h1 className="h1">Creator Insights</h1>
          <p className="sub">Paste an Instagram account link — we pull their posts and engagement.</p>
        </div>
        <div className="toggle">
          <button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")}>
            Grid
          </button>
          <button className={view === "table" ? "active" : ""} onClick={() => setView("table")}>
            Table
          </button>
        </div>
      </div>

      <form className="row" onSubmit={add} style={{ marginTop: 18 }}>
        <input
          className="input"
          placeholder="https://www.instagram.com/username/  (or @username)"
          value={link}
          onChange={(e) => setLink(e.target.value)}
        />
        <button className="btn" disabled={adding}>
          {adding ? "Adding…" : "+ Add link"}
        </button>
        {err && <span style={{ color: "#f87171", fontSize: 13 }}>{err}</span>}
      </form>

      {creators.length === 0 ? (
        <p className="muted" style={{ marginTop: 40 }}>No creators yet. Add one above.</p>
      ) : view === "grid" ? (
        <div className="grid">
          {creators.map((c) => (
            <Link key={c.id} href={`/creator/${c.id}`} className="card">
              <div className="row spread">
                <div className="row">
                  {c.profile_pic_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="avatar" src={c.profile_pic_url} alt="" />
                  ) : (
                    <div className="avatar" />
                  )}
                  <div>
                    <div className="uname">@{c.username}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{c.full_name}</div>
                  </div>
                </div>
                <StatusPill s={c.scrape_status} />
              </div>
              <div className="row spread">
                <div className="stat muted">
                  <b style={{ color: "var(--text)" }}>{fmt(c.post_count)}</b> posts
                </div>
                <div className="stat muted">
                  <b style={{ color: "var(--green-soft)" }}>{fmt(c.total_views)}</b> views
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Creator</th>
              <th>Status</th>
              <th className="num">Posts</th>
              <th className="num">Total views</th>
              <th className="num">Followers</th>
            </tr>
          </thead>
          <tbody>
            {creators.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link href={`/creator/${c.id}`} className="link">@{c.username}</Link>
                </td>
                <td><StatusPill s={c.scrape_status} /></td>
                <td className="num">{fmt(c.post_count)}</td>
                <td className="num">{fmt(c.total_views)}</td>
                <td className="num">{fmt(c.followers)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
