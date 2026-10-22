import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from './client'
import type { components } from './schema'

export type Network = components['schemas']['Network']

/**
 * Who is one, two and three handshakes away, and how many are farther (ADR-0028): the
 * wizard's rings, and who an order's reach will reach.
 */
export function useNetwork() {
  return useQuery({ queryKey: ['network'], queryFn: () => unwrap(api.GET('/api/v1/network')) })
}

/** How many will see an order of `reach`: the author's links, and how many beyond them. */
export function audience(network: Network, reach: number | null): { links: number; more: number } {
  const ring = (distance: number) =>
    network.rings.find((each) => each.distance === distance)?.people.length ?? 0
  const furthest = reach ?? 3
  let more = 0
  for (let distance = 2; distance <= furthest; distance++) more += ring(distance)
  if (reach === null) more += network.farther
  return { links: reach === 0 ? 0 : ring(1), more }
}
