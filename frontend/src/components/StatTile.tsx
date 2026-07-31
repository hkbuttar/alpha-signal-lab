export function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 28, fontWeight: 600, color: 'var(--text-primary)' }}>{value}</p>
    </div>
  )
}

export function formatMetricValue(key: string, value: number | boolean | string): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'string') return value
  if (key.toLowerCase().includes('rate') || key.toLowerCase().includes('drawdown')) {
    return `${(value * 100).toFixed(1)}%`
  }
  if (key.toLowerCase().includes('cagr')) {
    return `${(value * 100).toFixed(1)}%`
  }
  return value.toFixed(2)
}