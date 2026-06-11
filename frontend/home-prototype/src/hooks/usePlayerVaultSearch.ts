import { useEffect, useState } from "react"
import { fetchPlayerSearch, type StagingPlayerSearchHit } from "../api/stagingClient"
import { USE_STAGING_API } from "../api/config"

export function usePlayerVaultSearch(query: string) {
  const [results, setResults] = useState<StagingPlayerSearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    const q = query.trim()
    if (!USE_STAGING_API || q.length < 2) {
      setResults([])
      setLoading(false)
      setFromApi(false)
      return
    }

    let cancelled = false
    setLoading(true)

    const timer = window.setTimeout(() => {
      ;(async () => {
        const hits = await fetchPlayerSearch(q, 50)
        if (cancelled) return
        if (hits) {
          setResults(hits)
          setFromApi(true)
        } else {
          setResults([])
          setFromApi(false)
        }
        setLoading(false)
      })()
    }, 280)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [query])

  return { results, loading, fromApi }
}
