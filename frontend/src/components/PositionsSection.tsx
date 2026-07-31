import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LatestPositions } from '../lib/api'
import { Card, EmptyState } from './Card'

export function PositionsSection({ data }: { data: LatestPositions }) {
  if (!data.date || data.positions.length === 0) {
    return (
      <Card title="Positions & sector exposure">
        <EmptyState message="No open positions yet. Run the live scheduler to populate this." />
      </Card>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20 }}>
      <Card title={`Current positions (as of ${data.date})`}>
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Shares</th>
              <th>Sector</th>
            </tr>
          </thead>
          <tbody>
            {data.positions.map((p) => (
              <tr key={p.ticker}>
                <td>{p.ticker}</td>
                <td>{p.shares.toFixed(2)}</td>
                <td>{p.sector}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Sector exposure">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.sector_exposure} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="var(--gridline)" vertical={false} />
            <XAxis
              dataKey="sector"
              stroke="var(--baseline)"
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
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
            <Bar dataKey="shares" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={48} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}