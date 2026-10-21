import type { ReactNode } from 'react'

/** A whole screen, clear of Telegram's buttons in fullscreen (see `.screen`). */
export function Screen({ children }: { children: ReactNode }) {
  return <main className="screen mx-auto flex max-w-xl flex-col gap-4">{children}</main>
}
