import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import { setLaunchInitData } from './api/client'
import { startSentry } from './sentry'
import { startTelegram } from './telegram'
import './styles.css'

if (import.meta.env.DEV) {
  // Never in a production build: Vite drops this branch, mock and all.
  const { mockTelegramForDev } = await import('./telegram-mock')
  mockTelegramForDev()
}

startSentry()
const launch = startTelegram()
setLaunchInitData(launch?.initDataRaw)

const root = document.getElementById('root')
if (!root) throw new Error('index.html has no #root')
createRoot(root).render(
  <StrictMode>
    <App launch={launch} />
  </StrictMode>,
)
