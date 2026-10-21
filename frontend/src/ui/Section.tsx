import type { ReactNode } from 'react'

export function Section({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="mx-4">
      {title && (
        <h2 className="mb-1.5 px-4 text-[0.8125rem] font-medium tracking-wide text-hint uppercase">
          {title}
        </h2>
      )}
      <div className="divide-y divide-separator overflow-hidden rounded-xl bg-section-bg">
        {children}
      </div>
    </section>
  )
}
