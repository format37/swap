import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, done, unwrap } from './client'
import type { components } from './schema'

export type PaymentMethod = components['schemas']['PaymentMethod']
export type NewPaymentMethod = components['schemas']['NewPaymentMethod']

const PAYMENTS = ['payment-methods'] as const

/** The signed-in user's saved payment details, in full: they are theirs (Q-B8). */
export function usePaymentMethods() {
  return useQuery({
    queryKey: PAYMENTS,
    queryFn: () => unwrap(api.GET('/api/v1/payment-methods')),
  })
}

function usePaymentsMutation<Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: PAYMENTS }),
  })
}

export function useAddPaymentMethod() {
  return usePaymentsMutation((body: NewPaymentMethod) =>
    unwrap(api.POST('/api/v1/payment-methods', { body })),
  )
}

export function useDeletePaymentMethod() {
  return usePaymentsMutation((id: string) =>
    done(
      api.DELETE('/api/v1/payment-methods/{method_id}', { params: { path: { method_id: id } } }),
    ),
  )
}
