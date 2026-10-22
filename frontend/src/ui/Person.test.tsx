import { fireEvent, render, screen } from '@testing-library/react'

import { Avatar } from './Avatar'
import { Person } from './Person'

const PHOTO = 'https://t.me/i/userpic/320/nino.jpg'
const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: PHOTO,
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
  render(<Person person={NINO} detail="с 21 окт." />)
  expect(screen.getByText('Nino B')).toBeInTheDocument()
  expect(screen.getByText('@nino · с 21 окт.')).toBeInTheDocument()
})

it('makes the name a heading on a screen about the person', () => {
  render(<Person person={{ ...NINO, username: null, photo_url: null }} heading detail="Сделка" />)
  expect(screen.getByRole('heading', { name: 'Nino B' })).toBeInTheDocument()
  expect(screen.getByText('Сделка')).toBeInTheDocument()
})
