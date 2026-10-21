import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { Locale } from '../i18n/locale'
import { api, unwrap, type Me } from './client'

const ME = ['me'] as const

export function useMe() {
  return useQuery({ queryKey: ME, queryFn: () => unwrap(api.GET('/api/v1/me')) })
}

/** Saves the language on the server, so the bot speaks it too (ADR-0009). */
export function useSetLocale() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (locale: Locale) => unwrap(api.PATCH('/api/v1/me', { body: { locale } })),
    onSuccess: (me: Me) => {
      queryClient.setQueryData(ME, me)
    },
  })
}
