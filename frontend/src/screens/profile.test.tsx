import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import { fakeApi } from '../test/api'
import { renderScreen } from '../test/render'
import { Profile } from './Profile'

const me: Me = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: null,
  score: 0,
  locale: 'ru',
  locale_chosen: false,
  tz: 'Asia/Tbilisi',
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('the profile', () => {
  it('shows who I am and my language, and asks for no payment details', () => {
    const { served } = fakeApi({})
    renderScreen(<Profile me={me} />, { route: '/profile' })
    expect(screen.getByRole('heading', { name: 'Nino B' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Язык.*Русский/ })).toBeInTheDocument()
    // The parties settle where to pay among themselves (QUESTIONS G3).
    expect(screen.queryByText(/Реквизиты/)).toBeNull()
    expect(served).toEqual([])
  })
})
