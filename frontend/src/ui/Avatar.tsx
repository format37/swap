import { useState } from 'react'

const SIZES = {
  xs: 'size-8 text-xs',
  sm: 'size-10 text-base',
  lg: 'size-14 text-xl',
  xl: 'size-20 text-3xl',
}

export type AvatarSize = keyof typeof SIZES

/**
 * Someone's Telegram photo, loaded straight from Telegram, or their initials when there is
 * none or it doesn't load (QUESTIONS J4, ADR-0027).
 */
export function Avatar({
  name,
  photo,
  size = 'lg',
}: {
  name: string
  photo?: string | null
  size?: AvatarSize
}) {
  const [failed, setFailed] = useState<string | null>(null)
  if (photo && failed !== photo)
    return (
      <img
        aria-hidden
        alt=""
        src={photo}
        referrerPolicy="no-referrer"
        onError={() => {
          setFailed(photo)
        }}
        onLoad={(event) => {
          // Telegram answers a hidden photo with a 1×1 picture: as good as none.
          if (event.currentTarget.naturalWidth < 2) setFailed(photo)
        }}
        className={`${SIZES[size]} shrink-0 rounded-full bg-secondary-bg object-cover`}
      />
    )
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
