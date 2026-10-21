import { TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { useAssets, type PaymentKind } from '../api/orders'
import { useAddPaymentMethod } from '../api/payments'
import { errorMessage } from '../i18n/errors'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { KINDS } from '../money/kinds'
import { assetText } from '../money/looks'
import { hapticNotify, hapticSelect, useMainButton } from '../telegram'
import { Chip } from '../ui/Chip'
import { CONTROL, Field } from '../ui/Field'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

// Whoever pays needs somewhere to send it; the api says the same (payment.text_required).
const TEXT_REQUIRED: PaymentKind[] = ['card', 'phone', 'bank', 'crypto']

/** «Новые реквизиты»: an asset, a way, a name in the clear, and the text, sealed (ADR-0010). */
export function PaymentMethodForm() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const assets = useAssets()
  const add = useAddPaymentMethod()
  const [asset, setAsset] = useState('')
  const [kind, setKind] = useState<PaymentKind>('card')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [shown, setShown] = useState<MessageKey | null>(null)

  const problem: MessageKey | null = !asset
    ? 'wizard.error.choose'
    : !title.trim()
      ? 'error.details_title'
      : TEXT_REQUIRED.includes(kind) && !text.trim()
        ? 'error.payment_text_required'
        : null

  useMainButton({
    text: t('details.save'),
    busy: add.isPending,
    onClick: () => {
      if (problem) {
        setShown(problem)
        hapticNotify('error')
        return
      }
      add.mutate(
        { asset, kind, title: title.trim(), text: text.trim() },
        {
          onSuccess: () => {
            hapticNotify('success')
            void navigate(-1)
          },
          onError: () => {
            hapticNotify('error')
          },
        },
      )
    },
  })

  return (
    <Screen>
      <h1 className="px-6 pt-4 text-2xl font-semibold">{t('details.new')}</h1>
      <Section>
        <Field label={t('wizard.currency')}>
          <select
            className={CONTROL}
            value={asset}
            onChange={(event) => {
              hapticSelect()
              setShown(null)
              setAsset(event.target.value)
            }}
          >
            <option value="" disabled>
              {t('wizard.choose')}
            </option>
            {(assets.data ?? []).map((code) => (
              <option key={code} value={code}>
                {assetText(code)}
              </option>
            ))}
          </select>
        </Field>
      </Section>
      <Section title={t('details.kind')}>
        <div role="radiogroup" className="flex flex-wrap gap-2 p-3">
          {KINDS.map(({ kind: option, icon, label }) => (
            <Chip
              key={option}
              icon={icon}
              label={t(label)}
              selected={kind === option}
              onToggle={() => {
                hapticSelect()
                setShown(null)
                setKind(option)
              }}
            />
          ))}
        </div>
      </Section>
      <Section title={t('details.title')}>
        <input
          aria-label={t('details.title')}
          className="block w-full bg-transparent px-4 py-3 outline-none placeholder:text-hint"
          maxLength={60}
          placeholder={t('details.title_hint')}
          value={title}
          onChange={(event) => {
            setShown(null)
            setTitle(event.target.value)
          }}
        />
      </Section>
      <Section title={t('details.text')}>
        <textarea
          aria-label={t('details.text')}
          className="block min-h-28 w-full resize-none bg-transparent px-4 py-3 outline-none placeholder:text-hint"
          maxLength={500}
          autoCapitalize="none"
          spellCheck={false}
          placeholder={t(`details.text_hint.${kind}`)}
          value={text}
          onChange={(event) => {
            setShown(null)
            setText(event.target.value)
          }}
        />
      </Section>
      {kind === 'crypto' && (
        <p className="flex items-start gap-2 px-6 text-sm text-hint">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t('details.check_network')}
        </p>
      )}
      {shown && <p className="px-6 text-destructive">{t(shown)}</p>}
      {add.isError && <p className="px-6 text-destructive">{t(errorMessage(add.error))}</p>}
    </Screen>
  )
}
