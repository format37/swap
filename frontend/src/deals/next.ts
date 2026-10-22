import type { Deal, Leg } from '../api/deals'
import type { MessageKey } from '../i18n/ru'

/** A mark the viewer may make on one transfer: they sent it, or they got it. */
export type Mark = 'sent' | 'received'

/** What the deal's status line says, and what the viewer may do now (§11). */
export interface Next {
  /** The status in words: what the viewer does next, or who they wait for. */
  line: MessageKey
  /** The leg the line is about, if any: its amount goes into the words. */
  leg?: Leg
  /** The other side, by name, when the viewer waits for them. */
  waitingFor?: Deal['proposer']
  /** The main action, for Telegram's MainButton: answering a proposal. */
  main?: 'accept'
  /** The mark each transfer's card offers the viewer, by its seq: both at once (H2). */
  marks: Partial<Record<number, Mark>>
  /** Actions on the page. */
  others: ('decline' | 'withdraw' | 'cancel')[]
}

/**
 * The status line answers «what do I do next?», not the state's name (§11). Once a deal
 * is accepted both transfers run at once (QUESTIONS H2): each side marks «Отправил» on
 * what they pay and «Получил» on what they get, in any order.
 */
export function nextFor(deal: Deal, me: string): Next {
  const other = deal.role === 'proposer' ? deal.acceptor : deal.proposer
  switch (deal.status) {
    case 'proposed':
      return deal.role === 'acceptor'
        ? { line: 'deal.status.answer', main: 'accept', marks: {}, others: ['decline'] }
        : { line: 'deal.status.wait_answer', waitingFor: other, marks: {}, others: ['withdraw'] }
    case 'accepted': {
      const mine = deal.legs.find((leg) => leg.payer.id === me)
      const theirs = deal.legs.find((leg) => leg.payee.id === me)
      const toSend = mine && !mine.sent_at ? mine : undefined
      const toGet = theirs && !theirs.received_at ? theirs : undefined
      const marks: Next['marks'] = {}
      if (toSend) marks[toSend.seq] = 'sent'
      if (toGet) marks[toGet.seq] = 'received'
      // Alone, a cancel only goes while nothing has moved (FR-4.5).
      const moved = deal.legs.some((leg) => leg.sent_at || leg.received_at)
      const others: Next['others'] = moved ? [] : ['cancel']
      if (toSend && toGet) return { line: 'deal.status.both', leg: toSend, marks, others }
      if (toSend) return { line: 'deal.status.send', leg: toSend, marks, others }
      if (toGet)
        return toGet.sent_at
          ? { line: 'deal.status.confirm', leg: toGet, marks, others }
          : { line: 'deal.status.wait_send', leg: toGet, waitingFor: other, marks, others }
      return { line: 'deal.status.wait_confirm', leg: mine, waitingFor: other, marks, others }
    }
    case 'disputed':
      return { line: 'deal.status.disputed', marks: {}, others: [] }
    case 'settled':
      return { line: 'deal.status.settled', marks: {}, others: [] }
    case 'cancelled':
      return { line: 'deal.status.cancelled', marks: {}, others: [] }
    case 'expired':
      return { line: 'deal.status.expired', marks: {}, others: [] }
  }
}
