import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, done, unwrap } from './client'
import type { components } from './schema'

export type Order = components['schemas']['Order']
export type OrderDraft = components['schemas']['OrderDraft']
export type PaymentKind = components['schemas']['PaymentKind']
export type FixedRate = components['schemas']['FixedRate']
export type RateSpec = components['schemas']['Want']['rate_spec']
export type Want = components['schemas']['Want']
export type QuoteRequest = components['schemas']['QuoteRequest']
export type MarketQuote = components['schemas']['MarketQuote']

const ORDERS = ['orders'] as const

/**
 * «Открытые мне» (`visible`), «Мои» (`mine`, the open ones), or the finished ones that are
 * mine or that I had a deal on (`history`, QUESTIONS H4). `within` narrows «Открытые мне»
 * to authors at most so many handshakes away; null is the whole network (J2).
 */
export function useOrders(scope: 'visible' | 'mine' | 'history', within: number | null = null) {
  return useQuery({
    queryKey: [...ORDERS, scope, within],
    queryFn: () => unwrap(api.GET('/api/v1/orders', { params: { query: { scope, within } } })),
  })
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: [...ORDERS, 'one', id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/orders/{order_id}', { params: { path: { order_id: id } } })),
  })
}

function useOrdersMutation<Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: ORDERS }),
  })
}

export function usePublishOrder() {
  return useOrdersMutation((draft: OrderDraft) =>
    unwrap(api.POST('/api/v1/orders', { body: draft })),
  )
}

export function useCloseOrder() {
  return useOrdersMutation((id: string) =>
    unwrap(api.POST('/api/v1/orders/{order_id}/close', { params: { path: { order_id: id } } })),
  )
}

/** A closed order, open again as it was (QUESTIONS F7). */
export function useReopenOrder() {
  return useOrdersMutation((id: string) =>
    unwrap(api.POST('/api/v1/orders/{order_id}/reopen', { params: { path: { order_id: id } } })),
  )
}

/** «Больше не повторять»: no more monthly copies of its series (QUESTIONS K7). */
export function useStopRepeating() {
  return useOrdersMutation((id: string) =>
    unwrap(
      api.POST('/api/v1/orders/{order_id}/stop-repeating', { params: { path: { order_id: id } } }),
    ),
  )
}

/** Gone for everyone, its author included; its deals carry on (QUESTIONS F6). */
/** Deletes an order for oneself (QUESTIONS J3, L4), and so the deals that go with it. */
export function useDeleteOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      done(api.DELETE('/api/v1/orders/{order_id}', { params: { path: { order_id: id } } })),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ORDERS }),
        queryClient.invalidateQueries({ queryKey: ['deals'] }),
      ]),
  })
}

/** What orders may give and want; config on the server (FR-2.2). */
export function useAssets() {
  return useQuery({
    queryKey: ['assets'],
    queryFn: () => unwrap(api.GET('/api/v1/assets')),
    staleTime: Infinity,
  })
}

/**
 * The market's rate for 1 `base` in `quote`, to fill the wizard in with (ADR-0020). The
 * api keeps Coinbase's answer for ten minutes; without one, the author types the rate.
 */
export function useMarketRate(base: string, quote: string) {
  return useQuery({
    queryKey: ['market', base, quote],
    queryFn: () => unwrap(api.GET('/api/v1/rates/market', { params: { query: { base, quote } } })),
    enabled: Boolean(base && quote && base !== quote),
    staleTime: 5 * 60_000,
    retry: false,
  })
}

/**
 * A counter-amount from the api, which does all money arithmetic (ADR-0004). Null asks
 * nothing. The last answer stays on screen while the next one is on its way.
 */
export function useQuote(request: QuoteRequest | null) {
  return useQuery({
    queryKey: ['quote', request],
    queryFn: () => unwrap(api.POST('/api/v1/quote', { body: request as QuoteRequest })),
    enabled: request !== null,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })
}
