import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' })
const geistMono = Geist_Mono({ subsets: ['latin'], variable: '--font-geist-mono' })

export const metadata: Metadata = {
  title: 'NVIDIA FP&A Terminal | Institutional Valuation Platform',
  description:
    'Institutional-grade FP&A and DCF valuation platform for NVIDIA. Gordon Growth DCF, scenario analysis, 3-statement model, KPI signals, and comparable company analysis built on 10-K SEC filings.',
}

export const viewport: Viewport = {
  themeColor: '#0a0e12',
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`bg-background ${geist.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
