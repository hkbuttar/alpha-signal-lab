import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Snapshot } from '../lib/api'
import { EmptyState } from './Card'

type EquityChartProps = {
  liveSnapshots: Snapshot[]
  backtestEquity: { date: string; equity: number }[]
}

type MergedPoint = { date: string; live?: number; backtested?: number }
type EquityPoint = { date: string; equity: number }

// Live paper trading and backtests start from different capital bases, so raw
// dollar equity isn't comparable between them - index each series to its own
// first value and plot % return instead.
function toIndexedReturns(points: EquityPoint[]): EquityPoint[] {
  if (points.length === 0) return []
  const base = points[0].equity
  return points.map((p) => ({ date: p.date, equity: base ? (p.equity / base - 1) * 100 : 0 }))
}

function mergeSeries(live: EquityPoint[], backtest: EquityPoint[]): MergedPoint[] {
  const byDate = new Map<string, MergedPoint>()
  for (const point of backtest) {
    byDate.set(point.date, { date: point.date, backtested: point.equity })
  }
  for (const point of live) {
    const existing = byDate.get(point.date) ?? { date: point.date }
    existing.live = point.equity
    byDate.set(point.date, existing)
  }
  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))
}

const percentFormatter = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`

export function EquityChart({ liveSnapshots, backtestEquity }: EquityChartProps) {
  if (liveSnapshots.length === 0 && backtestEquity.length === 0) {
    return <EmptyState message="No equity data yet. Run a backtest and/or the live scheduler." />
  }

  const data = mergeSeries(toIndexedReturns(liveSnapshots), toIndexedReturns(backtestEquity))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="var(--baseline)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          minTickGap={40}
        />
        <YAxis
          stroke="var(--baseline)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          tickFormatter={(v: number) => percentFormatter(v)}
          width={80}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            fontSize: 13,
          }}
          labelStyle={{ color: 'var(--text-secondary)' }}
          formatter={(value) => percentFormatter(Number(value))}
        />
        <Legend wrapperStyle={{ fontSize: 13, color: 'var(--text-secondary)' }} />
        <Line
          type="monotone"
          dataKey="backtested"
          name="Backtested expectation"
          stroke="var(--series-2)"
          strokeWidth={2}
          strokeDasharray="4 3"
          dot={false}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="live"
          name="Live (paper)"
          stroke="var(--series-1)"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  )
}