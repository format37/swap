import type { DealStatus, Leg } from '../api/deals'
import { ALEX, deal, NINO } from '../test/deals'
import { nextFor } from './next'

const asNino = (status: DealStatus) => nextFor(deal({ status, role: 'proposer' }), NINO.id)
const asAlex = (status: DealStatus) => nextFor(deal({ status, role: 'acceptor' }), ALEX.id)

// Leg 1 is Nino's GEL to Alex, leg 2 Alex's RUB to Nino; marks as the api returns them.
function running(marks: { sent?: number[]; received?: number[] }) {
  const legs = deal().legs.map((leg): Leg => ({
    ...leg,
    sent_at:
      marks.sent?.includes(leg.seq) || marks.received?.includes(leg.seq)
        ? '2026-10-22T10:00:00Z'
        : null,
    received_at: marks.received?.includes(leg.seq) ? '2026-10-22T11:00:00Z' : null,
  }))
  return {
    nino: nextFor(deal({ status: 'accepted', role: 'proposer', legs }), NINO.id),
    alex: nextFor(deal({ status: 'accepted', role: 'acceptor', legs }), ALEX.id),
  }
}

it('asks the author to answer a proposal, and the proposer to wait', () => {
  expect(asAlex('proposed')).toMatchObject({
    line: 'deal.status.answer',
    main: 'accept',
    marks: {},
    others: ['decline'],
  })
  expect(asNino('proposed')).toMatchObject({
    line: 'deal.status.wait_answer',
    waitingFor: ALEX,
    others: ['withdraw'],
  })
})

it('gives each side both marks at once, once the deal is accepted (H2)', () => {
  const { nino, alex } = running({})
  // Nino sends leg 1 and gets leg 2; Alex the other way round. Nothing waits on order.
  expect(nino).toMatchObject({
    line: 'deal.status.both',
    marks: { 1: 'sent', 2: 'received' },
    others: ['cancel'],
  })
  expect(nino.leg?.seq).toBe(1)
  expect(alex).toMatchObject({ marks: { 2: 'sent', 1: 'received' }, others: ['cancel'] })
  expect(nino.main).toBeUndefined()
})

it('says what is left as the marks come in', () => {
  // Alex has sent: Nino is told to check, and nobody may cancel alone any more.
  const sent = running({ sent: [2] })
  expect(sent.nino).toMatchObject({ line: 'deal.status.both', others: [] })
  expect(sent.alex).toMatchObject({ line: 'deal.status.wait_send', waitingFor: NINO })
  expect(sent.alex.marks).toEqual({ 1: 'received' })
  // Nino got Alex's RUB but hasn't sent hers.
  const got = running({ received: [2] })
  expect(got.nino).toMatchObject({ line: 'deal.status.send', marks: { 1: 'sent' } })
  expect(got.alex).toMatchObject({ line: 'deal.status.wait_send', marks: { 1: 'received' } })
  // Nino sent too: Alex is asked to check it.
  const both = running({ sent: [1], received: [2] })
  expect(both.alex).toMatchObject({ line: 'deal.status.confirm', marks: { 1: 'received' } })
  expect(both.nino).toMatchObject({ line: 'deal.status.wait_confirm', waitingFor: ALEX })
  expect(both.nino.marks).toEqual({})
})

it('names the end of a deal', () => {
  expect(asNino('settled').line).toBe('deal.status.settled')
  expect(asAlex('cancelled').line).toBe('deal.status.cancelled')
  expect(asNino('expired').line).toBe('deal.status.expired')
  expect(asAlex('disputed')).toMatchObject({ line: 'deal.status.disputed', marks: {} })
})
