import type { ReactNode } from 'react'

export function Panel({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-md border border-border bg-card ${className}`}>
      {children}
    </div>
  )
}

export function SectionHeader({
  title,
  sub,
  right,
}: {
  title: string
  sub?: string
  right?: ReactNode
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <h2 className="text-sm font-semibold tracking-tight text-foreground text-balance">
          {title}
        </h2>
        {sub ? (
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {sub}
          </p>
        ) : null}
      </div>
      {right}
    </div>
  )
}

export function MonoLabel({ children }: { children: ReactNode }) {
  return (
    <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
      {children}
    </span>
  )
}

export function KeyValueRow({
  label,
  value,
  valueClass = 'text-foreground',
  border = true,
}: {
  label: string
  value: ReactNode
  valueClass?: string
  border?: boolean
}) {
  return (
    <div
      className={`flex items-center justify-between gap-4 py-1.5 ${border ? 'border-b border-border/60' : ''}`}
    >
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`font-mono text-xs font-semibold ${valueClass}`}>{value}</span>
    </div>
  )
}

export function SignalDot({ color }: { color: string }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-2 w-2 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  )
}

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: '#10161c',
  border: '1px solid #1e2832',
  borderRadius: 6,
  fontSize: 11,
  fontFamily: 'var(--font-geist-mono)',
  color: '#e6ebf0',
} as const

export const AXIS_STYLE = {
  fontSize: 10,
  fill: '#8496a8',
  fontFamily: 'var(--font-geist-mono)',
} as const
