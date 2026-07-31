import { useEffect, useState } from 'react'
import './App.css'
import { Card } from './components/Card'
import { EquityChart } from './components/EquityChart'
import { PositionsSection } from './components/PositionsSection'
import { RollingRiskSection } from './components/RollingRiskSection'
import { formatMetricValue } from './components/StatTile'
import {
  api,
  type BacktestRunResponse,
  type LatestPositions,
  type RollingRisk,
  type Snapshot,
} from './lib/api'

type Tab = 'equity' | 'positions' | 'risk' | 'factors'

const TABS: { id: Tab; label: string }[] = [
  { id: 'equity', label: 'Equity Curve' },
  { id: 'positions', label: 'Positions & Exposure' },
  { id: 'risk', label: 'Rolling Risk' },
  { id: 'factors', label: 'Factor Breakdown' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('equity')
  const [error, setError] = useState<string | null>(null)

  const [runs, setRuns] = useState<string[]>([])
  const [sampleMetrics, setSampleMetrics] = useState<Record<string, unknown> | null>(null)
  const [selectedRun, setSelectedRun] = useState<string | null>(null)
  const [backtestData, setBacktestData] = useState<BacktestRunResponse | null>(null)

  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [positions, setPositions] = useState<LatestPositions | null>(null)
  const [risk, setRisk] = useState<RollingRisk | null>(null)

  useEffect(() => {
    api
      .backtestRuns()
      .then((r) => {
        setRuns(r.runs)
        setSampleMetrics(r.sample_metrics)
        if (r.runs.length > 0) setSelectedRun(r.runs[r.runs.length - 1])
      })
      .catch((e) => setError(String(e)))

    api
      .snapshots()
      .then((r) => setSnapshots(r.snapshots))
      .catch((e) => setError(String(e)))

    api.latestPositions().then(setPositions).catch((e) => setError(String(e)))
    api.rollingRisk().then(setRisk).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (selectedRun) {
      api.backtestRun(selectedRun).then(setBacktestData).catch((e) => setError(String(e)))
    }
  }, [selectedRun])

  const metrics = backtestData?.metrics ?? (sampleMetrics as Record<string, number | boolean> | null)

  return (
    <div className="app">
      <header className="app-header">
        <h1 style={{ fontSize: 22 }}>Alpha Signal Lab</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Event-driven factor research and paper-trading dashboard.
        </p>
      </header>

      {error && (
        <div
          style={{
            background: 'var(--status-critical)',
            color: 'white',
            padding: '10px 16px',
            borderRadius: 6,
            marginBottom: 16,
            fontSize: 13,
          }}
        >
          Couldn't reach the API ({error}). Is the backend running at{' '}
          {import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}?
        </div>
      )}

      <nav className="tab-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="tab-content">
        {tab === 'equity' && (
          <div style={{ display: 'grid', gap: 20 }}>
            {runs.length > 1 && (
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Backtest run:{' '}
                <select value={selectedRun ?? ''} onChange={(e) => setSelectedRun(e.target.value)}>
                  {runs.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <Card title="Equity: live vs. backtested expectation">
              <EquityChart liveSnapshots={snapshots} backtestEquity={backtestData?.equity ?? []} />
            </Card>
            {metrics && (
              <Card title="Backtest metrics">
                <table>
                  <tbody>
                    {Object.entries(metrics).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{formatMetricValue(key, value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}
          </div>
        )}

        {tab === 'positions' && positions && <PositionsSection data={positions} />}

        {tab === 'risk' && risk && <RollingRiskSection data={risk} />}

        {tab === 'factors' && (
          <Card>
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Per-holding factor score breakdown requires a fresh factor computation and is not
              cached here. Use notebooks/research.ipynb to inspect factor scores and IC/turnover
              diagnostics for the current universe.
            </p>
          </Card>
        )}
      </main>
    </div>
  )
}