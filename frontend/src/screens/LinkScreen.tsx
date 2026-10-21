import { CircleCheck, CircleSlash, Clock, Undo2, Unlink, UserPlus, Users, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router'

import { fullName, useAnswerLink, useLink, useRemoveLink, type LinkDetail } from '../api/links'
import { errorMessage } from '../i18n/errors'
import { formatDate } from '../i18n/format'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Loading } from '../ui/Loading'
import { Screen } from '../ui/Screen'
import { Problem } from './Problem'

/**
 * One link from the signed-in user's side (FR-1.2, ADR-0012): who, how many mutual
 * links, and what can be done now. A request is answered here, however it came.
 */
export function LinkScreen() {
  const { id = '' } = useParams()
  const link = useLink(id)
  const answer = useAnswerLink()
  const incoming = link.data?.status === 'pending' && link.data.direction === 'incoming'

  const { t } = useI18n()
  useMainButton(
    incoming
      ? {
          text: t('link.accept'),
          busy: answer.isPending,
          onClick: () => {
            answer.mutate(
              { id, answer: 'accept' },
              {
                onSuccess: () => {
                  hapticNotify('success')
                },
                onError: () => {
                  hapticNotify('error')
                },
              },
            )
          },
        }
      : null,
  )

  if (link.isPending)
    return (
      <Screen>
        <Loading />
      </Screen>
    )
  if (link.isError) return <Problem error={link.error} retry={() => void link.refetch()} />
  return <Shown link={link.data} answer={answer} />
}

function Shown({ link, answer }: { link: LinkDetail; answer: ReturnType<typeof useAnswerLink> }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const remove = useRemoveLink()
  const name = fullName(link.person)
  const failure = answer.error ?? remove.error

  const backToLinks = () => void navigate('/links', { replace: true })
  const act = async (question: MessageKey, ok: MessageKey, run: () => Promise<unknown>) => {
    if (!(await confirmAction(t(question), t(ok), { destructive: true }))) return
    try {
      await run()
      backToLinks()
    } catch {
      hapticNotify('error')
    }
  }

  let status: ReactNode
  let action: ReactNode = null
  if (link.status === 'pending' && link.direction === 'incoming') {
    status = <Status icon={<UserPlus className="size-5" />} text={t('link.incoming')} />
    action = (
      <Button
        tone="destructive"
        icon={<X aria-hidden className="size-5" />}
        disabled={answer.isPending}
        onClick={() =>
          void act('link.decline_confirm', 'link.decline', () =>
            answer.mutateAsync({ id: link.id, answer: 'decline' }),
          )
        }
      >
        {t('link.decline')}
      </Button>
    )
  } else if (link.status === 'pending') {
    status = <Status icon={<Clock className="size-5" />} text={t('link.outgoing')} />
    action = (
      <Button
        tone="destructive"
        icon={<Undo2 aria-hidden className="size-5" />}
        disabled={remove.isPending}
        onClick={() =>
          void act('link.withdraw_confirm', 'link.withdraw', () => remove.mutateAsync(link.id))
        }
      >
        {t('link.withdraw')}
      </Button>
    )
  } else if (link.status === 'active' && link.accepted_at) {
    const date = formatDate(locale, link.accepted_at, 'long')
    status = <Status icon={<CircleCheck className="size-5" />} text={t('link.active', { date })} />
    action = (
      <Button
        tone="destructive"
        icon={<Unlink aria-hidden className="size-5" />}
        disabled={remove.isPending}
        onClick={() =>
          void act('link.break_confirm', 'link.break', () => remove.mutateAsync(link.id))
        }
      >
        {t('link.break')}
      </Button>
    )
  } else {
    status = <Status icon={<CircleSlash className="size-5" />} text={t('link.none')} />
  }

  return (
    <Screen>
      <div className="flex flex-col items-center gap-2 px-6 pt-8 text-center">
        <Avatar name={name} size="xl" />
        <h1 className="text-2xl font-semibold break-words">{name}</h1>
        {link.person.username && <p className="text-hint">@{link.person.username}</p>}
        <p className="flex items-center gap-1.5 text-sm text-hint">
          <Users aria-hidden className="size-4" />
          {t('link.mutual', { count: link.mutual_links })}
        </p>
      </div>
      <div className="mx-4 rounded-xl bg-section-bg px-4 py-3">{status}</div>
      {failure && <p className="px-6 text-destructive">{t(errorMessage(failure))}</p>}
      {link.status === 'pending' && link.direction === 'incoming' && (
        <p className="px-6 text-sm text-hint">{t('links.how')}</p>
      )}
      {action && <div className="mx-4">{action}</div>}
    </Screen>
  )
}

function Status({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <p className="flex items-center gap-2 font-medium">
      <span aria-hidden className="text-accent">
        {icon}
      </span>
      {text}
    </p>
  )
}
