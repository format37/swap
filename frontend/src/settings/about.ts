/** The public page with the agreement and the privacy policy (QUESTIONS K3). */
export function privacyUrl(): string {
  return new URL('/privacy', window.location.href).toString()
}

/** The owner's address for anything about Swap, as the owner wrote it (QUESTIONS K9). */
export const DEVELOPER_EMAIL = 'format37@gmail.com'
