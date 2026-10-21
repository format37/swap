import type { ReactNode } from 'react'

/** An empty screen that explains the product instead of just being empty (§11). */
export function EmptyState({
  icon,
  title,
  steps,
}: {
  icon: ReactNode
  title: string
  steps: string[]
}) {
  return (
    <div className="flex flex-col items-center gap-4 px-6 py-8 text-center">
      <span className="text-hint">{icon}</span>
      <h2 className="text-lg font-semibold">{title}</h2>
      <ol className="flex flex-col gap-2 text-left">
        {steps.map((step, index) => (
          <li key={step} className="flex items-start gap-3">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-button text-sm font-semibold text-button-text">
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
