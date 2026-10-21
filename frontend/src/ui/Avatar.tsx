/** Initials, never a photo (ADR-0003): no third-party image ever loads. */
export function Avatar({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')
  return (
    <span
      aria-hidden
      className="flex size-14 shrink-0 items-center justify-center rounded-full bg-button text-xl font-semibold text-button-text"
    >
      {initials || '?'}
    </span>
  )
}
