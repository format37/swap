import type { DealStatus } from '../api/deals'
import { ALEX, deal, NINO } from '../test/deals'
import { nextFor } from './next'

const asNino = (status: DealStatus) => nextFor(deal({ status, role: 'proposer' }), NINO.id)
const asAlex = (status: DealStatus) => nextFor(deal({ status, role: 'acceptor' }), ALEX.id)

it('asks the author to answer a proposal, and the proposer to wait', () => {
  expect(asAlex('proposed')).toMatchObject({
    line: 'deal.status.answer',
    main: 'accept',
    others: ['decline'],
  })
  expect(asNino('proposed')).toMatchObject({
    line: 'deal.status.wait_answer',
    waitingFor: ALEX,
    others: ['withdraw'],
  })
})

it('gives each step to the one whose move it is, and has the other wait', () => {
  // Nino sends first (leg 1), Alex confirms; then Alex sends, and Nino confirms.
  expect(asNino('accepted')).toMatchObject({
    line: 'deal.status.send',
    main: 'sent',
    others: ['cancel'],
  })
  expect(asAlex('accepted')).toMatchObject({ line: 'deal.status.wait_send', waitingFor: NINO })
  expect(asAlex('leg1_sent')).toMatchObject({ line: 'deal.status.confirm', main: 'received' })
  expect(asNino('leg1_sent')).toMatchObject({ line: 'deal.status.wait_confirm', waitingFor: ALEX })
  expect(asAlex('leg1_received')).toMatchObject({
    line: 'deal.status.send',
    main: 'sent',
    others: [],
  })
  expect(asNino('leg1_received')).toMatchObject({ line: 'deal.status.wait_send', waitingFor: ALEX })
  expect(asNino('leg2_sent')).toMatchObject({ line: 'deal.status.confirm', main: 'received' })
  expect(asAlex('leg2_sent')).toMatchObject({ line: 'deal.status.wait_confirm', waitingFor: NINO })
  expect(asNino('leg1_received').leg?.seq).toBe(2)
})

it.each<[DealStatus, string]>([
  ['settled', 'deal.status.settled'],
  ['cancelled', 'deal.status.cancelled'],
  ['expired', 'deal.status.expired'],
  ['disputed', 'deal.status.disputed'],
])('leaves nothing to do in %s', (status, line) => {
  for (const next of [asNino(status), asAlex(status)]) {
    expect(next.line).toBe(line)
    expect(next.main).toBeUndefined()
    expect(next.others).toEqual([])
  }
})
