import "./globals.css"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Creator Insights",
  description: "Track Instagram creators — posts, views, engagement.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
