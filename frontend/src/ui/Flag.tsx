import type { ReactNode } from 'react'

export type FlagCode = 'RU' | 'GE' | 'US' | 'EU' | 'TR' | 'KZ' | 'AM'

// A flag's colours are the flag itself, so these are the one place with colours of their
// own (ADR-0003). Simplified to what reads at 21×14 px.
const SMALL_CROSS = 'h1.2v1.4h1.4v1.2h-1.4v1.4h-1.2v-1.4h-1.4v-1.2h1.4z'

/** A five-pointed star's outline, its first point at `angle` degrees. */
function star(cx: number, cy: number, r: number, angle = -90): string {
  return Array.from({ length: 10 }, (_, i) => {
    const radius = i % 2 === 0 ? r : r * 0.4
    const a = ((angle + i * 36) * Math.PI) / 180
    return `${(cx + radius * Math.cos(a)).toFixed(2)},${(cy + radius * Math.sin(a)).toFixed(2)}`
  }).join(' ')
}

const FLAGS: Record<FlagCode, ReactNode> = {
  RU: (
    <>
      <rect width="30" height="20" fill="#fff" />
      <rect y="6.67" width="30" height="6.67" fill="#0039a6" />
      <rect y="13.33" width="30" height="6.67" fill="#d52b1e" />
    </>
  ),
  GE: (
    <>
      <rect width="30" height="20" fill="#fff" />
      <rect x="13" width="4" height="20" fill="#f00" />
      <rect y="8" width="30" height="4" fill="#f00" />
      <path
        fill="#f00"
        d={`M5.9 2.6${SMALL_CROSS}M22.9 2.6${SMALL_CROSS}M5.9 14.6${SMALL_CROSS}M22.9 14.6${SMALL_CROSS}`}
      />
    </>
  ),
  US: (
    <>
      <rect width="30" height="20" fill="#fff" />
      {Array.from({ length: 7 }, (_, stripe) => (
        <rect key={stripe} y={(stripe * 2 * 20) / 13} width="30" height={20 / 13} fill="#b22234" />
      ))}
      <rect width="12" height={(7 * 20) / 13} fill="#3c3b6e" />
    </>
  ),
  EU: (
    <>
      <rect width="30" height="20" fill="#039" />
      {Array.from({ length: 12 }, (_, star) => (
        <circle
          key={star}
          cx={15 + 6 * Math.sin((star * Math.PI) / 6)}
          cy={10 - 6 * Math.cos((star * Math.PI) / 6)}
          r="0.9"
          fill="#fc0"
        />
      ))}
    </>
  ),
  TR: (
    <>
      <rect width="30" height="20" fill="#e30a17" />
      <circle cx="11" cy="10" r="5" fill="#fff" />
      <circle cx="12.25" cy="10" r="4" fill="#e30a17" />
      <polygon fill="#fff" points={star(17.2, 10, 2.4, 180)} />
    </>
  ),
  KZ: (
    <>
      <rect width="30" height="20" fill="#00afca" />
      <circle cx="15" cy="9" r="3.5" fill="#fec50c" />
      <rect x="2" y="2" width="1.2" height="16" fill="#fec50c" />
    </>
  ),
  AM: (
    <>
      <rect width="30" height="20" fill="#f2a800" />
      <rect width="30" height="13.33" fill="#0033a0" />
      <rect width="30" height="6.67" fill="#d90012" />
    </>
  ),
}

/** A small flag beside a fiat currency, drawn here: Windows shows flag emoji as letters. */
export function Flag({ code }: { code: FlagCode }) {
  return (
    <svg
      viewBox="0 0 30 20"
      aria-hidden
      className="inline-block h-3.5 w-[1.3125rem] shrink-0 rounded-[2px] ring-1 ring-separator"
    >
      {FLAGS[code]}
    </svg>
  )
}
