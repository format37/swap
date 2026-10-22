/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Error reports go to this DSN; a build without one sends none (ADR-0025). */
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_SENTRY_RELEASE?: string
}
