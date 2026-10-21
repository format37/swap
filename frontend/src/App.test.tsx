import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import type { Me } from './api/client'
import { App } from './App'
import { I18nProvider } from './i18n/I18n'
import type { Locale } from './i18n/locale'
import { Home } from './screens/Home'

const me: Me = {
  id: '6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  locale: 'ru',
  locale_chosen: false,
}

function home(locale: Locale) {
  return render(
    <I18nProvider locale={locale}>
      <MemoryRouter>
        <Home me={me} />
      </MemoryRouter>
    </I18nProvider>,
  )
}

it('outside Telegram, points to the bot in the browser’s language', () => {
  render(<App launch={null} />)
  // jsdom's navigator.language is en-US.
  expect(screen.getByRole('heading')).toHaveTextContent('Open Swap in Telegram')
  expect(screen.getByRole('link')).toHaveAttribute('href', 'https://t.me/peertopeerswapbot')
})

it('greets the user by name, in their language', () => {
  home('ru')
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Привет, Alex!')
  expect(screen.getByText('@format37')).toBeInTheDocument()
  // The language row names the current language in its own script.
  expect(screen.getByRole('button', { name: /Язык.*Русский/ })).toBeInTheDocument()
})

it('speaks Georgian when asked to', () => {
  home('ka')
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('გამარჯობა, Alex!')
  expect(screen.getByRole('button', { name: /ენა.*ქართული/ })).toBeInTheDocument()
})
