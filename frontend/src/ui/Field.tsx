import type { ReactNode } from 'react'

/** A labelled control in a list row: the label on the left, the control on the right. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex min-h-12 items-center gap-3 px-4 py-2">
      <span className="shrink-0">{label}</span>
      <span className="flex min-w-0 flex-1 justify-end">{children}</span>
    </label>
  )
}

/** The look of a native control inside a Field: plain, right-aligned, in the link colour. */
export const CONTROL =
  'min-w-0 max-w-full bg-transparent text-right text-link outline-none placeholder:text-hint'
