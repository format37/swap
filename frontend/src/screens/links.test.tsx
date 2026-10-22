import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Link, Links as LinksBody } from '../api/links'
import { confirmAction, copyText, shareLink, useMainButton, type MainAction } from '../telegram'
import { fakeApi, json, problem } from '../test/api'
import { renderScreen } from '../test/render'
import { Invite } from './Invite'
import { LinkScreen } from './LinkScreen'
import { Links } from './Links'

vi.mock('../telegram', () => ({
  useMainButton: vi.fn(),
  confirmAction: vi.fn(() => Promise.resolve(true)),
  hapticNotify: vi.fn(),
  shareLink: vi.fn(() => false),
  copyText: vi.fn(() => Promise.resolve(true)),
}))

/** What the screen last put into Telegram's MainButton. */
function mainButton(): MainAction | null {
  return vi.mocked(useMainButton).mock.lastCall?.[0] ?? null
}

function pressMainButton() {
  act(() => {
    mainButton()?.onClick()
  })
}

const ALEX = {
  id: 'a0000000-0000-4000-8000-000000000001',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  photo_url: null,
}
const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: null,
}
const GIO = {
  id: 'a0000000-0000-4000-8000-000000000003',
  first_name: 'Gio',
  last_name: null,
  username: null,
  photo_url: null,
}
const LINK_ID = 'b0000000-0000-4000-8000-000000000001'

function link(overrides: Partial<Link> = {}): Link {
  return {
    id: LINK_ID,
    person: NINO,
    status: 'active',
    direction: 'outgoing',
    requested_at: '2026-10-20T10:00:00Z',
    accepted_at: '2026-10-21T10:00:00Z',
    ...overrides,
  }
}

const NOBODY: LinksBody = { active: [], incoming: [], outgoing: [], invites: [] }

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('the «Связи» tab', () => {
  it('explains linking while there is nobody yet', async () => {
    fakeApi({ 'GET /api/v1/links': () => json(200, NOBODY) })
    renderScreen(<Links />, { route: '/links' })
    expect(await screen.findByText('Пока ни одной связи')).toBeInTheDocument()
    expect(screen.getByText('Пригласите знакомого по ссылке')).toBeInTheDocument()
    expect(mainButton()?.text).toBe('Пригласить')
  })

  it('lists requests, links, sent requests and invitations', async () => {
    fakeApi({
      'GET /api/v1/links': () =>
        json(200, {
          incoming: [
            link({ person: ALEX, status: 'pending', direction: 'incoming', accepted_at: null }),
          ],
          active: [link()],
          outgoing: [link({ person: GIO, status: 'pending', accepted_at: null })],
          invites: [
            { id: 'c1', created_at: '2026-10-22T10:00:00Z', expires_at: '2026-10-25T10:00:00Z' },
          ],
        } satisfies LinksBody),
    })
    renderScreen(<Links />, { route: '/links' })
    const requests = (await screen.findByRole('heading', { name: 'Запросы' })).parentElement
    expect(requests).toHaveTextContent('Alex@format37')
    expect(screen.getByRole('heading', { name: 'Мои связи' }).parentElement).toHaveTextContent(
      'Nino B@nino · с 21 окт.',
    )
    expect(screen.getByRole('heading', { name: 'Отправленные' }).parentElement).toHaveTextContent(
      'Gioждёт ответа',
    )
    expect(screen.getByText('Ссылка действует до 25 окт.')).toBeInTheDocument()
  })

  it('creates an invitation from the main button and opens it', async () => {
    const { served } = fakeApi({
      'GET /api/v1/links': () => json(200, NOBODY),
      'POST /api/v1/links/invites': () =>
        json(201, {
          id: 'c1',
          created_at: '2026-10-22T10:00:00Z',
          expires_at: '2026-10-25T10:00:00Z',
          url: 'https://t.me/peertopeerswapbot?start=inv_abc',
        }),
    })
    renderScreen(<Links />, { route: '/links' })
    await screen.findByText('Пока ни одной связи')
    pressMainButton()
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent('/links/invite')
    expect(served).toContain('POST /api/v1/links/invites')
  })

  it('says so when there are too many unused invitations', async () => {
    fakeApi({
      'GET /api/v1/links': () => json(200, NOBODY),
      'POST /api/v1/links/invites': () => problem(429, 'invite.limit'),
    })
    renderScreen(<Links />, { route: '/links' })
    await screen.findByText('Пока ни одной связи')
    pressMainButton()
    expect(
      await screen.findByText(/Слишком много неиспользованных приглашений/),
    ).toBeInTheDocument()
  })

  it('revokes an invitation only once that is confirmed', async () => {
    const { served } = fakeApi({
      'GET /api/v1/links': () =>
        json(200, {
          ...NOBODY,
          invites: [
            { id: 'c1', created_at: '2026-10-22T10:00:00Z', expires_at: '2026-10-25T10:00:00Z' },
          ],
        }),
      'DELETE /api/v1/links/invites/c1': () => new Response(null, { status: 204 }),
    })
    renderScreen(<Links />, { route: '/links' })
    const revoke = await screen.findByRole('button', { name: 'Отозвать' })

    vi.mocked(confirmAction).mockResolvedValueOnce(false)
    fireEvent.click(revoke)
    await waitFor(() => {
      expect(confirmAction).toHaveBeenCalledTimes(1)
    })
    expect(served).not.toContain('DELETE /api/v1/links/invites/c1')

    fireEvent.click(revoke)
    await waitFor(() => {
      expect(served).toContain('DELETE /api/v1/links/invites/c1')
    })
  })
})

