/** Russian is the source: en.ts and ka.ts must have exactly these keys (ADR-0009). */
export const ru = {
  'home.hello': 'Привет, {name}!',
  'home.intro':
    'Swap поможет договориться об обмене денег между странами с теми, кого вы знаете. Сами деньги Swap не хранит и не переводит.',
  'home.soon': 'Скоро здесь появятся связи, заявки и сделки.',
  'settings.title': 'Настройки',
  'settings.language': 'Язык',
  'language.title': 'Язык',
  'outside.title': 'Откройте Swap в Telegram',
  'outside.text': 'Swap работает внутри Telegram, как мини-приложение бота.',
  'outside.button': 'Открыть в Telegram',
  'error.title': 'Не получилось',
  'error.generic': 'Что-то пошло не так. Попробуйте ещё раз.',
  'error.network': 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.',
  'error.reopen': 'Сессия устарела. Закройте Swap и откройте его снова.',
  'error.retry': 'Повторить',
} as const

export type MessageKey = keyof typeof ru
export type Messages = Record<MessageKey, string>
