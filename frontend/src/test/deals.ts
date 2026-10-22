import type { Deal, Leg } from '../api/deals'

export const ALEX = {
  id: 'a0000000-0000-4000-8000-000000000001',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
}
export const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
}
export const DEAL_ID = 'f0000000-0000-4000-8000-000000000001'

function leg(changes: Partial<Leg>): Leg {
  return {
    seq: 1,
    payer: NINO,
    payee: ALEX,
    currency: 'GEL',
    country: 'GE',
    amount: '1712.33',
    method: 'cash',
    due_date: '2026-10-26',
    sent_at: null,
    received_at: null,
    ...changes,
  }
}

/** Nino's proposal on Alex's order: GEL cash to Alex first, then RUB to Nino by card. */
export function deal(changes: Partial<Deal> = {}): Deal {
  return {
    id: DEAL_ID,
    order_id: 'd0000000-0000-4000-8000-000000000001',
    status: 'proposed',
    role: 'proposer',
    proposer: NINO,
    acceptor: ALEX,
    rate: { base: 'GEL', quote: 'RUB', value: '29.20' },
    whole: false,
    expires_at: '2026-10-24T10:00:00Z',
    accepted_at: null,
    closed_at: null,
    created_at: '2026-10-22T10:00:00Z',
    cancel_requested_by: null,
    disputed_by: null,
    dispute_note: null,
    resolution: null,
    resolution_by: null,
    note: null,
    legs: [
      leg({}),
      leg({
        seq: 2,
        payer: ALEX,
        payee: NINO,
        currency: 'RUB',
        country: 'RU',
        amount: '50000.00',
        method: 'bank',
        due_date: '2026-10-28',
      }),
    ],
    events: [{ type: 'proposed', actor_id: NINO.id, at: '2026-10-22T10:00:00Z', to: 'proposed' }],
    ...changes,
  }
}
