export type StagingBadgeVariant = "vault" | "mock"

const VARIANT_CLASS: Record<StagingBadgeVariant, string> = {
  vault: "bg-emerald-500/15 text-emerald-400",
  mock: "bg-zinc-500/15 text-zinc-400",
}

const VARIANT_LABEL: Record<StagingBadgeVariant, string> = {
  vault: "Vault",
  mock: "Mock",
}

/** Small indicator for staging API data, derived rates, or mock content. */
export function StagingBadge({
  show,
  variant = "vault",
}: {
  show: boolean
  variant?: StagingBadgeVariant
}) {
  if (!show) return null
  return (
    <span
      className={`ml-2 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${VARIANT_CLASS[variant]}`}
    >
      {VARIANT_LABEL[variant]}
    </span>
  )
}