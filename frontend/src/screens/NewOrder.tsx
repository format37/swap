import { ArrowLeftRight, Plus, X } from 'lucide-react'
import { Fragment, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { useLinks } from '../api/links'
import { useMe } from '../api/me'
import { audience, useNetwork } from '../api/network'
import {
  useAssets,
  useMarketRate,
  usePublishOrder,
  useQuote,
  type PaymentKind,
  type QuoteRequest,
} from '../api/orders'
import { useBackOverride } from '../back'
import { countryName, sortedCountries } from '../i18n/countries'
import { errorMessage } from '../i18n/errors'
import { formatTime } from '../i18n/format'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { assetText, look } from '../money/looks'
import { formatRate, parseAmount, parseRate } from '../money/format'
import { KINDS } from '../money/kinds'
import {
  emptyForm,
  giveProblem,
  isoDate,
  newWant,
  specOf,
  toDraft,
  toggled,
  wantProblem,
  type Reach,
  whoProblem,
  type OrderForm,
  type WantForm,
} from '../orders/form'
import { Rings } from '../orders/Rings'
import { hapticNotify, hapticSelect, useMainButton } from '../telegram'
import { Button } from '../ui/Button'
import { Chip } from '../ui/Chip'
import { Choice } from '../ui/Choice'
import { CONTROL, Field } from '../ui/Field'
import { FormError } from '../ui/FormError'
import { Person } from '../ui/Person'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Switch } from '../ui/Switch'
import { useDebounced } from '../useDebounced'

type Step = 1 | 2
const MAX_WANTS = 3

/**
 * «Новая заявка» in two steps (QUESTIONS J1): what I give and what I get, then who sees it.
 * The state stays here until «Опубликовать»; there are no server drafts (Q-B17).
 * BackButton steps back to step 1, then leaves.
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
            setStep(1)
          }
        : null,
    [step],
  )
  useBackOverride(stepBack)

  const problem = step === 1 ? (giveProblem(form, today) ?? wantProblem(form)) : whoProblem(form)
  useMainButton({
    text: t(step === 2 ? 'wizard.publish' : 'wizard.next'),
    busy: publish.isPending,
    onClick: () => {
      if (problem) {
        setShown(problem)
        hapticNotify('error')
        return
      }
      if (step === 1) {
        setStep(2)
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
        {/* What step 1 decided, in a line, before it goes out (J1). */}
        {step === 2 && <Digest form={form} />}
      </header>
      {step === 1 && (
        <>
          <GiveGroup form={form} today={today} change={change} />
          <WantGroup form={form} change={change} />
        </>
      )}
      {step === 2 && <WhoStep form={form} change={change} />}
      <FormError>
        {shown ? t(shown) : publish.isError ? t(errorMessage(publish.error)) : null}
      </FormError>
    </Screen>
  )
}

/** What a step changes: plain values, or values worked out from the form as it is now. */
type Changes = Partial<OrderForm> | ((current: OrderForm) => Partial<OrderForm>)

interface StepProps {
  form: OrderForm
  change: (changes: Changes) => void
}

/**
 * `prompt` heads the list, «Отдаёте» or «Получаете»: the list covers the screen while it
 * is open, and someone distracted should still know which side they are choosing (F1).
 */
