import { ChevronRight } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface CellProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
  label: ReactNode
  detail?: ReactNode
  trailing?: ReactNode
  /** Shows the chevron that says "this opens a screen". */
  opens?: boolean
}

/** A list row: an icon, a label, an optional detail, and what sits at its end. */
export function Cell({ icon, label, detail, trailing, opens, ...button }: CellProps) {
  return (
    <button
      type="button"
      className="flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
      {...button}
    >
      {icon && (
        <span className="flex size-7 shrink-0 items-center justify-center text-accent">{icon}</span>
      )}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {detail && <span className="shrink-0 text-hint">{detail}</span>}
      {trailing}
      {opens && <ChevronRight aria-hidden className="size-5 shrink-0 text-hint" />}
    </button>
  )
}
