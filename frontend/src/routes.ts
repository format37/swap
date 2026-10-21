/** Where each kind of start parameter leads (ADR-0013). Later slices add orders and deals. */
const BY_KIND: Partial<Record<string, (id: string) => string>> = {
  link: (id) => `/links/${id}`,
}

const START_PARAM = /^([a-z]+)_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/

/** The screen a launch's `startapp=<kind>_<id>` opens; null for Home. */
export function startRoute(param: string | undefined): string | null {
  const match = START_PARAM.exec(param ?? '')
  if (!match?.[1] || !match[2]) return null
  return BY_KIND[match[1]]?.(match[2]) ?? null
}
