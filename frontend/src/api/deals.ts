import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from './client'
import type { components } from './schema'

export type Deal = components['schemas']['Deal']
export type Leg = components['schemas']['Leg']
export type DealEvent = components['schemas']['DealEvent']
export type Proposal = components['schemas']['Proposal']
export type DealStatus = components['schemas']['DealStatus']

const DEALS = ['deals'] as const

/** My open deals, or closed ones; on one order, when it is named. */
export function useDeals(scope: 'active' | 'history' = 'active', orderId?: string) {
  return useQuery({
    queryKey: [...DEALS, scope, orderId ?? null],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/deals', {
          params: { query: { scope, ...(orderId ? { order_id: orderId } : {}) } },
        }),
      ),
  })
}

// Nobody moves a deal once it is over.
const FINAL: DealStatus[] = ['settled', 'cancelled', 'expired']

export function useDeal(id: string) {
  return useQuery({
    queryKey: [...DEALS, 'one', id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/deals/{deal_id}', { params: { path: { deal_id: id } } })),
    // An open card shows the other side's step within seconds: two people handing over
    // cash both have it open.
    refetchInterval: (query) =>
      query.state.data && !FINAL.includes(query.state.data.status) ? 10_000 : false,
  })
}

/** A change to a deal can change its order's remainder too, so both refresh. */
function useDealsMutation<Variables>(mutationFn: (variables: Variables) => Promise<Deal>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: DEALS }),
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
      ]),
  })
}

export function usePropose(orderId: string) {
  return useDealsMutation((proposal: Proposal) =>
    unwrap(
      api.POST('/api/v1/orders/{order_id}/deals', {
        params: { path: { order_id: orderId } },
        body: proposal,
      }),
    ),
  )
}

export function useAccept(dealId: string) {
  return useDealsMutation((receiveWith: string | null) =>
    unwrap(
      api.POST('/api/v1/deals/{deal_id}/accept', {
        params: { path: { deal_id: dealId } },
        body: { receive_with: receiveWith },
      }),
    ),
  )
}

/** The state machine's steps that take no body (ADR-0018). */
export type Step =
  { kind: 'decline' | 'withdraw' | 'cancel' } | { kind: 'sent' | 'received'; seq: number }

export function useStep(dealId: string) {
  return useDealsMutation((step: Step) => {
    const deal = { deal_id: dealId }
    switch (step.kind) {
      case 'decline':
        return unwrap(api.POST('/api/v1/deals/{deal_id}/decline', { params: { path: deal } }))
      case 'withdraw':
        return unwrap(api.POST('/api/v1/deals/{deal_id}/withdraw', { params: { path: deal } }))
      case 'cancel':
        return unwrap(api.POST('/api/v1/deals/{deal_id}/cancel', { params: { path: deal } }))
      case 'sent':
        return unwrap(
          api.POST('/api/v1/deals/{deal_id}/legs/{seq}/sent', {
            params: { path: { ...deal, seq: step.seq } },
          }),
        )
      case 'received':
        return unwrap(
          api.POST('/api/v1/deals/{deal_id}/legs/{seq}/received', {
            params: { path: { ...deal, seq: step.seq } },
          }),
        )
    }
  })
}
