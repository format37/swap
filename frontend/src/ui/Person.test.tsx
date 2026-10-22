import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactElement } from 'react'
import { vi } from 'vitest'

import { I18nProvider } from '../i18n/I18n'
import { explain } from '../telegram'
import { Avatar } from './Avatar'
import { Person } from './Person'

vi.mock('../telegram', () => ({ explain: vi.fn(() => Promise.resolve()) }))

function inRussian(ui: ReactElement) {
  return render(<I18nProvider locale="ru">{ui}</I18nProvider>)
}

const PHOTO = 'https://t.me/i/userpic/320/nino.jpg'
const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: PHOTO,
  score: 0,
  deleted: false,
}

it('shows the Telegram photo, straight from Telegram (J4)', () => {
  const { container } = render(<Avatar name="Nino B" photo={PHOTO} />)
  const image = container.querySelector('img')
  expect(image).toHaveAttribute('src', PHOTO)
  // Telegram learns nothing of where the app runs from.
  expect(image).toHaveAttribute('referrerpolicy', 'no-referrer')
})

it('falls back to the initials when there is no photo, or it doesn’t load', () => {
  const { container, rerender } = render(<Avatar name="Nino B" />)
  expect(container).toHaveTextContent('NB')
  rerender(<Avatar name="Nino B" photo={PHOTO} />)
  fireEvent.error(container.querySelector('img') as HTMLImageElement)
  expect(container.querySelector('img')).toBeNull()
  expect(container).toHaveTextContent('NB')
})

it('takes Telegram’s 1×1 stand-in for a hidden photo as no photo', () => {
  const { container } = render(<Avatar name="Alex" photo={PHOTO} />)
  const image = container.querySelector('img') as HTMLImageElement
  Object.defineProperty(image, 'naturalWidth', { value: 1 })
  fireEvent.load(image)
  expect(container.querySelector('img')).toBeNull()
  expect(container).toHaveTextContent('A')
})

it('puts the name and, under it, the @username to the right of the photo', () => {
  inRussian(<Person person={NINO} detail="с 21 окт." />)
  expect(screen.getByText('Nino B')).toBeInTheDocument()
  expect(screen.getByText('@nino · с 21 окт.')).toBeInTheDocument()
})

it('makes the name a heading on a screen about the person', () => {
  inRussian(
    <Person person={{ ...NINO, username: null, photo_url: null }} heading detail="Сделка" />,
  )
  expect(screen.getByRole('heading', { name: 'Nino B' })).toBeInTheDocument()
  expect(screen.getByText('Сделка')).toBeInTheDocument()
})

it('shows the score beside the name, and explains it on a tap in a heading (J5)', () => {
  const { rerender } = inRussian(<Person person={{ ...NINO, score: 7 }} />)
  // In a row that is itself a button, the score only shows.
  expect(screen.getByRole('img', { name: 'Скор: 7' })).toHaveTextContent('7')
  rerender(
    <I18nProvider locale="ru">
      <Person person={{ ...NINO, score: 7 }} heading />
    </I18nProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Скор: 7' }))
  expect(explain).toHaveBeenCalledWith(
    'Успешные сделки с разными людьми: 7. Повторные сделки с тем же человеком не прибавляют.',
  )
})
