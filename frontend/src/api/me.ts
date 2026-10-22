import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import type { Locale } from '../i18n/locale'
import { api, done, setLaunchInitData, unwrap, type Me } from './client'
import type { components } from './schema'

export type MeUpdate = components['schemas']['MeUpdate']
export type NotificationKind = components['schemas']['NotificationKind']

const ME = ['me'] as const

export function useMe() {
  return useQuery({ queryKey: ME, queryFn: () => unwrap(api.GET('/api/v1/me')) })
}

/** Changes what is sent of the settings, and keeps the answer as the new /me. */
export function useUpdateMe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (changes: MeUpdate) => unwrap(api.PATCH('/api/v1/me', { body: changes })),
    onSuccess: (me: Me) => {
      queryClient.setQueryData(ME, me)
    },
  })
}

/** Every finished deal and order deleted for oneself at once (QUESTIONS K2). */
export function useDeleteHistory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/v1/me/history')),
    onSettled: () => queryClient.invalidateQueries(),
  })
}

/**
 * The account, gone (Q-B10). This launch's initData is forgotten at once: signing in
 * again with it would quietly start a new account.
 */
export function useDeleteAccount() {
  return useMutation({
    mutationFn: () => done(api.DELETE('/api/v1/me')),
    onSuccess: () => {
      setLaunchInitData(undefined)
    },
  })
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
