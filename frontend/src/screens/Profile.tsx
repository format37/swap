import { Bell, Eraser, Globe, UserX } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { useDeleteAccount, useDeleteHistory } from '../api/me'
import { errorMessage } from '../i18n/errors'
import { useI18n } from '../i18n/useI18n'
import { notificationsState } from '../settings/notifications'
import { LANGUAGE_NAMES } from '../i18n/locale'
import { confirmAction, hapticNotify } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Cell } from '../ui/Cell'
import { Score } from '../ui/Person'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * The profile behind Home's avatar (Q-B14), which holds the settings (QUESTIONS K1): who I
 * am, notifications, the language, and deleting my history or my account (K2). No payment
 * details: the parties settle where to pay among themselves (QUESTIONS G3).
 */
export function Profile({ me, onGone }: { me: Me; onGone?: () => void }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const history = useDeleteHistory()
  const account = useDeleteAccount()
  const name = [me.first_name, me.last_name].filter(Boolean).join(' ')
  const failure = history.error ?? account.error

  return (
    <Screen>
      <header className="flex flex-col items-center gap-2 px-6 pt-8 text-center">
        <Avatar name={name} photo={me.photo_url} size="xl" />
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">{name}</h1>
          <Score count={me.score} explained />
        </div>
        {me.username && <p className="text-hint">@{me.username}</p>}
      </header>

      <Section title={t('home.settings')}>
        <Cell
          icon={<Bell aria-hidden className="size-6" />}
          label={t('settings.notifications')}
          detail={t(notificationsState(me))}
          opens
          onClick={() => void navigate('/settings/notifications')}
        />
        <Cell
          icon={<Globe aria-hidden className="size-6" />}
          label={t('settings.language')}
          detail={LANGUAGE_NAMES[locale]}
          opens
          onClick={() => void navigate('/language')}
        />
      </Section>

      {/* Everything finished, for oneself; what runs stays (QUESTIONS K2, J3). */}
      <Section title={t('settings.data')}>
        <Button
          tone="destructive"
          icon={<Eraser aria-hidden className="size-5" />}
          disabled={history.isPending}
          onClick={() => {
            void confirmAction(t('settings.delete_history_confirm'), t('settings.delete_history'), {
              destructive: true,
            }).then((confirmed) => {
              if (!confirmed) return
              history.mutate(undefined, {
                onSuccess: () => {
                  hapticNotify('success')
                },
                onError: () => {
                  hapticNotify('error')
                },
              })
            })
          }}
        >
          {t('settings.delete_history')}
        </Button>
        <Button
          tone="destructive"
          icon={<UserX aria-hidden className="size-5" />}
          disabled={account.isPending}
          onClick={() => {
            void confirmAction(t('settings.delete_account_confirm'), t('settings.delete_account'), {
              destructive: true,
            }).then((confirmed) => {
              if (!confirmed) return
              account.mutate(undefined, {
                onSuccess: () => {
                  hapticNotify('success')
                  onGone?.()
                },
                onError: () => {
                  hapticNotify('error')
                },
              })
            })
          }}
        >
          {t('settings.delete_account')}
        </Button>
      </Section>
      {history.data && (
        <p className="px-6 text-sm text-hint">{t('settings.history_deleted', history.data)}</p>
      )}
      {failure && <p className="px-6 text-destructive">{t(errorMessage(failure))}</p>}
    </Screen>
  )
}