describe('a request by @username', () => {
  it('asks and opens the request', async () => {
    let body: unknown
    fakeApi({
      'GET /api/v1/links': () => json(200, NOBODY),
      'POST /api/v1/links/requests': async (request) => {
        body = await request.json()
        return json(200, link({ status: 'pending', accepted_at: null }))
      },
    })
    renderScreen(<Links />, { route: '/links' })
    const field = await screen.findByRole('textbox', { name: 'Запрос по @username' })
    const send = screen.getByRole('button', { name: 'Отправить запрос' })
    expect(send).toBeDisabled()
    fireEvent.change(field, { target: { value: '@nino' } })
    fireEvent.click(send)
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent(`/links/${LINK_ID}`)
    expect(body).toEqual({ username: '@nino' })
  })

  it('suggests an invitation for a name nobody in Swap has', async () => {
    fakeApi({
      'GET /api/v1/links': () => json(200, NOBODY),
      'POST /api/v1/links/requests': () => problem(404, 'user.not_found'),
    })
    renderScreen(<Links />, { route: '/links' })
    fireEvent.change(await screen.findByRole('textbox', { name: 'Запрос по @username' }), {
      target: { value: 'stranger' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить запрос' }))
    expect(await screen.findByText(/Отправьте ссылку-приглашение/)).toBeInTheDocument()
  })

  it('says when to ask again after a decline', async () => {
    fakeApi({
      'GET /api/v1/links': () => json(200, NOBODY),
      'POST /api/v1/links/requests': () => problem(429, 'link.cooldown'),
    })
    renderScreen(<Links />, { route: '/links' })
    fireEvent.change(await screen.findByRole('textbox', { name: 'Запрос по @username' }), {
      target: { value: 'nino' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить запрос' }))
    expect(await screen.findByText(/через неделю/)).toBeInTheDocument()
  })
})

describe('the request screen', () => {
  const route = `/links/${LINK_ID}`
  const path = '/links/:id'

  it('accepts an incoming request with the main button', async () => {
    let status: Link['status'] = 'pending'
    const { served } = fakeApi({
      [`GET /api/v1/links/${LINK_ID}`]: () =>
        json(200, {
          ...link({
            person: ALEX,
            status,
            direction: 'incoming',
            accepted_at: status === 'active' ? '2026-10-22T10:00:00Z' : null,
          }),
          mutual_links: 2,
        }),
      [`POST /api/v1/links/${LINK_ID}/accept`]: () => {
        status = 'active'
        return json(200, link({ person: ALEX, status, direction: 'incoming' }))
      },
    })
    renderScreen(<LinkScreen />, { route, path })
    expect(await screen.findByText('Хочет установить с вами связь')).toBeInTheDocument()
    expect(screen.getByText('Общие связи: 2')).toBeInTheDocument()
    expect(mainButton()?.text).toBe('Установить связь')

    pressMainButton()
    expect(await screen.findByText('Связь установлена 22 октября')).toBeInTheDocument()
    expect(served).toContain(`POST /api/v1/links/${LINK_ID}/accept`)
    // Nothing is left to answer, so the main button leads on (QUESTIONS G6).
    expect(mainButton()?.text).toBe('На главную')
    pressMainButton()
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent('/')
  })

  it('declines after confirmation and goes back to the tab', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/links/${LINK_ID}`]: () =>
        json(200, {
          ...link({ person: ALEX, status: 'pending', direction: 'incoming', accepted_at: null }),
          mutual_links: 0,
        }),
      [`POST /api/v1/links/${LINK_ID}/decline`]: () =>
        json(
          200,
          link({ person: ALEX, status: 'declined', direction: 'incoming', accepted_at: null }),
        ),
    })
    renderScreen(<LinkScreen />, { route, path })
    fireEvent.click(await screen.findByRole('button', { name: 'Отклонить' }))
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent('/links')
    expect(confirmAction).toHaveBeenCalledWith('Отклонить запрос?', 'Отклонить', {
      destructive: true,
    })
    expect(served).toContain(`POST /api/v1/links/${LINK_ID}/decline`)
  })

  it('lets the requester withdraw, and either side break a link', async () => {
    fakeApi({
      [`GET /api/v1/links/${LINK_ID}`]: () =>
        json(200, { ...link({ status: 'pending', accepted_at: null }), mutual_links: 0 }),
    })
    const { unmount } = renderScreen(<LinkScreen />, { route, path })
    expect(await screen.findByText('Ждём ответа')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Отозвать запрос' })).toBeInTheDocument()
    expect(mainButton()?.text).toBe('На главную')
    unmount()

    fakeApi({ [`GET /api/v1/links/${LINK_ID}`]: () => json(200, { ...link(), mutual_links: 0 }) })
    renderScreen(<LinkScreen />, { route, path })
    expect(await screen.findByRole('button', { name: 'Разорвать связь' })).toBeInTheDocument()
  })

  it('tells a stranger only that there is no such link', async () => {
    fakeApi({ [`GET /api/v1/links/${LINK_ID}`]: () => problem(404, 'link.not_found') })
    renderScreen(<LinkScreen />, { route, path })
    expect(await screen.findByText('Связь не найдена.')).toBeInTheDocument()
    // Trying again would find nothing either.
    expect(screen.queryByRole('button', { name: 'Повторить' })).toBeNull()
  })
})

describe('the invitation sheet', () => {
  const invite = {
    id: 'c1',
    created_at: '2026-10-22T10:00:00Z',
    expires_at: '2026-10-25T10:00:00Z',
    url: 'https://t.me/peertopeerswapbot?start=inv_abc',
  }

  it('shows the link once and shares it through Telegram', () => {
    vi.mocked(shareLink).mockReturnValueOnce(true)
    renderScreen(<Invite />, { route: '/links/invite', state: invite })
    expect(screen.getByText(invite.url)).toBeInTheDocument()
    expect(screen.getByText(/действует до 25 октября/)).toBeInTheDocument()
    expect(mainButton()?.text).toBe('Поделиться')
    pressMainButton()
    expect(shareLink).toHaveBeenCalledWith(invite.url, expect.stringContaining('Swap'))
    expect(copyText).not.toHaveBeenCalled()
  })

  it('copies the link where there is no share sheet', async () => {
    renderScreen(<Invite />, { route: '/links/invite', state: invite })
    pressMainButton()
    expect(copyText).toHaveBeenCalledWith(invite.url)
    expect(await screen.findByRole('button', { name: 'Скопировано' })).toBeInTheDocument()
  })

  it('without an invitation to show, goes back to the tab', () => {
    renderScreen(<Invite />, { route: '/links/invite' })
    expect(within(document.body).getByTestId('elsewhere')).toHaveTextContent('/links')
  })
})
