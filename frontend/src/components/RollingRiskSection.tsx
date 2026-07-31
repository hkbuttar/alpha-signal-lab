import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RollingRisk } from '../lib/api'
import { Card, EmptyState } from './Card'
import { StatTile } from './StatTile'

const percent = (v: number) => `${(v * 100).toFixed(1)}%`

export function RollingRiskSection({ data }: { data: RollingRisk }) {
  if (data.dates.length === 0) {
    return (
      <Card title="Rolling risk">
        <EmptyState message="Not enough history yet for rolling Sharpe/drawdown/VaR (need at least a few days)." />
      </Card>
    )
  }

  const chartData = data.dates.map((date, i) => ({
    date,
    rolling_sharpe: data.rolling_sharpe[i],
    drawdown: data.drawdown[i],
  }))

  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <Card title="Rolling 21-day Sharpe">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <CartesianGrid stroke="var(--gridline)" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="var(--baseline)"
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                minTickGap={40}
              />
              <YAxis stroke="var(--baseline)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 13,
                }}
                labelStyle={{ color: 'var(--text-secondary)' }}
              />
              <Line
                type="monotone"
                dataKey="rolling_sharpe"
                stroke="var(--series-1)"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Drawdown from peak">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
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
                tickFormatter={percent}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 13,
                }}
                labelStyle={{ color: 'var(--text-secondary)' }}
                formatter={(value) => percent(Number(value))}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="var(--status-critical)"
                strokeWidth={2}
                fill="var(--status-critical)"
                fillOpacity={0.1}
                connectNulls={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Value at Risk (95%, daily)">
        <div style={{ display: 'flex', gap: 48 }}>
          <StatTile
            label="Historical VaR"
            value={data.historical_var === null ? '—' : percent(data.historical_var)}
          />
          <StatTile
            label="Parametric VaR"
            value={data.parametric_var === null ? '—' : percent(data.parametric_var)}
          />
        </div>
      </Card>
    </div>
  )
}