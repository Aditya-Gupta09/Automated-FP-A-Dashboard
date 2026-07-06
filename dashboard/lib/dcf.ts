// ============================================================
// Client-side live DCF revaluation engine.
// A simplified FCFF model calibrated so that base-case driver
// settings exactly reproduce the Python engine's base-case
// enterprise value ($2,619,625M -> $109.16/share).
// FCFF = Revenue x FCFF-conversion margin, adjusted for gross
// margin and CapEx deltas at the driver level; Gordon Growth
// terminal value; end-of-year discounting.
// ============================================================

import {
  DCF_OUTPUTS,
  DILUTED_SHARES_M,
  NET_CASH_USDM,
  SEGMENT_FY2025,
  SEGMENT_GROWTH_PATH,
  SEGMENTS,
  type SegmentKey,
} from './data'

export interface DriverInputs {
  waccPct: number // e.g. 12.91
  terminalGrowthPct: number // e.g. 3.675
  dcGrowthFy26Pct: number // e.g. 69
  grossMarginDeltaPct: number // delta vs base, e.g. 0 / +5 / -11
  capexPctRev: number // e.g. 3.0
}

export const BASE_DRIVERS: DriverInputs = {
  waccPct: 12.91,
  terminalGrowthPct: 3.675,
  dcGrowthFy26Pct: 69,
  grossMarginDeltaPct: 0,
  capexPctRev: 3.0,
}

// FCFF conversion margins for the 5 forecast years (pre-calibration)
const RAW_FCFF_MARGIN = [0.47, 0.505, 0.52, 0.53, 0.545]
const BASE_TAX = 0.145
const BASE_CAPEX_PCT = 3.0

function revenuePath(dcGrowthFy26: number): number[] {
  const years = [0, 1, 2, 3, 4]
  const totals = [0, 0, 0, 0, 0]
  for (const seg of SEGMENTS) {
    const key = seg.key as SegmentKey
    let prev = SEGMENT_FY2025[key]
    const growth = [...SEGMENT_GROWTH_PATH[key].base]
    if (key === 'data_center') growth[0] = dcGrowthFy26
    for (const i of years) {
      prev = prev * (1 + growth[i])
      totals[i] += prev
    }
  }
  return totals
}

interface EngineResult {
  revenue: number[]
  fcff: number[]
  pvFcf: number[]
  sumPvFcf: number
  terminalValue: number
  pvTerminalValue: number
  enterpriseValue: number
  equityValue: number
  impliedSharePrice: number
}

function runRaw(inputs: DriverInputs, k: number): EngineResult {
  const wacc = inputs.waccPct / 100
  const g = inputs.terminalGrowthPct / 100
  const revenue = revenuePath(inputs.dcGrowthFy26Pct / 100)

  const gmDelta = inputs.grossMarginDeltaPct / 100
  const capexDelta = (inputs.capexPctRev - BASE_CAPEX_PCT) / 100

  const fcff = revenue.map((rev, i) => {
    const baseMargin = RAW_FCFF_MARGIN[i] * k
    const adj = gmDelta * (1 - BASE_TAX) - capexDelta
    return rev * (baseMargin + adj)
  })

  const pvFcf = fcff.map((f, i) => f / Math.pow(1 + wacc, i + 1))
  const sumPvFcf = pvFcf.reduce((a, b) => a + b, 0)

  const spread = Math.max(wacc - g, 0.005)
  const terminalValue = (fcff[4] * (1 + g)) / spread
  const pvTerminalValue = terminalValue / Math.pow(1 + wacc, 5)

  const enterpriseValue = sumPvFcf + pvTerminalValue
  const equityValue = enterpriseValue + NET_CASH_USDM
  const impliedSharePrice = equityValue / DILUTED_SHARES_M

  return {
    revenue,
    fcff,
    pvFcf,
    sumPvFcf,
    terminalValue,
    pvTerminalValue,
    enterpriseValue,
    equityValue,
    impliedSharePrice,
  }
}

// Calibration scalar: force base drivers to reproduce the engine's base EV
const _baseUncalibrated = runRaw(BASE_DRIVERS, 1)
const CALIBRATION_K = DCF_OUTPUTS.base.enterpriseValueUsdm / _baseUncalibrated.enterpriseValue

export function runLiveDcf(inputs: DriverInputs): EngineResult {
  return runRaw(inputs, CALIBRATION_K)
}

// ---- 9x9 sensitivity grid (WACC x terminal g) ----
export const SENSITIVITY_WACC = [10.91, 11.41, 11.91, 12.41, 12.91, 13.41, 13.91, 14.41, 14.91]
export const SENSITIVITY_G = [2.0, 2.5, 3.0, 3.5, 3.675, 4.0, 4.5, 5.0, 5.5]

export function sensitivityGrid(baseInputs: DriverInputs): number[][] {
  return SENSITIVITY_WACC.map((w) =>
    SENSITIVITY_G.map((g) => {
      if (w / 100 - g / 100 < 0.005) return NaN
      return runLiveDcf({ ...baseInputs, waccPct: w, terminalGrowthPct: g }).impliedSharePrice
    }),
  )
}
