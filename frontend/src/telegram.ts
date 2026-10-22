import {
  backButton,
  copyTextToClipboard,
  hapticFeedback,
  init,
  isTMA,
  mainButton,
  miniApp,
  popup,
  retrieveLaunchParams,
  retrieveRawInitData,
  shareURL,
  themeParams,
  viewport,
} from '@tma.js/sdk-react'
import { useEffect, useRef } from 'react'

export interface Launch {
  initDataRaw: string | undefined
  languageCode: string | undefined
  /** What the app was opened on, such as `link_<id>` (ADR-0013). */
  startParam: string | undefined
}

function attempt(step: () => void): void {
  try {
    step()
  } catch (error) {
    // An old client may lack a feature; the app works without any one of these.
    console.warn('Telegram feature unavailable', error)
  }
}

/** Connects to Telegram when the page runs inside it; null in a plain browser. */
export function startTelegram(): Launch | null {
  if (!isTMA()) return null
  try {
    init()
  } catch (error) {
    // Launch parameters with no Telegram around them, such as a launch URL opened in a
    // browser: show the way to Telegram rather than a blank page.
    console.warn('Not inside Telegram', error)
    return null
  }
  attempt(() => {
    miniApp.mount()
    miniApp.bindCssVars()
  })
  attempt(() => {
    themeParams.mount()
    themeParams.bindCssVars()
  })
  attempt(() => {
    backButton.mount()
  })
  attempt(() => {
    mainButton.mount()
  })
  // In fullscreen, Telegram draws its buttons over the page: the layout pads by the
  // insets this binds as CSS variables (ADR-0003). Opened from a chat button instead,
  // the app starts half-height, and the spec asks for the full height (§10).
  attempt(() => {
    viewport
      .mount()
      .then(() => {
        attempt(() => viewport.bindCssVars())
        attempt(() => {
          viewport.expand()
        })
      })
      .catch((error: unknown) => {
        console.warn('Telegram viewport unavailable', error)
      })
  })
  attempt(() => {
    miniApp.ready()
  })

  const params = retrieveLaunchParams()
  return {
    initDataRaw: retrieveRawInitData(),
    languageCode: params.tgWebAppData?.user?.language_code,
    startParam: params.tgWebAppStartParam,
  }
}

/** The light tick native pickers give; nothing outside Telegram. */
export function hapticSelect(): void {
  attempt(() => {
    if (hapticFeedback.selectionChanged.isAvailable()) hapticFeedback.selectionChanged()
  })
}

/** The buzz that says an action worked, or didn't. */
export function hapticNotify(kind: 'success' | 'error' | 'warning'): void {
  attempt(() => {
    if (hapticFeedback.notificationOccurred.isAvailable()) hapticFeedback.notificationOccurred(kind)
  })
}

export interface MainAction {
  text: string
  onClick: () => void
  disabled?: boolean
  /** Shows Telegram's spinner on the button, and ignores presses meanwhile. */
  busy?: boolean
}

/**
 * The screen's main action in Telegram's MainButton, for as long as the screen is
 * mounted (ADR-0003). `null` hides it.
 */
export function useMainButton(action: MainAction | null): void {
  const handler = useRef<(() => void) | undefined>(undefined)
  useEffect(() => {
    handler.current = action?.busy ? undefined : action?.onClick
  })
  const shown = action !== null
  const text = action?.text
  const enabled = !action?.disabled
  const busy = action?.busy ?? false

  useEffect(() => {
    if (!mainButton.isMounted() || text === undefined) return
    mainButton.setParams({
      text,
      isVisible: true,
      isEnabled: enabled && !busy,
      isLoaderVisible: busy,
    })
  }, [text, enabled, busy])

  useEffect(() => {
    if (!mainButton.isMounted() || !shown) return
    const off = mainButton.onClick(() => handler.current?.())
    return () => {
      off()
      mainButton.setParams({ isVisible: false, isLoaderVisible: false })
    }
  }, [shown])
}

/**
 * Telegram's native confirmation before an irreversible action (ADR-0003). Resolves
 * true when the user pressed `ok`.
 */
export async function confirmAction(
  message: string,
  ok: string,
  { destructive = false }: { destructive?: boolean } = {},
): Promise<boolean> {
  if (!popup.show.isAvailable()) return window.confirm(message)
  const pressed = await popup.show({
    message,
    buttons: [
      { id: 'ok', type: destructive ? 'destructive' : 'default', text: ok },
      { id: 'cancel', type: 'cancel' },
    ],
  })
  return pressed === 'ok'
}

/** A native popup that only explains something, with one button to close it. */
export async function explain(message: string): Promise<void> {
  if (!popup.show.isAvailable()) {
    window.alert(message)
    return
  }
  await popup.show({ message, buttons: [{ id: 'ok', type: 'ok' }] })
}

/** Telegram's share sheet for a link; false where there is none. */
export function shareLink(url: string, text: string): boolean {
  if (!shareURL.isAvailable()) return false
  shareURL(url, text)
  return true
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await copyTextToClipboard(text)
    return true
  } catch {
    return false
  }
}
