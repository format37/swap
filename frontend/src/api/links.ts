import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, done, unwrap } from './client'
import type { components } from './schema'

export type Link = components['schemas']['Link']
export type LinkDetail = components['schemas']['LinkDetail']
export type Links = components['schemas']['Links']
export type Invite = components['schemas']['Invite']
export type NewInvite = components['schemas']['NewInvite']
export type Person = components['schemas']['Person']

const LINKS = ['links'] as const

export function useLinks() {
  return useQuery({ queryKey: LINKS, queryFn: () => unwrap(api.GET('/api/v1/links')) })
}

export function useLink(id: string) {
  return useQuery({
    queryKey: [...LINKS, id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/links/{link_id}', { params: { path: { link_id: id } } })),
  })
}

/** Every change to links refreshes the tab and any open request screen. */
function useLinksMutation<Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: LINKS }),
  })
}

export function useCreateInvite() {
  return useLinksMutation(() => unwrap(api.POST('/api/v1/links/invites')))
}

export function useRevokeInvite() {
  return useLinksMutation((id: string) =>
    done(api.DELETE('/api/v1/links/invites/{invite_id}', { params: { path: { invite_id: id } } })),
  )
}

export function useAnswerLink() {
  return useLinksMutation(({ id, answer }: { id: string; answer: 'accept' | 'decline' }) => {
    const options = { params: { path: { link_id: id } } }
    return unwrap(
      answer === 'accept'
        ? api.POST('/api/v1/links/{link_id}/accept', options)
        : api.POST('/api/v1/links/{link_id}/decline', options),
    )
  })
}

/** Asks someone to link by their @username; linked at once if they had asked first. */
export function useRequestLink() {
  return useLinksMutation((username: string) =>
    unwrap(api.POST('/api/v1/links/requests', { body: { username } })),
  )
}

/** Hears nothing more of this person's new orders, or hears them again (FR-7.2, K1). */
export function useMuteLink(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (muted: boolean) => {
      const options = { params: { path: { link_id: id } } }
      return unwrap(
        muted
          ? api.PUT('/api/v1/links/{link_id}/mute', options)
          : api.DELETE('/api/v1/links/{link_id}/mute', options),
      )
    },
    onSuccess: (link: LinkDetail) => {
      queryClient.setQueryData([...LINKS, id], link)
    },
  })
}

/** Breaks an active link, or withdraws one's own request. */
export function useRemoveLink() {
  return useLinksMutation((id: string) =>
    done(api.DELETE('/api/v1/links/{link_id}', { params: { path: { link_id: id } } })),
  )
}

export function fullName(person: Pick<Person, 'first_name' | 'last_name'>): string {
  return [person.first_name, person.last_name].filter(Boolean).join(' ')
}
