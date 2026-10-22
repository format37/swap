import { CircleCheck } from 'lucide-react'

import { useI18n } from '../i18n/useI18n'
import { closeApp, useMainButton } from '../telegram'

/**
 * What is left once the account is deleted (QUESTIONS K2): nothing to do but close. The
 * app asks the api for nothing more, since this launch can no longer sign in.
 */
export function AccountDeleted() {
  const { t } = useI18n()
  useMainButton({ text: t('gone.close'), onClick: closeApp })
  return (
    <main className="screen mx-auto flex max-w-xl flex-col items-center justify-center gap-3 px-8 text-center">
      <CircleCheck aria-hidden className="size-12 text-accent" />
      <h1 className="text-2xl font-semibold">{t('gone.title')}</h1>
      <p className="text-hint">{t('gone.text')}</p>
    </main>
  )
}
