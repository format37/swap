import { Bell } from 'lucide-react'

import type { Me } from '../api/client'
import { useUpdateMe, type NotificationKind } from '../api/me'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { hapticSelect } from '../telegram'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Switch } from '../ui/Switch'

const KINDS: { kind: NotificationKind; label: MessageKey }[] = [
  { kind: 'orders', label: 'notify.kind.orders' },
  { kind: 'links', label: 'notify.kind.links' },
  { kind: 'proposals', label: 'notify.kind.proposals' },
  { kind: 'transfers', label: 'notify.kind.transfers' },
  { kind: 'cancellations', label: 'notify.kind.cancellations' },
]

/**
 * What the bot tells: everything off at once, or kind by kind (QUESTIONS K1). One
 * person's new orders are muted on their link's screen.
 */
export function Notifications({ me }: { me: Me }) {
  const { t } = useI18n()
  const update = useUpdateMe()
  const muted = me.muted_kinds
  return (
    <Screen>
      <h1 className="flex items-center gap-2 px-6 pt-4 text-2xl font-semibold">
        <Bell aria-hidden className="size-6 text-accent" />
        {t('notify.title')}
      </h1>
      <Section>
        <Switch
          label={t('notify.all')}
          checked={!me.notifications_off}
          onChange={(on) => {
            hapticSelect()
            update.mutate({ notifications_off: !on })
          }}
        />
      </Section>
      {!me.notifications_off && (
        <Section title={t('notify.kinds')}>
          {KINDS.map(({ kind, label }) => (
            <Switch
              key={kind}
              label={t(label)}
              checked={!muted.includes(kind)}
              onChange={(on) => {
                hapticSelect()
                update.mutate({
                  muted_kinds: on ? muted.filter((each) => each !== kind) : [...muted, kind],
                })
              }}
            />
          ))}
        </Section>
      )}
      <p className="px-6 text-sm text-hint">{t('notify.hint')}</p>
      {update.isError && <p className="px-6 text-destructive">{t('error.generic')}</p>}
    </Screen>
  )
}
