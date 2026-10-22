import type { Me } from '../api/client'
import type { Network } from '../api/network'
import { useI18n } from '../i18n/useI18n'
import { Avatar } from '../ui/Avatar'

type Shown = Network['rings'][number]['people'][number]

// The picture is 320 units wide: the author in the middle, then a ring per handshake.
const SIZE = 320
const RADII = [0, 62, 106, 148]
// How many faces fit around each ring before a «+N» stands in for the rest.
const FACES = [0, 6, 9, 12]

/**
 * Who an order reaches, as rings around its author, one per handshake, with faces and
 * first names (QUESTIONS J2, ADR-0028). Rings within the reach are drawn whole, the rest
 * faint. Plain SVG for the rings and the app's own avatars over them: a web of lines stops
 * being readable on a phone at about fifteen people, and a graph library would cost the
 * budget (ADR-0003).
 */
export function Rings({ me, network, reach }: { me: Me; network: Network; reach: number | null }) {
  const { t } = useI18n()
  const furthest = reach ?? 3
  return (
    <div className="mx-4" aria-hidden>
      <div className="relative mx-auto aspect-square w-full max-w-80">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="absolute inset-0 size-full">
          {[1, 2, 3].map((distance) => (
            <circle
              key={distance}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADII[distance]}
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeDasharray={distance <= furthest ? undefined : '4 5'}
              className={distance <= furthest ? 'text-accent' : 'text-hint opacity-40'}
            />
          ))}
        </svg>
        <Face person={me} x={0} y={0} size="sm" name={me.first_name} faint={false} />
        {network.rings.map((ring) => {
          const radius = RADII[ring.distance] ?? 0
          const room = FACES[ring.distance] ?? 0
          const shown = ring.people.length > room ? ring.people.slice(0, room - 1) : ring.people
          const rest = ring.people.length - shown.length
          const count = shown.length + (rest > 0 ? 1 : 0)
          // Each ring starts at a different angle, so faces don't line up across rings.
          const at = (index: number) => ((index / count) * 2 - 0.5 + ring.distance * 0.09) * Math.PI
          const faint = ring.distance > furthest
          return [
            ...shown.map((person, index) => (
              <Face
                key={person.id}
                person={person}
                x={(radius / SIZE) * Math.cos(at(index))}
                y={(radius / SIZE) * Math.sin(at(index))}
                size="xs"
                name={person.first_name}
                faint={faint}
              />
            )),
            rest > 0 && (
              <More
                key={`more-${ring.distance}`}
                count={rest}
                x={(radius / SIZE) * Math.cos(at(shown.length))}
                y={(radius / SIZE) * Math.sin(at(shown.length))}
                faint={faint}
              />
            ),
          ]
        })}
      </div>
      {reach === null && network.farther > 0 && (
        <p className="text-center text-sm text-hint">
          {t('reach.farther', { count: network.farther })}
        </p>
      )}
    </div>
  )
}

/** Where a face sits: (x, y) from the middle, as fractions of the picture's width. */
function place(x: number, y: number) {
  return { left: `${(0.5 + x) * 100}%`, top: `${(0.5 + y) * 100}%` }
}

function Face({
  person,
  x,
  y,
  size,
  name,
  faint,
}: {
  person: Pick<Shown, 'id' | 'first_name' | 'last_name' | 'photo_url'>
  x: number
  y: number
  size: 'xs' | 'sm'
  name: string
  faint: boolean
}) {
  return (
    <span
      style={place(x, y)}
      className={`absolute flex w-16 -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-0.5 ${faint ? 'opacity-40' : ''}`}
    >
      <Avatar
        name={[person.first_name, person.last_name].filter(Boolean).join(' ')}
        photo={person.photo_url}
        size={size}
      />
      <span className="w-full truncate text-center text-[0.6875rem] leading-tight">{name}</span>
    </span>
  )
}

function More({ count, x, y, faint }: { count: number; x: number; y: number; faint: boolean }) {
  return (
    <span
      style={place(x, y)}
      className={`absolute flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-secondary-bg text-xs font-semibold ${faint ? 'opacity-40' : ''}`}
    >
      +{count}
    </span>
  )
}
