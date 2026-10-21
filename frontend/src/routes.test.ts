import { startRoute } from './routes'

const ID = '6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11'

it.each([
  [`link_${ID}`, `/links/${ID}`],
  [undefined, null],
  ['', null],
  [`spaceship_${ID}`, null],
  ['link_not-a-uuid', null],
  [`link_${ID}_more`, null],
])('startapp=%s opens %s', (param, route) => {
  expect(startRoute(param)).toBe(route)
})
