import { emitEvent, mockTelegramEnv } from '@tma.js/sdk-react'

/**
 * Dev only (main.tsx imports it behind import.meta.env.DEV): lets a desktop browser,
 * opened with signed launch parameters in its URL, stand in for Telegram. The api still
 * validates those parameters for real; `python -m swap.tools.dev_launch` makes them.
 */
export function mockTelegramForDev(): void {
  const inTelegram = 'TelegramWebviewProxy' in window || window.self !== window.top
  if (inTelegram || !window.location.hash.includes('tgWebAppData=')) return

  const launchParams = new URLSearchParams(window.location.hash.slice(1))
  const themeParams: unknown = JSON.parse(launchParams.get('tgWebAppThemeParams') ?? '{}')
  const noInsets = { top: 0, bottom: 0, left: 0, right: 0 }
  mockTelegramEnv({
    launchParams,
    onEvent(event) {
      // Answer what the SDK waits for at start, the way Telegram does.
      if (event.name === 'web_app_request_viewport') {
        emitEvent('viewport_changed', {
          height: window.innerHeight,
          width: window.innerWidth,
          is_expanded: true,
          is_state_stable: true,
        })
      } else if (event.name === 'web_app_request_theme') {
        emitEvent('theme_changed', { theme_params: themeParams as Record<string, `#${string}`> })
      } else if (event.name === 'web_app_request_safe_area') {
        emitEvent('safe_area_changed', noInsets)
      } else if (event.name === 'web_app_request_content_safe_area') {
        emitEvent('content_safe_area_changed', noInsets)
      }
    },
  })
}
