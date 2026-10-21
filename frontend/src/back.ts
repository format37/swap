import { useEffect } from 'react'

let override: (() => void) | null = null

/** What BackButton does now: the screen's own step back, if it has one (see App). */
export function backOverride(): (() => void) | null {
  return override
}

/**
 * Lets a screen with steps of its own, such as the wizard, take BackButton over while it
 * isn't on its first step. History then holds the screen once, whatever its step.
 */
export function useBackOverride(handler: (() => void) | null): void {
  useEffect(() => {
    override = handler
    return () => {
      override = null
    }
  }, [handler])
}
