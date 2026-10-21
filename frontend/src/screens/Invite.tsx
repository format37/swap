import { Check, Copy, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router'

import type { NewInvite } from '../api/links'
import { formatDate } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { copyText, hapticNotify, shareLink, useMainButton } from '../telegram'
import { Button } from '../ui/Button'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

function isNewInvite(value: unknown): value is NewInvite {
  return typeof value === 'object' && value !== null && 'url' in value && 'expires_at' in value
}

/**
 * A fresh invitation, shown once: only its hash is kept, so this is the one chance to
 * share it (ADR-0012). The main action is Telegram's share sheet.
 */
export function Invite() {
  const state: unknown = useLocation().state
  if (!isNewInvite(state)) return <Navigate to="/links" replace />
  return <Shown invite={state} />
}

function Shown({ invite }: { invite: NewInvite }) {
  const { t, locale } = useI18n()
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => {
      setCopied(false)
    }, 2000)
    return () => {
      clearTimeout(timer)
    }
  }, [copied])

  const copy = () => {
    void copyText(invite.url).then((ok) => {
      hapticNotify(ok ? 'success' : 'error')
      setCopied(ok)
    })
  }

  useMainButton({
    text: t('invite.share'),
    onClick: () => {
      if (!shareLink(invite.url, t('invite.share_text'))) copy()
    },
  })

  return (
    <Screen>
      <div className="flex flex-col items-center gap-3 px-6 pt-8 text-center">
        <UserPlus aria-hidden className="size-12 text-accent" />
        <h1 className="text-2xl font-semibold">{t('invite.title')}</h1>
        <p className="text-hint">
          {t('invite.text', { date: formatDate(locale, invite.expires_at, 'long') })}
        </p>
      </div>
      <Section>
        <p className="px-4 py-3 font-mono text-sm break-all select-all">{invite.url}</p>
      </Section>
      <div className="mx-4">
        <Button
          icon={
            copied ? (
              <Check aria-hidden className="size-5" />
            ) : (
              <Copy aria-hidden className="size-5" />
            )
          }
          onClick={copy}
        >
          {copied ? t('invite.copied') : t('invite.copy')}
        </Button>
      </div>
    </Screen>
  )
}
