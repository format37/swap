import { ArrowLeftRight, Plus, X } from 'lucide-react'
import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { fullName, useLinks } from '../api/links'
import { useAssets, usePublishOrder, useQuote, type QuoteRequest } from '../api/orders'
import { useBackOverride } from '../back'
import { sortedCountries } from '../i18n/countries'
import { errorMessage } from '../i18n/errors'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { assetText, look } from '../money/looks'
import { parseAmount, parseRate } from '../money/format'
import { KINDS } from '../money/kinds'
import {
  emptyForm,
  giveProblem,
  isoDate,
  newWant,
  quoteOf,
  toDraft,
  wantProblem,
  whoProblem,
  type OrderForm,
  type WantForm,
} from '../orders/form'
import { hapticNotify, hapticSelect, useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Chip } from '../ui/Chip'
import { Choice } from '../ui/Choice'
import { CONTROL, Field } from '../ui/Field'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Switch } from '../ui/Switch'
import { useDebounced } from '../useDebounced'

type Step = 1 | 2 | 3
const MAX_WANTS = 3

/**
 * «Новая заявка»: what I give, what I want, who sees it (FR-2.1). The state stays here
 * until «Опубликовать»; there are no server drafts (Q-B17). BackButton steps back through
 * the steps, then leaves.
 */
export function NewOrder() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const today = useMemo(() => isoDate(new Date()), [])
  const [form, setForm] = useState<OrderForm>(() => emptyForm(today))
  const [step, setStep] = useState<Step>(1)
  const [shown, setShown] = useState<MessageKey | null>(null)
  const publish = usePublishOrder()

  const change = useCallback((changes: Changes) => {
    setShown(null)
    setForm((current) => ({
      ...current,
      ...(typeof changes === 'function' ? changes(current) : changes),
    }))
  }, [])

  const stepBack = useMemo(
    () =>
      step > 1
        ? () => {
            setShown(null)
            setStep((step - 1) as Step)
          }
        : null,
    [step],
  )
  useBackOverride(stepBack)

  const problem =
    step === 1 ? giveProblem(form, today) : step === 2 ? wantProblem(form) : whoProblem(form)
  useMainButton({
    text: t(step === 3 ? 'wizard.publish' : 'wizard.next'),
    busy: publish.isPending,
    onClick: () => {
      if (problem) {
        setShown(problem)
        hapticNotify('error')
        return
      }
      if (step < 3) {
        setStep((step + 1) as Step)
        window.scrollTo(0, 0)
        return
      }
      publish.mutate(toDraft(form), {
        onSuccess: (order) => {
          hapticNotify('success')
          // The wizard leaves history: BackButton on the new card leads Home.
          void navigate(`/orders/${order.id}`, { replace: true })
        },
        onError: () => {
          hapticNotify('error')
        },
      })
    },
  })

  return (
    <Screen>
      <header className="px-6 pt-4">
        <p className="text-sm text-hint">{t('wizard.step', { n: step })}</p>
        <h1 className="text-2xl font-semibold">{t('home.new_order')}</h1>
      </header>
      {step === 1 && <GiveStep form={form} today={today} change={change} />}
      {step === 2 && <WantStep form={form} change={change} />}
      {step === 3 && <WhoStep form={form} change={change} />}
      {shown && <p className="px-6 text-destructive">{t(shown)}</p>}
      {publish.isError && <p className="px-6 text-destructive">{t(errorMessage(publish.error))}</p>}
    </Screen>
  )
}

/** What a step changes: plain values, or values worked out from the form as it is now. */
type Changes = Partial<OrderForm> | ((current: OrderForm) => Partial<OrderForm>)

interface StepProps {
  form: OrderForm
  change: (changes: Changes) => void
}

