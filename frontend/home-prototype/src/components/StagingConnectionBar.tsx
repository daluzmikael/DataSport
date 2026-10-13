import { useEffect, useState } from "react"
import { API_URL } from "../api/config"
import { fetchStagingHealth } from "../api/stagingClient"

export function StagingConnectionBar() {
  const [status, setStatus] = useState<"checking" | "ok" | "offline">("checking")
  const [tables, setTables] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let attempt = 0
    // Keep retrying: a cold-starting (or reloading) backend answers a few seconds
    // later, and a one-shot check left the "offline" banner up for good.
    const check = async () => {
      const health = await fetchStagingHealth()
      if (cancelled) return
      if (health?.tables?.length) {
        setStatus("ok")
        setTables(health.tables)
        return
      }
      setStatus("offline")
      attempt += 1
      timer = setTimeout(check, Math.min(3000 * attempt, 15000))
    }
    void check()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [])

  if (status === "checking") return null

  return (
    <div
      className={`shrink-0 border-b px-3 py-1.5 text-center text-[10px] ${
        status === "ok"
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
          : "border-amber-500/30 bg-amber-500/10 text-amber-200"
      }`}
    >
      {status === "ok" ? (
        <>
          Vault connected · {tables.length} staged tables · {API_URL}
        </>
      ) : (
        <>
          Connecting to the stats vault… showing sample data until it responds.
          {import.meta.env.DEV && (
            <>
              {" "}Start backend: <code className="font-mono">uvicorn main:app --port 8000</code>
            </>
          )}
        </>
      )}
    </div>
  )
}
