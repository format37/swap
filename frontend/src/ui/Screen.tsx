import type { ReactNode } from 'react'

/** A whole screen, clear of Telegram's buttons in fullscreen (see `.screen`). */
export function Screen({ children, tabs = false }: { children: ReactNode; tabs?: boolean }) {
  return (
    <main className={`screen mx-auto flex max-w-xl flex-col gap-4 ${tabs ? 'has-tab-bar' : ''}`}>
      {children}
    </main>
  )
}