function CurrencySelect({
  value,
  onChange,
  label,
}: {
  value: string
  onChange: (code: string) => void
  label: string
}) {
  const { t } = useI18n()
  const assets = useAssets()
  return (
    <Field label={label}>
      <select
        className={CONTROL}
        value={value}
        onChange={(event) => {
          hapticSelect()
          onChange(event.target.value)
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
  )
}

function CountrySelect({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  const { t, locale } = useI18n()
  const countries = useMemo(() => sortedCountries(locale), [locale])
  return (
    <Field label={t('wizard.country')}>
      <select
        className={CONTROL}
        value={value}
        onChange={(event) => {
          hapticSelect()
          onChange(event.target.value)
        }}
      >
        <option value="" disabled>
          {t('wizard.choose')}
        </option>
        {countries.map(({ code, name }) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>
    </Field>
  )
}

function AmountInput({
  value,
  onChange,
  currency,
  label,
}: {
  value: string
  onChange: (text: string) => void
  currency: string
  label: string
}) {
  return (
    <Field label={label}>
      <span className="flex min-w-0 items-center gap-1.5">
        <input
          className={`${CONTROL} w-full`}
          inputMode="decimal"
          autoComplete="off"
          placeholder="0"
          value={value}
          onChange={(event) => {
            onChange(event.target.value)
          }}
        />
        {currency && (
          <span className="shrink-0 text-hint">
            <Asset code={currency} />
          </span>
        )}
      </span>
    </Field>
  )
}

/** Step 1, «Отдаю»: currency, country, amount, how, when. */
function GiveStep({ form, today, change }: StepProps & { today: string }) {
  const { t } = useI18n()
  return (
    <>
      <Section title={t('wizard.give.title')}>
        <CurrencySelect
          label={t('wizard.currency')}
          value={form.giveCurrency}
          onChange={(code) => {
            change({
              giveCurrency: code,
              giveCountry: look(code).home ?? form.giveCountry,
              // An untouched rate turns to read the right way round for the new currency.
              wants: form.wants.map((want) =>
                want.rate ? want : { ...newWant(code, want.currency, want.country) },
              ),
            })
          }}
        />
        <CountrySelect
          value={form.giveCountry}
          onChange={(code) => {
            change({ giveCountry: code })
          }}
        />
      </Section>
      <Section title={t('wizard.amount')}>
        <AmountInput
          label={t('wizard.amount_total')}
          currency={form.giveCurrency}
          value={form.total}
          onChange={(total) => {
            change({ total })
          }}
        />
        <Switch
          label={t('wizard.amount_exact')}
          checked={form.exact}
          onChange={(exact) => {
            change({ exact })
          }}
        />
        {!form.exact && (
          <AmountInput
            label={t('wizard.amount_min')}
            currency={form.giveCurrency}
            value={form.least}
            onChange={(least) => {
              change({ least })
            }}
          />
        )}
      </Section>
      <Section title={t('wizard.methods')}>
        <div className="flex flex-wrap gap-2 p-3">
          {KINDS.map(({ kind, icon, label }) => {
            const selected = form.methods.includes(kind)
            return (
              <Chip
                key={kind}
                icon={icon}
                label={t(label)}
                selected={selected}
                onToggle={() => {
                  hapticSelect()
                  change(({ methods }) => ({
                    methods: methods.includes(kind)
                      ? methods.filter((method) => method !== kind)
                      : [...methods, kind],
                  }))
                }}
              />
            )
          })}
        </div>
      </Section>
      <Section title={t('wizard.dates')}>
        <Field label={t('wizard.first_day')}>
          <input
            type="date"
            className={CONTROL}
            min={today}
            value={form.from}
            onChange={(event) => {
              change({ from: event.target.value })
            }}
          />
        </Field>
        <Field label={t('wizard.last_day')}>
          <input
            type="date"
            className={CONTROL}
            min={form.from || today}
            value={form.until}
            onChange={(event) => {
              change({ until: event.target.value })
            }}
          />
        </Field>
      </Section>
    </>
  )
}

/** Step 2, «Хочу»: each wanted currency with its rate, and a live preview. */
function WantStep({ form, change }: StepProps) {
  const { t } = useI18n()
  const update = (index: number, changes: Partial<WantForm>) => {
    change(({ wants }) => ({
      wants: wants.map((want, at) => (at === index ? { ...want, ...changes } : want)),
    }))
  }
  return (
    <>
      {form.wants.map((want, index) => (
        <Section key={index} title={index === 0 ? t('wizard.want.title') : undefined}>
          <CurrencySelect
            label={t('wizard.currency')}
            value={want.currency}
            onChange={(code) => {
              const fresh = newWant(form.giveCurrency, code, look(code).home ?? want.country)
              update(index, want.rate ? { currency: code, country: fresh.country } : fresh)
            }}
          />
          <CountrySelect
            value={want.country}
            onChange={(country) => {
              update(index, { country })
            }}
          />
          <RateRow
            give={form.giveCurrency}
            want={want}
            onChange={(changes) => {
              update(index, changes)
            }}
          />
          <Preview form={form} want={want} />
          {form.wants.length > 1 && (
            <button
              type="button"
              onClick={() => {
                change(({ wants }) => ({ wants: wants.filter((_, at) => at !== index) }))
              }}
              className="flex w-full items-center justify-center gap-2 px-4 py-3 text-destructive"
            >
              <X aria-hidden className="size-4" />
              {t('wizard.remove_want')}
            </button>
          )}
        </Section>
      ))}
      {form.wants.length < MAX_WANTS && (
        <div className="mx-4">
          <Button
            icon={<Plus aria-hidden className="size-5" />}
            onClick={() => {
              change(({ wants, giveCurrency }) => ({ wants: [...wants, newWant(giveCurrency)] }))
            }}
          >
            {t('wizard.add_want')}
          </Button>
        </div>
      )}
    </>
  )
}

/** «1 GEL = [29,20] RUB ⇄», typed the way the author thinks (ADR-0004). */
function RateRow({
  give,
  want,
  onChange,
}: {
  give: string
  want: WantForm
  onChange: (changes: Partial<WantForm>) => void
}) {
  const { t } = useI18n()
  const [base, quote] = want.flipped ? [give, want.currency] : [want.currency, give]
  const label = (code: string): ReactNode => (code ? <Asset code={code} /> : '…')
  return (
    <div className="flex min-h-12 items-center gap-2 px-4 py-2">
      <span className="shrink-0">{t('order.rate')}</span>
      <span className="flex min-w-0 flex-1 items-center justify-end gap-1.5 whitespace-nowrap">
        <span>1</span>
        {label(base)}
        <span>=</span>
        <input
          className={`${CONTROL} w-20`}
          inputMode="decimal"
          autoComplete="off"
          placeholder="0"
          aria-label={t('order.rate')}
          value={want.rate}
          onChange={(event) => {
            onChange({ rate: event.target.value })
          }}
        />
        {label(quote)}
      </span>
      <button
        type="button"
        aria-label={t('wizard.flip')}
        onClick={() => {
          hapticSelect()
          onChange({ flipped: !want.flipped, rate: '' })
        }}
        className="flex size-9 shrink-0 items-center justify-center rounded-full text-accent active:bg-secondary-bg"
      >
        <ArrowLeftRight aria-hidden className="size-5" />
      </button>
    </div>
  )
}

/** «Отдав 150 000 ₽ RUB, получите ≈ 5 136,99 ₾ GEL», asked of the api as it changes. */
function Preview({ form, want }: { form: OrderForm; want: WantForm }) {
  const { tn, locale } = useI18n()
  const total = parseAmount(form.total)
  const request: QuoteRequest | null =
    total && parseRate(want.rate) && want.currency && form.giveCurrency
      ? {
          amount: total,
          give_currency: form.giveCurrency,
          want_currency: want.currency,
          rate_spec: { v: 1, type: 'fixed', quotes: [quoteOf(form.giveCurrency, want)] },
          whole: false,
        }
      : null
  // Debounced as text: a new object every render would never settle.
  const settled = useDebounced(request ? JSON.stringify(request) : null)
  const quote = useQuote(
    useMemo(() => (settled ? (JSON.parse(settled) as QuoteRequest) : null), [settled]),
  )
  if (!request || !total || !quote.data) return null
  return (
    <p className="px-4 pb-3 text-sm text-hint">
      {tn('wizard.preview', {
        give: <Money locale={locale} amount={total} code={form.giveCurrency} />,
        want: <Money locale={locale} amount={quote.data.amount} code={want.currency} />,
      })}
    </p>
  )
}

/** Step 3, «Кому видно»: all links or chosen ones, and a note. */
function WhoStep({ form, change }: StepProps) {
  const { t } = useI18n()
  const links = useLinks()
  const active = links.data?.active ?? []
  return (
    <>
      <Section title={t('wizard.who.title')}>
        <Choice
          kind="radio"
          label={t('wizard.who.all')}
          checked={form.everyone}
          onChange={() => {
            change({ everyone: true })
          }}
        />
        <Choice
          kind="radio"
          label={t('wizard.who.some')}
          checked={!form.everyone}
          onChange={() => {
            change({ everyone: false })
          }}
        />
      </Section>
      {links.isSuccess && active.length === 0 && (
        <p className="px-6 text-sm text-hint">{t('wizard.who.none')}</p>
      )}
      {!form.everyone && active.length > 0 && (
        <Section>
          {active.map((link) => {
            const checked = form.chosen.includes(link.person.id)
            return (
              <Choice
                key={link.id}
                kind="checkbox"
                leading={<Avatar name={fullName(link.person)} size="sm" />}
                label={fullName(link.person)}
                checked={checked}
                onChange={() => {
                  change(({ chosen }) => ({
                    chosen: chosen.includes(link.person.id)
                      ? chosen.filter((id) => id !== link.person.id)
                      : [...chosen, link.person.id],
                  }))
                }}
              />
            )
          })}
        </Section>
      )}
      <Section title={t('wizard.note')}>
        <textarea
          className="block min-h-24 w-full resize-none bg-transparent px-4 py-3 outline-none placeholder:text-hint"
          maxLength={500}
          placeholder={t('wizard.note_hint')}
          value={form.note}
          onChange={(event) => {
            change({ note: event.target.value })
          }}
        />
      </Section>
    </>
  )
}
