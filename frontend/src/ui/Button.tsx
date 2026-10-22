import type { ButtonHTMLAttributes, ReactNode } from 'react'

const TONES = {
  plain: 'bg-section-bg text-link',
  destructive: 'bg-section-bg text-destructive',
  // The button colour of Telegram's theme: for an action inside a card of section colour.
  filled: 'bg-button text-button-text',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
  tone?: keyof typeof TONES
}

/**
 * An action on the page itself. The screen's main action is Telegram's MainButton
 * (ADR-0003); this is for the others, such as «Отклонить».
 */
export function Button({ icon, tone = 'plain', children, className = '', ...button }: ButtonProps) {
  return (
    <button
      type="button"
      className={`flex min-h-12 w-full items-center justify-center gap-2 rounded-xl px-4 py-3 font-medium active:opacity-70 disabled:opacity-50 ${TONES[tone]} ${className}`}
      {...button}
    >
      {icon}
      {children}
    </button>
  )
}
