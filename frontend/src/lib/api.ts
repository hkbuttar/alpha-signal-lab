const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type Snapshot = { date: string; equity: number; cash: number }
export type Position = { ticker: string; shares: number; sector: string }
export type SectorExposure = { sector: string; shares: number }

export type BacktestRunsResponse = {
  runs: string[]
  sample_metrics: Record<string, unknown> | null
}
export type BacktestRunResponse = {
  equity: { date: string; equity: number }[]
  metrics: Record<string, number | boolean | string>
}
export type RollingRisk = {
  dates: string[]
  rolling_sharpe: (number | null)[]
  drawdown: (number | null)[]
  historical_var: number | null
  parametric_var: number | null
}
export type LatestPositions = {
  date: string | null
  positions: Position[]
  sector_exposure: SectorExposure[]
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`${path} failed with status ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  snapshots: () => getJSON<{ snapshots: Snapshot[] }>('/api/snapshots'),
  latestPositions: () => getJSON<LatestPositions>('/api/positions/latest'),
  backtestRuns: () => getJSON<BacktestRunsResponse>('/api/backtest/runs'),
  backtestRun: (runId: string) => getJSON<BacktestRunResponse>(`/api/backtest/${runId}`),
  rollingRisk: () => getJSON<RollingRisk>('/api/risk/rolling'),
}