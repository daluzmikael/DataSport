import { Search } from "lucide-react"

interface AskReferenceButtonProps {
  label: string
  onReference: (label: string) => void
  className?: string
}

export function AskReferenceButton({
  label,
  onReference,
  className = "",
}: AskReferenceButtonProps) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        e.preventDefault()
        onReference(label)
      }}
      className={`inline-flex shrink-0 items-center justify-center rounded p-0.5 text-ds-muted/50 transition hover:bg-ds-accent/15 hover:text-ds-accent ${className}`}
      title={`Reference ${label} in analyzer`}
      aria-label={`Reference ${label} in analyzer`}
    >
      <Search className="h-2.5 w-2.5" strokeWidth={2.5} />
    </button>
  )
}

interface ReferencedLabelProps {
  label: string
  onReference?: (label: string) => void
  className?: string
}

export function ReferencedLabel({ label, onReference, className = "" }: ReferencedLabelProps) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`}>
      <span>{label}</span>
      {onReference && <AskReferenceButton label={label} onReference={onReference} />}
    </span>
  )
}
