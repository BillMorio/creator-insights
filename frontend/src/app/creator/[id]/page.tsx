"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { api, CreatorDetail, fmt } from "@/lib/api"

type Sort = "views" | "likes" | "comments" | "date"

export default function CreatorPage() {
  const { id } = useParams<{ id: string }>()
  const cid = Number(id)
  const router = useRouter()
  const [c, setC] = useState<CreatorDetail | null>(null)
  const [err, setErr] = useState("")
  const [sort, setSort] = useState<Sort>("views")
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => api.get(cid).then(setC).catch((e) => setErr(String(e)))

  useEffect(() => {
    load()
    timer.current = setInterval(() => {
      api.get(cid).then((d) => {
        setC(d)
        if (d.scrape_status !== "scraping" && d.scrape_status !== "pending" && timer.current) clearInterval(timer.current)
      }).catch(() => {})
    }, 5000)
    return () => { if (timer.current) clearInterval(timer.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cid])

  if (err) return <div className="wrap"><p className="err">{err}</p></div>
  if (!c) return <div className="wrap"><div className="skeleton" style={{ height: 80, borderRadius: 14 }} /></div>

  const posts = [...c.posts].sort((a, b) => {
    if (sort === "date") return (b.posted_at || "").localeCompare(a.posted_at || "")
    return Number(b[sort] ?? 0) - Number(a[sort] ?? 0)
  })
  const th = (key: Sort, label: string, num = true) => (
    <th className={`sortable${num ? " num" : ""}`} onClick={() => setSort(key)}>
      {label}{sort === key ? " ↓" : ""}
    </th>
  )

  return (
    <div className="wrap">
      <Link href="/" className="back">← All creators</Link>

      <div className="header" style={{ marginTop: 16 }}>
        <div className="brand">
          {c.profile_pic_url
            // eslint-disable-next-line @next/next/no-img-element
            ? <img className="avatar lg" src={c.profile_pic_url} alt="" />
            : <div className="avatar lg" />}
          <div>
            <h1 className="h1">@{c.username}</h1>
            <div className="dstats">
              <span className="dstat"><b>{fmt(c.post_count)}</b> posts</span>
              <span className="dstat">·</span>
              <span className="dstat"><b style={{ color: "var(--green-soft)" }}>{fmt(c.total_views)}</b> views</span>
              <span className="dstat">·</span>
              <span className="dstat"><b>{fmt(c.followers)}</b> followers</span>
              {c.scrape_status === "scraping" && <span className="pill scraping" style={{ marginLeft: 6 }}><span className="spin" />Scraping</span>}
              {c.scrape_status === "failed" && <span className="err" style={{ marginLeft: 6 }}>failed: {c.scrape_error}</span>}
            </div>
          </div>
        </div>
        <div className="toolbar" style={{ marginTop: 0 }}>
          <a className="btn ghost" href={api.exportUrl(c.id)}>↓ CSV</a>
          <button className="btn ghost" onClick={() => api.refresh(c.id).then(load)}>Refresh</button>
          <button className="btn ghost" onClick={async () => {
            if (confirm(`Delete @${c.username}?`)) { await api.remove(c.id); router.push("/") }
          }}>Delete</button>
        </div>
      </div>

      {posts.length === 0 ? (
        <div className="empty">
          <div className="big">No posts yet</div>
          {c.scrape_status === "scraping" ? "Scraping in progress — this updates automatically." : "Try Refresh."}
        </div>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Post</th><th>Type</th>
                {th("views", "Views")}{th("likes", "Likes")}{th("comments", "Comments")}
                <th className="sortable" onClick={() => setSort("date")}>Posted{sort === "date" ? " ↓" : ""}</th>
              </tr>
            </thead>
            <tbody>
              {posts.map((p) => (
                <tr key={p.id}>
                  <td><a className="link" href={p.url} target="_blank" rel="noopener noreferrer">{p.url.replace("https://www.instagram.com", "")}</a></td>
                  <td><span className="chip">{p.media_type || "post"}</span></td>
                  <td className="num">{fmt(p.views)}</td>
                  <td className="num">{fmt(p.likes)}</td>
                  <td className="num">{fmt(p.comments)}</td>
                  <td style={{ color: "var(--muted)" }}>{p.posted_at ? p.posted_at.slice(0, 10) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
