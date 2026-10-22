import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from './client'
import type { components } from './schema'

export type Order = components['schemas']['Order']
export type OrderDraft = components['schemas']['OrderDraft']
export type PaymentKind = components['schemas']['PaymentKind']
export type FixedRate = components['schemas']['FixedRate']
export type QuoteRequest = components['schemas']['QuoteRequest']
export type MarketQuote = components['schemas']['MarketQuote']

const ORDERS = ['orders'] as const

/** «Открытые мне» (`visible`) or «Мои» (`mine`). */
export function useOrders(scope: 'visible' | 'mine') {
  return useQuery({
    queryKey: [...ORDERS, scope],
    queryFn: () => unwrap(api.GET('/api/v1/orders', { params: { query: { scope } } })),
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
