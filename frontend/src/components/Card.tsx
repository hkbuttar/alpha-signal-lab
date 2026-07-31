import type { ReactNode } from 'react'

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 20,
      }}
    >
      {title && (
        <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 16 }}>{title}</h3>
      )}
      {children}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>{message}</p>
}