import { ArrowLeftRight, ChevronRight } from 'lucide-react'

import type { Deal } from '../api/deals'
import { fullName } from '../api/links'
import { useI18n } from '../i18n/useI18n'
import { Money } from '../money/Asset'
import { Avatar } from '../ui/Avatar'
import { statusText } from './words'

/** A deal in a list: the other side, both amounts, and what happens next. */
export function DealRow({ deal, me, onOpen }: { deal: Deal; me: string; onOpen: () => void }) {
  const i18n = useI18n()
  const other = deal.role === 'proposer' ? deal.acceptor : deal.proposer
  const [first, second] = deal.legs
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
    >
      <Avatar name={fullName(other)} photo={other.photo_url} size="sm" />
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
          {first && <Money locale={i18n.locale} amount={first.amount} code={first.currency} />}
          <ArrowLeftRight aria-hidden className="size-4 text-hint" />
          {second && <Money locale={i18n.locale} amount={second.amount} code={second.currency} />}
        </span>
        <span className="block truncate text-sm text-hint">
          {fullName(other)} · {statusText(i18n, deal, me)}
        </span>
      </span>
      <ChevronRight aria-hidden className="size-5 shrink-0 text-hint" />
    </button>
  )
}
