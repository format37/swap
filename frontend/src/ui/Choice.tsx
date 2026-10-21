import { Check, Circle, CircleDot, Square } from 'lucide-react'
import type { ReactNode } from 'react'

/** A list row that is chosen or not: one of several (radio) or any of several (checkbox). */
export function Choice({
  kind,
  label,
  checked,
  onChange,
  leading,
}: {
  kind: 'radio' | 'checkbox'
  label: ReactNode
  checked: boolean
  onChange: () => void
  leading?: ReactNode
}) {
  const mark =
    kind === 'radio' ? (
      checked ? (
        <CircleDot aria-hidden className="size-5 text-accent" />
      ) : (
        <Circle aria-hidden className="size-5 text-hint" />
      )
    ) : checked ? (
      <span className="flex size-5 items-center justify-center rounded bg-button text-button-text">
        <Check aria-hidden className="size-4" />
      </span>
    ) : (
      <Square aria-hidden className="size-5 text-hint" />
    )
  return (
    <button
      type="button"
      role={kind}
      aria-checked={checked}
      onClick={onChange}
      className="flex min-h-12 w-full items-center gap-3 px-4 py-2 text-left active:bg-secondary-bg"
    >
      {mark}
      {leading}
      <span className="min-w-0 flex-1 truncate">{label}</span>
    </button>
  )
}
