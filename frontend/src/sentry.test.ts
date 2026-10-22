import { withoutLaunchData } from './sentry'

const HASH =
  '#tgWebAppData=user%3D%257B%2522id%2522%253A42%257D%26hash%3Dabc123&tgWebAppVersion=8.0'

afterEach(() => {
  window.location.hash = ''
})

it('drops the launch data from every URL in a report', () => {
  window.location.hash = HASH
  const href = window.location.href
  const event = {
    request: { url: href },
    breadcrumbs: [{ category: 'navigation', data: { from: href, to: '/api/v1/me' } }],
    exception: { values: [{ value: `failed at ${href}` }] },
  }

  const sent = JSON.stringify(withoutLaunchData(event))

  expect(sent).not.toContain('tgWebAppData')
  expect(sent).not.toContain('abc123')
  expect(sent).toContain('/api/v1/me')
})

it('leaves a report alone when there is no hash', () => {
  const event = { request: { url: 'https://swap.latentstate.dev/' } }
  expect(withoutLaunchData(event)).toEqual(event)
})
