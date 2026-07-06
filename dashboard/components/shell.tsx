'use client'

import {
  DCF_OUTPUTS,
  MARKET_PRICE_USD,
  SCENARIO_ASSUMPTIONS,
  SCENARIO_META,
  SCENARIOS,
  VALUATION_DATE,
  type Scenario,
} from '@/lib/data'
import { fmtUsd } from '@/lib/format'
import {
  Activity,
  BarChart3,
  Calculator,
  Landmark,
  Layers,
  Menu,
  TrendingUp,
  X,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'

export type TabKey = 'valuation' | 'segments' | 'three_statement' | 'kpis' | 'comps'

const TABS: { key: TabKey; label: string; icon: typeof Calculator }[] = [
  { key: 'valuation', label: 'Valuation', icon: Calculator },
  { key: 'segments', label: 'Revenue & Segments', icon: Layers },
  { key: 'three_statement', label: '3-Statement', icon: Landmark },
  { key: 'kpis', label: 'KPIs & Ratios', icon: Activity },
  { key: 'comps', label: 'Comps', icon: BarChart3 },
]

const DIR_BADGE: Record<'up' | 'down' | 'flat', { char: string; cls: string }> = {
  up: { char: '\u25B2', cls: 'text-positive' },
  down: { char: '\u25BC', cls: 'text-negative' },
  flat: { char: '\u2014', cls: 'text-muted-foreground' },
}

export function Shell({
  scenario,
  onScenarioChange,
  tab,
  onTabChange,
  children,
}: {
  scenario: Scenario
  onScenarioChange: (s: Scenario) => void
  tab: TabKey
  onTabChange: (t: TabKey) => void
  children: ReactNode
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const active = DCF_OUTPUTS[scenario]
  const premium = MARKET_PRICE_USD / active.impliedSharePriceUsd - 1

  const sidebar = (
    <div className="flex h-full flex-col">
      {/* Brand */}
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
            <TrendingUp className="h-4.5 w-4.5 text-primary-foreground" aria-hidden="true" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight text-foreground">
              NVIDIA FP&amp;A
            </div>
            <div className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
              Valuation Terminal v4.0
            </div>
          </div>
        </div>
      </div>

      {/* Scenario switcher */}
      <div className="border-b border-border px-4 py-4">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Scenario
        </div>
        <div className="flex flex-col gap-1.5">
          {SCENARIOS.map((s) => {
            const meta = SCENARIO_META[s]
            const isActive = s === scenario
            return (
              <button
                key={s}
                type="button"
                onClick={() => onScenarioChange(s)}
                aria-pressed={isActive}
                className={`flex items-center justify-between gap-2 rounded border px-3 py-2 text-left transition-colors ${
                  isActive
                    ? 'border-primary/50 bg-primary/10'
                    : 'border-border bg-transparent hover:bg-muted/50'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="inline-block h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span
                    className={`text-xs font-medium ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}
                  >
                    {meta.label}
                  </span>
                </span>
                <span
                  className="font-mono text-[11px] font-semibold"
                  style={{ color: meta.color }}
                >
                  {fmtUsd(DCF_OUTPUTS[s].impliedSharePriceUsd)}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Active assumptions */}
      <div className="border-b border-border px-4 py-4">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Active assumptions
        </div>
        <div className="flex flex-col">
          {SCENARIO_ASSUMPTIONS[scenario].map((a) => {
            const b = DIR_BADGE[a.dir]
            return (
              <div
                key={a.label}
                className="flex items-center justify-between border-b border-border/50 py-1.5 last:border-b-0"
              >
                <span className="text-[11px] text-muted-foreground">{a.label}</span>
                <span className="flex items-center gap-1.5 font-mono text-[11px] font-semibold text-foreground">
                  {a.value}
                  <span className={`text-[9px] ${b.cls}`} aria-hidden="true">
                    {b.char}
                  </span>
                </span>
              </div>
            )
          })}
          <div className="flex items-center justify-between py-1.5">
            <span className="text-[11px] text-muted-foreground">Diluted shares</span>
            <span className="font-mono text-[11px] font-semibold text-foreground">24,300M</span>
          </div>
        </div>
      </div>

      {/* Market context */}
      <div className="px-4 py-4">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Market context
        </div>
        <div className="rounded border border-border bg-muted/30 p-3">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] text-muted-foreground">NVDA market</span>
            <span className="font-mono text-sm font-bold text-foreground">
              {fmtUsd(MARKET_PRICE_USD)}
            </span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-[11px] text-muted-foreground">vs intrinsic</span>
            <span
              className={`font-mono text-xs font-semibold ${premium > 0 ? 'text-negative' : 'text-positive'}`}
            >
              {premium > 0 ? '+' : ''}
              {(premium * 100).toFixed(1)}% {premium > 0 ? 'premium' : 'discount'}
            </span>
          </div>
          <div className="mt-2 border-t border-border/60 pt-2 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
            Valuation date {VALUATION_DATE}
          </div>
        </div>
      </div>

      <div className="mt-auto border-t border-border px-4 py-3">
        <p className="font-mono text-[9px] leading-relaxed text-muted-foreground">
          Source: NVIDIA 10-K SEC filings FY2020&ndash;FY2025 &middot; Gordon Growth DCF &middot;
          end-of-year discounting
        </p>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-border bg-card lg:block">
        {sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close sidebar"
            className="absolute inset-0 bg-background/80"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-border bg-card">
            <button
              type="button"
              aria-label="Close sidebar"
              className="absolute right-3 top-3 z-10 rounded p-1 text-muted-foreground hover:text-foreground"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
            {sidebar}
          </aside>
        </div>
      ) : null}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
          <div className="flex items-center justify-between gap-4 px-4 py-2.5 md:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Open sidebar"
                className="rounded p-1 text-muted-foreground hover:text-foreground lg:hidden"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-5 w-5" aria-hidden="true" />
              </button>
              <div>
                <div className="text-xs font-semibold tracking-tight text-foreground">
                  NVDA &middot; NVIDIA Corporation
                </div>
                <div className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                  FP&amp;A &amp; Intrinsic Valuation Platform
                </div>
              </div>
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Model live &middot; WACC 12.91% &middot; g 3.675%
              </span>
            </div>
          </div>

          {/* Tab nav */}
          <nav aria-label="Dashboard sections" className="flex overflow-x-auto px-4 md:px-6">
            {TABS.map((t) => {
              const isActive = t.key === tab
              const Icon = t.icon
              return (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => onTabChange(t.key)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors ${
                    isActive
                      ? 'border-primary text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {t.label}
                </button>
              )
            })}
          </nav>
        </header>

        <main className="flex-1 px-4 py-5 md:px-6">{children}</main>

        <footer className="border-t border-border px-4 py-3 md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
              NVIDIA FP&amp;A Platform v4.0 &middot; Institutional Edition
            </span>
            <span className="font-mono text-[9px] uppercase tracking-widest text-primary">
              Data provenance: SEC EDGAR 10-K &middot; assumptions.json v1.0
            </span>
          </div>
        </footer>
      </div>
    </div>
  )
}
