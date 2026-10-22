import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

import { fullName, type Person as PersonData } from '../api/links'
import { Avatar, type AvatarSize } from './Avatar'

/**
 * A person as Swap shows one (QUESTIONS J4): the photo on the left, and to its right the
 * name with the @username under it. `detail` follows the @username on that quieter line,
 * as in «@nino · с 21 окт.». `heading` makes the name a screen's title.
 */
export function Person({
  person,
  size = 'sm',
  detail,
  heading = false,
}: {
  person: PersonData
  size?: AvatarSize
  detail?: ReactNode
  heading?: boolean
}) {
  const name = fullName(person)
  const handle = person.username ? `@${person.username}` : null
  return (
    <span className="flex min-w-0 flex-1 items-center gap-3">
      <Avatar name={name} photo={person.photo_url} size={size} />
      <span className="min-w-0 flex-1">
        {heading ? (
          <h1 className="truncate text-xl font-semibold">{name}</h1>
        ) : (
          <span className="block truncate">{name}</span>
        )}
        {(handle || detail) && (
          <span className="block truncate text-sm text-hint">
            {handle}
            {handle && detail && ' · '}
            {detail}
          </span>
        )}
      </span>
    </span>
  )
}

/** A person in a list, opening their screen: «Связи», link requests. */
export function PersonRow({
  person,
  detail,
  onClick,
}: {
  person: PersonData
  detail?: ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
    >
      <Person person={person} detail={detail} />
      <ChevronRight aria-hidden className="size-5 shrink-0 text-hint" />
    </button>
  )
}
