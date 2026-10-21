import { Check, Copy, Trash2, TriangleAlert, WalletCards } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router'

import { useDeletePaymentMethod, usePaymentMethods } from '../api/payments'
import { errorMessage } from '../i18n/errors'
import { useI18n } from '../i18n/useI18n'
import { Asset } from '../money/Asset'
import { KINDS } from '../money/kinds'
import { confirmAction, copyText, hapticNotify } from '../telegram'
import { Button } from '../ui/Button'
import { Loading } from '../ui/Loading'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/** One saved entry, in full for its owner (Q-B8): copy it, or delete it. */
export function PaymentMethodCard() {
  const { id = '' } = useParams()
  const { t } = useI18n()
  const navigate = useNavigate()
  const methods = usePaymentMethods()
  const remove = useDeletePaymentMethod()
  const [copied, setCopied] = useState(false)

  if (methods.isPending)
    return (
      <Screen>
        <Loading />
      </Screen>
    )
  const method = methods.data?.find((entry) => entry.id === id)
  if (!method) return <Navigate to="/profile" replace />
  const kind = KINDS.find((entry) => entry.kind === method.kind)
  const Icon = kind?.icon ?? WalletCards
  const full = method.details?.full

  return (
    <Screen>
      <header className="flex flex-col items-center gap-2 px-6 pt-8 text-center">
        <Icon aria-hidden className="size-12 text-accent" />
        <h1 className="text-2xl font-semibold break-words">{method.title}</h1>
        <p className="flex items-center gap-1.5 text-hint">
          <Asset code={method.asset} />
          {kind && <span>· {t(kind.label)}</span>}
        </p>
      </header>
      <Section>
        <p className="px-4 py-3 break-words whitespace-pre-line select-all">
          {full ?? t('details.no_text')}
        </p>
      </Section>
      {method.kind === 'crypto' && (
        <p className="flex items-start gap-2 px-6 text-sm text-hint">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t('details.check_network')}
        </p>
      )}
      {full && (
        <div className="mx-4">
          <Button
            icon={
              copied ? (
                <Check aria-hidden className="size-5" />
              ) : (
                <Copy aria-hidden className="size-5" />
              )
            }
            onClick={() => {
              void copyText(full).then((ok) => {
                hapticNotify(ok ? 'success' : 'error')
                setCopied(ok)
              })
            }}
          >
            {copied ? t('invite.copied') : t('details.copy')}
          </Button>
        </div>
      )}
      <div className="mx-4">
        <Button
          tone="destructive"
          icon={<Trash2 aria-hidden className="size-5" />}
          disabled={remove.isPending}
          onClick={() => {
            void confirmAction(t('details.delete_confirm'), t('details.delete'), {
              destructive: true,
            }).then((confirmed) => {
              if (!confirmed) return
              remove.mutate(method.id, {
                onSuccess: () => {
                  hapticNotify('success')
                  void navigate(-1)
                },
              })
            })
          }}
        >
          {t('details.delete')}
        </Button>
      </div>
      {remove.isError && <p className="px-6 text-destructive">{t(errorMessage(remove.error))}</p>}
    </Screen>
  )
}
