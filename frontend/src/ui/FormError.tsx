import type { ReactNode } from 'react'

/**
 * What stops a form, kept in sight just above Telegram's MainButton however far the form
 * is scrolled. At the end of a long form it went unseen, and «Отправить предложение»
 * seemed to do nothing (QUESTIONS G5).
 */
export function FormError({ children }: { children: ReactNode }) {
  if (!children) return null
  return (
    <p
      role="alert"
      className="fixed inset-x-0 bottom-0 z-20 border-t border-separator bg-section-bg px-6 py-3 text-destructive"
    >
      {children}
    </p>
  )
}
