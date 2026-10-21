import type { ReactNode } from 'react'

export interface Tab {
  path: string
  label: string
  icon: ReactNode
}

/** The bottom tabs (Q-B14): an icon and a word each, the current one in the accent. */
export function TabBar({
  tabs,
  current,
  onSelect,
}: {
  tabs: Tab[]
  current: string
  onSelect: (path: string) => void
}) {
  return (
    <nav className="tab-bar fixed inset-x-0 bottom-0 z-10 border-t border-separator bg-bg">
      <ul className="mx-auto flex max-w-xl">
        {tabs.map((tab) => {
          const selected = tab.path === current
          return (
            <li key={tab.path} className="flex-1">
              <button
                type="button"
                aria-current={selected ? 'page' : undefined}
                onClick={() => {
                  onSelect(tab.path)
                }}
                className={`flex w-full flex-col items-center gap-0.5 py-2 text-xs font-medium ${selected ? 'text-accent' : 'text-hint'}`}
              >
                {tab.icon}
                {tab.label}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