function CurrencySelect({
  value,
  onChange,
  label,
  prompt,
}: {
  value: string
  onChange: (code: string) => void
  label: string
  prompt: string
}) {
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
          {prompt}
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

/** The ways money moves, as chips that each tap turns on or off, under their label. */
function MethodChips({
  label,
  chosen,
  onToggle,
}: {
  label: string
  chosen: PaymentKind[]
  onToggle: (kind: PaymentKind) => void
}) {
  const { t } = useI18n()
  return (
    <div role="group" aria-label={label} className="px-4 py-3">
      <p>{label}</p>
      <div className="flex flex-wrap gap-2 pt-2">
        {KINDS.map(({ kind, icon, label: name }) => (
          <Chip
            key={kind}
            icon={icon}
            label={t(name)}
            selected={chosen.includes(kind)}
            onToggle={() => {
              hapticSelect()
              onToggle(kind)
            }}
          />
        ))}
      </div>
    </div>
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

/** Step 1's «Отдаёте»: currency, country, amount, how, when; one group, no titles (J1). */
function GiveGroup({ form, today, change }: StepProps & { today: string }) {
  const { t } = useI18n()
  return (
    <Section title={t('wizard.give')}>
      <CurrencySelect
        label={t('wizard.currency')}
        prompt={t('wizard.give.prompt')}
        value={form.giveCurrency}
        onChange={(code) => {
          change({
            giveCurrency: code,
            giveCountry: look(code).home ?? form.giveCountry,
            // A rate the author hasn't typed turns to read the right way round for the
            // new currency, and the market's rate for the new pair fills it in again.
            wants: form.wants.map((want) =>
              want.typed
                ? want
                : {
                    ...newWant(code, want.currency, want.country),
                    fixed: want.fixed,
                    receiveMethods: want.receiveMethods,
                  },
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
      <AmountInput
        label={t('wizard.amount')}
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
      <MethodChips
        label={t('wizard.methods')}
        chosen={form.methods}
        onToggle={(kind) => {
          change(({ methods }) => ({ methods: toggled(methods, kind) }))
        }}
      />
      <Field label={t('wizard.dates')}>
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
      {/* Off by default: open until its author closes it (F3). */}
      <Switch
        label={t('wizard.limited')}
        checked={form.limited}
        onChange={(limited) => {
          change({ limited })
        }}
      />
      {form.limited && (
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
      )}
      {/* A copy every month on day N, told like any new order (QUESTIONS K7). */}
      <Switch
        label={t('wizard.repeats')}
        checked={form.repeats}
        onChange={(repeats) => {
          change({ repeats })
        }}
      />
      {form.repeats && (
        <Field label={t('wizard.repeat_day')}>
          <select
            className={CONTROL}
            value={form.repeatDay}
            onChange={(event) => {
              hapticSelect()
              change({ repeatDay: event.target.value })
            }}
          >
            {Array.from({ length: 31 }, (_, index) => String(index + 1)).map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
          </select>
        </Field>
      )}
    </Section>
  )
}

/**
 * Step 1's «Получаете»: each wanted currency with its rate, its own «Зафиксировать курс»,
 * a live preview (J1), and how the author takes it (L1).
 */
function WantGroup({ form, change }: StepProps) {
  const { t } = useI18n()
  const update = (index: number, changes: Partial<WantForm>) => {
    change(({ wants }) => ({
      wants: wants.map((want, at) => (at === index ? { ...want, ...changes } : want)),
    }))
  }
  return (
    <>
      {form.wants.map((want, index) => (
        <Section key={index} title={index === 0 ? t('wizard.want') : undefined}>
          <CurrencySelect
            label={t('wizard.currency')}
            prompt={t('wizard.want.prompt')}
            value={want.currency}
            onChange={(code) => {
              const fresh = newWant(form.giveCurrency, code, look(code).home ?? want.country)
              update(
                index,
                want.typed
                  ? { currency: code, country: fresh.country }
                  : { ...fresh, fixed: want.fixed, receiveMethods: want.receiveMethods },
              )
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
          {/* The market's rate unless the author fixes this one (QUESTIONS G2, J1). */}
          <Switch
            label={t('wizard.fixed')}
            checked={want.fixed}
            onChange={(fixed) => {
              update(index, { fixed })
            }}
          />
          <Preview form={form} want={want} />
          <MethodChips
            label={t('wizard.receive_methods')}
            chosen={want.receiveMethods}
            onToggle={(kind) => {
              change(({ wants }) => ({
                wants: wants.map((other, at) =>
                  at === index
                    ? { ...other, receiveMethods: toggled(other.receiveMethods, kind) }
                    : other,
                ),
              }))
            }}
          />
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
      {form.wants.some((want) => !want.fixed) && (
        <p className="-mt-2 px-6 text-sm text-hint">{t('wizard.market_hint')}</p>
      )}
      {form.wants.length < MAX_WANTS && (
        <div className="mx-4">
          <Button
            icon={<Plus aria-hidden className="size-5" />}
            onClick={() => {
              // Taken the way the one above is, so shared ways cost no taps (ADR-0037).
              change(({ wants, giveCurrency }) => ({
                wants: [
                  ...wants,
                  { ...newWant(giveCurrency), receiveMethods: wants.at(-1)?.receiveMethods ?? [] },
                ],
              }))
            }}
          >
            {t('wizard.add_want')}
          </Button>
        </div>
      )}
    </>
  )
}

/**
 * «1 GEL = [29,20] RUB ⇄», typed the way the author thinks (ADR-0004). Until they type,
 * it holds the market's rate for the pair, with its source and time beneath (F5). While
 * the order follows the market, it only shows the market's rate (QUESTIONS G2).
 */
function RateRow({
  give,
  want,
  onChange,
}: {
  give: string
  want: WantForm
  onChange: (changes: Partial<WantForm>) => void
}) {
  const { t, tn, locale } = useI18n()
  const [base, quote] = want.flipped ? [give, want.currency] : [want.currency, give]
  const market = useMarketRate(base, quote).data
  const suggested = market && formatRate(locale, market.value)
  useEffect(() => {
    if (suggested && !want.typed && !want.rate) onChange({ rate: suggested })
  }, [suggested, want.typed, want.rate, onChange])
  const label = (code: string): ReactNode => (code ? <Asset code={code} /> : '…')
  if (!want.fixed)
    return (
      <div>
        <div className="flex min-h-12 items-center gap-2 px-4 py-2">
          <span className="shrink-0">{t('order.rate')}</span>
          <span className="flex min-w-0 flex-1 items-center justify-end gap-1.5 whitespace-nowrap">
            {suggested ? (
              <>
                1 {label(base)} = {suggested} {label(quote)}
              </>
            ) : (
              '…'
            )}
          </span>
        </div>
        {market && (
          <p className="px-4 pb-2 text-sm text-hint">
            {t('wizard.market_source', { time: formatTime(locale, market.fetched_at) })}
          </p>
        )}
      </div>
    )
  // One child of the section, so no line parts the rate from where it came from.
  return (
    <div>
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
              onChange({ rate: event.target.value, typed: true })
            }}
          />
          {label(quote)}
        </span>
        <button
          type="button"
          aria-label={t('wizard.flip')}
          onClick={() => {
            hapticSelect()
            onChange({ flipped: !want.flipped, rate: '', typed: false })
          }}
          className="flex size-9 shrink-0 items-center justify-center rounded-full text-accent active:bg-secondary-bg"
        >
          <ArrowLeftRight aria-hidden className="size-5" />
        </button>
      </div>
      {market && suggested && (
        // The market's rate itself only once the author's differs; tapping puts it back.
        <button
          type="button"
          onClick={() => {
            hapticSelect()
            onChange({ rate: suggested, typed: false })
          }}
          className="flex w-full flex-wrap items-center gap-1 px-4 pb-2 text-left text-sm text-hint active:opacity-70"
        >
          {want.rate === suggested
            ? t('wizard.market_source', { time: formatTime(locale, market.fetched_at) })
            : tn('wizard.market', {
                time: formatTime(locale, market.fetched_at),
                rate: (
                  <>
                    1 <Asset code={base} /> = {suggested} <Asset code={quote} />
                  </>
                ),
              })}
        </button>
      )}
    </div>
  )
}

/** «Отдав 150 000 ₽ RUB, получите ≈ 5 136,99 ₾ GEL», asked of the api as it changes. */
function Preview({ form, want }: { form: OrderForm; want: WantForm }) {
  const { tn, locale } = useI18n()
  const total = parseAmount(form.total)
  const request: QuoteRequest | null =
    total && (!want.fixed || parseRate(want.rate)) && want.currency && form.giveCurrency
      ? {
          amount: total,
          give_currency: form.giveCurrency,
          want_currency: want.currency,
          rate_spec: specOf(form.giveCurrency, want),
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

/**
 * «Отдаёте 150 000 ₽ RUB · Россия → ₾ GEL по рынку или $ USD по 1 USD = 80 RUB»: step 1 in a
 * line, at the head of step 2 (QUESTIONS J1).
 */
function Digest({ form }: { form: OrderForm }) {
  const { t, tn, locale } = useI18n()
  const wants = form.wants.map((want, index) => {
    const [base, quote] = want.flipped
      ? [form.giveCurrency, want.currency]
      : [want.currency, form.giveCurrency]
    const value = parseRate(want.rate)
    return (
      <Fragment key={want.currency}>
        {index > 0 && ` ${t('order.or')} `}
        {want.fixed && value
          ? tn('wizard.digest.fixed', {
              currency: <Asset code={want.currency} />,
              rate: (
                <>
                  1 <Asset code={base} /> = {formatRate(locale, value)} <Asset code={quote} />
                </>
              ),
            })
          : tn('wizard.digest.market', { currency: <Asset code={want.currency} /> })}
      </Fragment>
    )
  })
  return (
    <p className="mt-2">
      {tn('wizard.digest', {
        amount: (
          <Money locale={locale} amount={parseAmount(form.total) ?? '0'} code={form.giveCurrency} />
        ),
        country: countryName(locale, form.giveCountry),
        wants,
      })}
      {form.repeats && t('wizard.digest.repeats', { day: form.repeatDay })}
    </p>
  )
}

// The slider's five stops: 0 is «Только выбранным», 4 stands for the whole network.
const STOPS: Reach[] = [0, 1, 2, 3, null]

function stopKey(reach: Reach, kind: 'stop' | 'about'): MessageKey {
  return `reach.${kind}.${reach ?? 'all'}`
}

/**
 * Step 2, «Кому видно»: how many handshakes away the order is seen, on a slider in words,
 * with who that is and the rings it reaches (QUESTIONS J2); at 0, the links to choose
 * from. Then a note.
 */
function WhoStep({ form, change }: StepProps) {
  const { t } = useI18n()
  const links = useLinks()
  const network = useNetwork()
  const me = useMe().data
  const active = links.data?.active ?? []
  const stop = STOPS.indexOf(form.reach)
  const pick = (reach: Reach) => {
    hapticSelect()
    change({ reach })
  }
  const seen = network.data && audience(network.data, form.reach)
  return (
    <>
      <Section title={t('wizard.who.title')}>
        <div className="px-4 py-3">
          <p className="font-medium">{t(stopKey(form.reach, 'about'))}</p>
          <input
            type="range"
            className="mt-3 w-full accent-[var(--color-button)]"
            min={0}
            max={STOPS.length - 1}
            step={1}
            value={stop}
            aria-label={t('wizard.who.title')}
            aria-valuetext={t(stopKey(form.reach, 'about'))}
            onChange={(event) => {
              pick(STOPS[Number(event.target.value)] ?? null)
            }}
          />
          <div className="mt-1 grid grid-cols-5 gap-1 text-center text-xs leading-tight">
            {STOPS.map((reach) => (
              <button
                key={reach ?? 'all'}
                type="button"
                aria-pressed={form.reach === reach}
                onClick={() => {
                  pick(reach)
                }}
                className={form.reach === reach ? 'font-semibold text-accent' : 'text-hint'}
              >
                {t(stopKey(reach, 'stop'))}
              </button>
            ))}
          </div>
          <p className="mt-3 text-sm text-hint">
            {form.reach === 0
              ? t('reach.audience_chosen', { count: form.chosen.length })
              : seen &&
                (form.reach === 1
                  ? t('reach.audience_links', { links: seen.links })
                  : t('reach.audience', { links: seen.links, more: seen.more }))}
          </p>
        </div>
      </Section>
      {links.isSuccess && active.length === 0 && (
        <p className="px-6 text-sm text-hint">{t('wizard.who.none')}</p>
      )}
      {form.reach === 0 && active.length > 0 && (
        <Section>
          {active.map((link) => {
            const checked = form.chosen.includes(link.person.id)
            return (
              <Choice
                key={link.id}
                kind="checkbox"
                label={<Person person={link.person} />}
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
      {form.reach !== 0 && network.data && me && (
        <Rings me={me} network={network.data} reach={form.reach} />
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
