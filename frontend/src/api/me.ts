import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

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

/**
 * The device's time zone, sent once, when the server doesn't have one yet: order and
 * deal dates are calendar dates in it (Q-B17). The profile will let people change it.
 */
export function useDeviceTimeZone(me: Me | undefined) {
  const queryClient = useQueryClient()
  const missing = me !== undefined && me.tz === null
  useEffect(() => {
    if (!missing) return
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    unwrap(api.PATCH('/api/v1/me', { body: { tz } }))
      .then((updated) => {
        queryClient.setQueryData(ME, updated)
      })
      .catch((error: unknown) => {
        // A zone the server doesn't know leaves the user on UTC; the app works on.
        console.warn('time zone not saved', error)
      })
  }, [missing, queryClient])
}
