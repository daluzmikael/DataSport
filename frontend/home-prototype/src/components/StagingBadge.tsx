/** Small indicator when a panel is backed by staged parquet via the API. */
export function StagingBadge({ show }: { show: boolean }) {
  if (!show) return null
  return (
    <span className="ml-2 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-emerald-400">
      Vault
    </span>
  )
}
