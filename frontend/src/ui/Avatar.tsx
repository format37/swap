const SIZES = {
  sm: 'size-10 text-base',
  lg: 'size-14 text-xl',
  xl: 'size-20 text-3xl',
}

/** Initials, never a photo (ADR-0003): no third-party image ever loads. */
export function Avatar({ name, size = 'lg' }: { name: string; size?: keyof typeof SIZES }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')
  return (
    <span
      aria-hidden
      className={`flex ${SIZES[size]} shrink-0 items-center justify-center rounded-full bg-button font-semibold text-button-text`}
    >
      {initials || '?'}
    </span>
  )
}
