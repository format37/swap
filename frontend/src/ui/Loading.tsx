/** While a screen's data is on its way: the app's icon, breathing. */
export function Loading() {
  return (
    <div aria-busy className="flex flex-1 items-center justify-center py-16">
      <img src="/icon.svg" alt="" width={48} height={48} className="animate-pulse" />
    </div>
  )
}
