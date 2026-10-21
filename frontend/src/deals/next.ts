import type { Deal, Leg } from '../api/deals'
import type { MessageKey } from '../i18n/ru'

/** What the deal's status line says, and what the viewer may do now (§11). */
export interface Next {
  /** The status in words: what the viewer does next, or who they wait for. */
  line: MessageKey
  /** The leg the line is about, if any: its amount goes into the words. */
  leg?: Leg
  /** The other side, by name, when the viewer waits for them. */
  waitingFor?: Deal['proposer']
  /** The main action that is the viewer's now, for Telegram's MainButton. */
  main?: 'accept' | 'sent' | 'received'
  /** Actions on the page. */
  others: ('decline' | 'withdraw' | 'cancel')[]
}

const SENDING = { accepted: 1, leg1_received: 2 } as const
const CONFIRMING = { leg1_sent: 1, leg2_sent: 2 } as const

/**
 * The status line answers «what do I do next?», not the state's name (§11): «Ваш ход:
 * отправьте 1 712,33 ₾ GEL» or «Ждём подтверждения получения — Alex».
 */
export function nextFor(deal: Deal, me: string): Next {
  const other = deal.role === 'proposer' ? deal.acceptor : deal.proposer
  switch (deal.status) {
    case 'proposed':
      return deal.role === 'acceptor'
        ? { line: 'deal.status.answer', main: 'accept', others: ['decline'] }
        : { line: 'deal.status.wait_answer', waitingFor: other, others: ['withdraw'] }
    case 'accepted':
    case 'leg1_received': {
      const leg = deal.legs.find((l) => l.seq === SENDING[deal.status as keyof typeof SENDING])
      const others: Next['others'] = deal.status === 'accepted' ? ['cancel'] : []
      if (!leg) return { line: 'deal.status.wait_send', others }
      return leg.payer.id === me
        ? { line: 'deal.status.send', leg, main: 'sent', others }
        : { line: 'deal.status.wait_send', leg, waitingFor: leg.payer, others }
    }
    case 'leg1_sent':
    case 'leg2_sent': {
      const leg = deal.legs.find(
        (l) => l.seq === CONFIRMING[deal.status as keyof typeof CONFIRMING],
      )
      if (!leg) return { line: 'deal.status.wait_confirm', others: [] }
      return leg.payee.id === me
        ? { line: 'deal.status.confirm', leg, main: 'received', others: [] }
        : { line: 'deal.status.wait_confirm', leg, waitingFor: leg.payee, others: [] }
    }
    case 'disputed':
      return { line: 'deal.status.disputed', others: [] }
    case 'settled':
      return { line: 'deal.status.settled', others: [] }
    case 'cancelled':
      return { line: 'deal.status.cancelled', others: [] }
    case 'expired':
      return { line: 'deal.status.expired', others: [] }
  }
}
