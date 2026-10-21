import type { FlagCode } from '../ui/Flag'

interface Look {
  symbol: string
  /** Fiat only: the flag beside it (ADR-0003). */
  flag?: FlagCode
  /** Where it is at home: the wizard's first guess of a country. */
  home?: string
}

const LOOKS: Partial<Record<string, Look>> = {
  RUB: { symbol: '₽', flag: 'RU', home: 'RU' },
  GEL: { symbol: '₾', flag: 'GE', home: 'GE' },
  USD: { symbol: '$', flag: 'US' },
  EUR: { symbol: '€', flag: 'EU' },
  TRY: { symbol: '₺', flag: 'TR', home: 'TR' },
  KZT: { symbol: '₸', flag: 'KZ', home: 'KZ' },
  AMD: { symbol: '֏', flag: 'AM', home: 'AM' },
  USDT: { symbol: '₮' },
  USDC: { symbol: '$' },
}

/** A configured asset we know nothing about still shows its code. */
export function look(code: string): Look {
  return LOOKS[code] ?? { symbol: '' }
}

/** For a native <option>, which can't hold a flag: «₽ RUB». */
export function assetText(code: string): string {
  const { symbol } = look(code)
  return symbol ? `${symbol} ${code}` : code
}
