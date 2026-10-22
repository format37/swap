import { useAcceptTerms } from '../api/me'
import { errorMessage } from '../i18n/errors'
import { useI18n } from '../i18n/useI18n'
import { privacyUrl } from '../settings/about'
import { hapticNotify, openPage, useMainButton } from '../telegram'
import { FormError } from '../ui/FormError'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * The agreement, shown once at the first launch with «Принимаю» (Q-B15, QUESTIONS K3), and
 * again whenever its text changes. The full text is the public page.
 */
export function Terms() {
  const { t } = useI18n()
  const accept = useAcceptTerms()
  useMainButton({
    text: t('terms.accept'),
    busy: accept.isPending,
    onClick: () => {
      accept.mutate(undefined, {
        onSuccess: () => {
          hapticNotify('success')
        },
        onError: () => {
          hapticNotify('error')
        },
      })
    },
  })
  return (
    <Screen>
      <header className="flex flex-col items-center gap-3 px-6 pt-8 text-center">
        <img src="/icon.svg" alt="" width={56} height={56} />
        <h1 className="text-2xl font-semibold">{t('terms.title')}</h1>
      </header>
      <Section>
        <div className="flex flex-col gap-3 px-4 py-4">
          <p>{t('terms.what')}</p>
          <p>{t('terms.who')}</p>
          <p>{t('terms.data')}</p>
        </div>
      </Section>
      <button
        type="button"
        onClick={() => {
          openPage(privacyUrl())
        }}
        className="mx-6 text-left text-link underline"
      >
        {t('terms.privacy')}
      </button>
      <FormError>{accept.isError ? t(errorMessage(accept.error)) : null}</FormError>
    </Screen>
  )
}
