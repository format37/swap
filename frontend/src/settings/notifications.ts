import type { Me } from '../api/client'
import type { MessageKey } from '../i18n/ru'

/** How the settings row says it: «Включены», «Выключены» or «Частично» (QUESTIONS K1). */
export function notificationsState(me: Me): MessageKey {
  if (me.notifications_off) return 'notify.off'
  return me.muted_kinds.length > 0 ? 'notify.some' : 'notify.on'
}
