// Fails the build when the JS and CSS that ship exceed the budget (ADR-0003, §7).
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const BUDGET_KB = 300
const assets = 'dist/assets'

let total = 0
for (const name of readdirSync(assets).sort()) {
  if (!/\.(js|css)$/.test(name)) continue
  const size = gzipSync(readFileSync(join(assets, name)), { level: 9 }).length
  total += size
  console.log(`${(size / 1024).toFixed(1).padStart(7)} KB  ${name}`)
}
console.log(`${(total / 1024).toFixed(1).padStart(7)} KB  total gzip (budget ${BUDGET_KB} KB)`)
if (total > BUDGET_KB * 1024) {
  console.error('Over budget.')
  process.exit(1)
}
