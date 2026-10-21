import type { LucideIcon } from 'lucide-react'

/** One of several choices that can all be on at once, with its icon (ADR-0003). */
export function Chip({
  icon: Icon,
  label,
  selected,
  onToggle,
}: {
  icon: LucideIcon
  label: string
  selected: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onToggle}
      className={`flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium ${selected ? 'bg-button text-button-text' : 'bg-secondary-bg text-text'}`}
    >
      <Icon aria-hidden className="size-4" />
      {label}
    </button>
  )
}
