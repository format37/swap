import { ChevronRight, Handshake } from 'lucide-react'
import type { ReactNode } from 'react'

import { fullName, type Person as PersonData } from '../api/links'
import { useI18n } from '../i18n/useI18n'
import { explain } from '../telegram'
import { Avatar, type AvatarSize } from './Avatar'

/**
 * A person's score: how many different people they settled a deal with (QUESTIONS J5,
 * ADR-0029). A tap explains it, unless it sits in a row that is itself a button.
 */
export function Score({ count, explained = false }: { count: number; explained?: boolean }) {
  const { t } = useI18n()
  const look =
    'inline-flex shrink-0 items-center gap-0.5 rounded-full bg-secondary-bg px-1.5 py-0.5 text-xs font-medium text-hint'
  const content = (
    <>
      <Handshake aria-hidden className="size-3.5" />
      {count}
    </>
  )
  if (!explained)
    return (
      <span role="img" aria-label={t('score.label', { count })} className={look}>
        {content}
      </span>
    )
  return (
    <button
      type="button"
      aria-label={t('score.label', { count })}
      onClick={() => void explain(t('score.about', { count }))}
      className={`${look} active:opacity-70`}
    >
      {content}
    </button>
  )
}

/**
 * A person as Swap shows one (QUESTIONS J4): the photo on the left, and to its right the
 * name with the score beside it and the @username under it. `detail` follows the
 * @username on that quieter line, as in «@nino · с 21 окт.». `heading` makes the name a
 * screen's title, whose score explains itself on a tap.
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
        <span className="flex min-w-0 items-center gap-1.5">
          {heading ? (
            <h1 className="truncate text-xl font-semibold">{name}</h1>
          ) : (
            <span className="truncate">{name}</span>
          )}
          <Score count={person.score} explained={heading} />
        </span>
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
