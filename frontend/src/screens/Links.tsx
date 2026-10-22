import { AtSign, Link2, Send, Trash2, UserPlus, Users } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import {
  useCreateInvite,
  useLinks,
  useRequestLink,
  useRevokeInvite,
  type Invite,
  type Link,
} from '../api/links'
import { errorMessage } from '../i18n/errors'
import { formatDate } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { EmptyState } from '../ui/EmptyState'
import { Loading } from '../ui/Loading'
import { PersonRow } from '../ui/Person'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Problem } from './Problem'

/** The «Связи» tab: requests, links, sent requests and open invitations (FR-1.3, FR-1.5). */
export function Links() {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const links = useLinks()
  const create = useCreateInvite()

  useMainButton({
    text: t('links.invite'),
    busy: create.isPending,
    onClick: () => {
      create.mutate(undefined, {
        onSuccess: (invite) => void navigate('/links/invite', { state: invite }),
        onError: () => {
          hapticNotify('error')
        },
      })
    },
  })

  if (links.isPending)
    return (
      <Screen tabs>
        <Loading />
      </Screen>
    )
  if (links.isError) return <Problem error={links.error} retry={() => void links.refetch()} />

  const { active, incoming, outgoing, invites } = links.data
  const empty = !active.length && !incoming.length && !outgoing.length && !invites.length

  const row = (link: Link, detail?: string) => (
    <PersonRow
      key={link.id}
      person={link.person}
      detail={detail}
      onClick={() => void navigate(`/links/${link.id}`)}
    />
  )

  return (
    <Screen tabs>
      <h1 className="flex items-center gap-2 px-6 pt-4 text-2xl font-semibold">
        <Users aria-hidden className="size-6 text-accent" />
        {t('links.title')}
      </h1>
      {create.isError && <p className="px-6 text-destructive">{t(errorMessage(create.error))}</p>}
      <UsernameRequest />
      {empty ? (
        <EmptyState
          icon={<UserPlus aria-hidden className="size-12" />}
          title={t('links.empty.title')}
          steps={[t('links.empty.step1'), t('links.empty.step2'), t('links.empty.step3')]}
        />
      ) : (
        <>
          {incoming.length > 0 && (
            <Section title={t('links.requests')}>{incoming.map((link) => row(link))}</Section>
          )}
          {active.length > 0 && (
            <Section title={t('links.active')}>
              {active.map((link) =>
                row(
                  link,
                  link.accepted_at
                    ? t('links.since', { date: formatDate(locale, link.accepted_at) })
                    : undefined,
                ),
              )}
            </Section>
          )}
          {outgoing.length > 0 && (
            <Section title={t('links.sent')}>
              {outgoing.map((link) => row(link, t('links.waiting')))}
            </Section>
          )}
          {invites.length > 0 && (
            <Section title={t('links.invites')}>
              {invites.map((invite) => (
                <InviteRow key={invite.id} invite={invite} />
              ))}
            </Section>
          )}
        </>
      )}
      <p className="px-6 text-sm text-hint">{t('links.how')}</p>
    </Screen>
  )
}

/** An invitation not yet used. Its link can't be shown again (ADR-0012), only revoked. */
function InviteRow({ invite }: { invite: Invite }) {
  const { t, locale } = useI18n()
  const revoke = useRevokeInvite()
  return (
    <div className="flex min-h-12 items-center gap-3 px-4 py-2">
      <Link2 aria-hidden className="size-6 shrink-0 text-accent" />
      <span className="min-w-0 flex-1 truncate">
        {t('links.invite_until', { date: formatDate(locale, invite.expires_at) })}
      </span>
      <button
        type="button"
        aria-label={t('links.revoke')}
        disabled={revoke.isPending}
        onClick={() => {
          void confirmAction(t('links.revoke_confirm'), t('links.revoke'), {
            destructive: true,
          }).then((confirmed) => {
            if (confirmed) revoke.mutate(invite.id)
          })
        }}
        className="flex size-10 items-center justify-center rounded-full text-destructive active:bg-secondary-bg"
      >
        <Trash2 aria-hidden className="size-5" />
      </button>
    </div>
  )
}

/** A request to someone's @username (FR-1.1). An unknown name suggests an invitation. */
function UsernameRequest() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const request = useRequestLink()
  const [username, setUsername] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!username.trim()) return
    request.mutate(username, {
      onSuccess: (link) => void navigate(`/links/${link.id}`),
      onError: () => {
        hapticNotify('error')
      },
    })
  }

  return (
    <>
      <Section title={t('links.by_username')}>
        <form onSubmit={submit} className="flex items-center gap-2 pr-2 pl-4">
          <AtSign aria-hidden className="size-5 shrink-0 text-hint" />
          <input
            value={username}
            onChange={(event) => {
              setUsername(event.target.value)
              request.reset()
            }}
            placeholder={t('links.username_placeholder')}
            aria-label={t('links.by_username')}
            autoCapitalize="none"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="send"
            className="min-w-0 flex-1 bg-transparent py-3 outline-none placeholder:text-hint"
          />
          <button
            type="submit"
            aria-label={t('links.send_request')}
            disabled={!username.trim() || request.isPending}
            className="flex size-10 items-center justify-center rounded-full text-accent active:bg-secondary-bg disabled:text-hint"
          >
            <Send aria-hidden className="size-5" />
          </button>
        </form>
      </Section>
      {request.isError && (
        <p className="px-6 text-sm text-destructive">{t(errorMessage(request.error))}</p>
      )}
    </>
  )
}
