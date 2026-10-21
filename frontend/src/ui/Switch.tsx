/** An on/off row (role switch), for a choice that is yes or no. */
export function Switch({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => {
        onChange(!checked)
      }}
      className="flex min-h-12 w-full items-center gap-3 px-4 py-2 text-left"
    >
      <span className="flex-1">{label}</span>
      <span
        aria-hidden
        className={`flex h-7 w-12 shrink-0 items-center rounded-full p-0.5 transition-colors ${checked ? 'bg-button' : 'bg-secondary-bg'}`}
      >
        <span
          className={`size-6 rounded-full bg-bg shadow transition-transform ${checked ? 'translate-x-5' : ''}`}
        />
      </span>
    </button>
  )
}
