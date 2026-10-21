import {
  backButton,
  hapticFeedback,
  init,
  isTMA,
  miniApp,
  retrieveLaunchParams,
  retrieveRawInitData,
  themeParams,
  viewport,
} from '@tma.js/sdk-react'

export interface Launch {
  initDataRaw: string | undefined
  languageCode: string | undefined
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
  // In fullscreen, Telegram draws its buttons over the page: the layout pads by the
  // insets this binds as CSS variables (ADR-0003).
  attempt(() => {
    viewport
      .mount()
      .then(() => {
        attempt(() => viewport.bindCssVars())
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
  }
}

/** The light tick native pickers give; nothing outside Telegram. */
export function hapticSelect(): void {
  attempt(() => {
    if (hapticFeedback.selectionChanged.isAvailable()) hapticFeedback.selectionChanged()
  })
}
