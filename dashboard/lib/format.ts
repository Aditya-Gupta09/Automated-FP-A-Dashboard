export function fmtUsd(v: number, digits = 2): string {
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`
}

export function fmtM(v: number): string {
  return `$${Math.round(v).toLocaleString('en-US')}M`
}

export function fmtB(v: number, digits = 1): string {
  return `$${(v / 1000).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}B`
}

export function fmtPct(v: number, digits = 1): string {
  return `${(v * 100).toFixed(digits)}%`
}

export function fmtX(v: number, digits = 1): string {
  return `${v.toFixed(digits)}x`
}

export function fmtSignedPct(v: number, digits = 0): string {
  const s = (v * 100).toFixed(digits)
  return v >= 0 ? `+${s}%` : `${s}%`
}
