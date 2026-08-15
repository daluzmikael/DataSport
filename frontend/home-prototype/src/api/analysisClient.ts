import { API_URL } from "./config"

function analysisUrl(): string {
  const base =
    API_URL && API_URL.length > 0
      ? API_URL
      : typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:8000"
  return `${base}/api/analysis`
}

export interface AnalysisHistoryMessage {
  role: "user" | "assistant"
  content: string
}

export interface AnalysisResult {
  success: boolean
  analysis: string
  data?: unknown[]
  question?: string
}

/** Calls the real /api/analysis pipeline (router → SQL builder → analyst). */
export async function postAnalysis(
  question: string,
  history: AnalysisHistoryMessage[] = [],
): Promise<AnalysisResult> {
  const res = await fetch(analysisUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(`API ${res.status}${detail ? `: ${detail.slice(0, 300)}` : ""}`)
  }
  const json = (await res.json()) as AnalysisResult
  if (!json.success) {
    throw new Error(json.analysis || "Analysis request failed")
  }
  return json
}
