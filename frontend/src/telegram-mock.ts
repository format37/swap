import { emitEvent, mockTelegramEnv } from '@tma.js/sdk-react'

/**
 * Dev only (main.tsx imports it behind import.meta.env.DEV): lets a desktop browser,
 * opened with signed launch parameters in its URL, stand in for Telegram. The api still
 * validates those parameters for real; `python -m swap.tools.dev_launch` makes them.
 *
 * It also draws the parts Telegram draws itself (MainButton, BackButton and popups) as
 * plain DOM, so they can be clicked in Chrome. The app's own code is the same as in
 * Telegram.
 */
export function mockTelegramForDev(): void {
  const inTelegram = 'TelegramWebviewProxy' in window || window.self !== window.top
  if (inTelegram || !window.location.hash.includes('tgWebAppData=')) return

  // On a reload the SDK restores its buttons from sessionStorage and tells Telegram
  // nothing, but the stand-ins below start out empty. Start every load afresh.
  sessionStorage.clear()
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
      } else if (event.name === 'web_app_setup_main_button') {
        drawMainButton(event.params as MainButtonParams)
      } else if (event.name === 'web_app_setup_back_button') {
        drawBackButton((event.params as { is_visible?: boolean }).is_visible ?? false)
      } else if (event.name === 'web_app_open_popup') {
        drawPopup(event.params as PopupParams)
      } else if (event.name === 'web_app_open_tg_link') {
        console.info('[telegram-mock] would open', event.params)
      }
    },
  })
}

interface MainButtonParams {
  is_visible?: boolean
  is_active?: boolean
  is_progress_visible?: boolean
  text?: string
}

interface PopupParams {
  title?: string
  message: string
  buttons?: { id: string; type?: string; text?: string }[]
}

const STYLE = {
  bar: 'position:fixed;left:0;right:0;bottom:0;padding:8px 12px;background:var(--tg-theme-bottom-bar-bg-color,#fff);border-top:1px solid #8884;z-index:1000',
  button:
    'width:100%;height:46px;border:0;border-radius:10px;font:600 15px system-ui;background:var(--tg-theme-button-color,#3390ec);color:var(--tg-theme-button-text-color,#fff)',
  back: 'position:fixed;left:8px;top:8px;z-index:1000;border:0;border-radius:16px;padding:6px 12px;font:500 14px system-ui;background:#0008;color:#fff',
  scrim:
    'position:fixed;inset:0;background:#0006;display:flex;align-items:center;justify-content:center;z-index:1001',
  popup:
    'background:var(--tg-theme-bg-color,#fff);color:var(--tg-theme-text-color,#000);border-radius:14px;padding:16px;max-width:300px;font:15px system-ui',
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  id: string,
  style: string,
): HTMLElementTagNameMap[K] {
  const existing = document.getElementById(id)
  if (existing) return existing as HTMLElementTagNameMap[K]
  const created = document.createElement(tag)
  created.id = id
  created.style.cssText = style
  document.body.append(created)
  return created
}

const state: MainButtonParams = {}

function drawMainButton(params: MainButtonParams): void {
  Object.assign(state, params)
  const bar = element('div', 'tg-mock-main-bar', STYLE.bar)
  const button = bar.querySelector('button') ?? bar.appendChild(document.createElement('button'))
  button.style.cssText = STYLE.button
  button.dataset.testid = 'telegram-main-button'
  button.textContent = state.is_progress_visible ? '…' : (state.text ?? '')
  button.disabled = state.is_active === false
  button.style.opacity = button.disabled ? '0.6' : '1'
  button.onclick = () => {
    emitEvent('main_button_pressed')
  }
  bar.style.display = state.is_visible ? 'block' : 'none'
  // Telegram shrinks the page above its button. A transform makes #root the box that
  // fixed elements such as the tab bar sit in, so the page shrinks here too.
  const root = document.getElementById('root')
  if (root)
    root.style.cssText = state.is_visible
      ? 'position:fixed;inset:0 0 63px 0;overflow:auto;transform:translateZ(0)'
      : ''
}

function drawBackButton(visible: boolean): void {
  const button = element('button', 'tg-mock-back', STYLE.back)
  button.textContent = '‹ Back'
  button.onclick = () => {
    emitEvent('back_button_pressed')
  }
  button.style.display = visible ? 'block' : 'none'
}

function drawPopup(params: PopupParams): void {
  const scrim = element('div', 'tg-mock-popup', STYLE.scrim)
  scrim.replaceChildren()
  const box = document.createElement('div')
  box.style.cssText = STYLE.popup
  box.setAttribute('role', 'dialog')
  const message = document.createElement('p')
  message.textContent = params.message
  message.style.margin = '0 0 12px'
  box.append(message)
  for (const button of params.buttons ?? [{ id: 'ok', type: 'ok' }]) {
    const choice = document.createElement('button')
    choice.textContent = button.text ?? (button.type === 'cancel' ? 'Cancel' : 'OK')
    choice.style.cssText = `margin:4px 8px 0 0;padding:8px 12px;border-radius:8px;border:1px solid #8886;background:none;color:${button.type === 'destructive' ? '#e53935' : 'inherit'};font:inherit`
    choice.onclick = () => {
      scrim.remove()
      emitEvent('popup_closed', { button_id: button.id })
    }
    box.append(choice)
  }
  scrim.append(box)
}
