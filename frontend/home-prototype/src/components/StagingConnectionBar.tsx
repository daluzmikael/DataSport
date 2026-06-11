import { useEffect, useState } from "react"
import { API_URL } from "../api/config"
import { fetchStagingHealth } from "../api/stagingClient"

export function StagingConnectionBar() {
  const [status, setStatus] = useState<"checking" | "ok" | "offline">("checking")
  const [tables, setTables] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const health = await fetchStagingHealth()
      if (cancelled) return
      if (health?.tables?.length) {
        setStatus("ok")
        setTables(health.tables)
      } else {
        setStatus("offline")
      }
    })()
    return () => {
      cancelled = true
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
          Vault offline — using mock data. Start backend:{" "}
          <code className="font-mono">uvicorn main:app --port 8000</code>
        </>
      )}
    </div>
  )
}
