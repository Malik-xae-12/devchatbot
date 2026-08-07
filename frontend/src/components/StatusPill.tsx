import './StatusPill.css'

export default function StatusPill({ connected }: { connected: boolean | null }) {
  const label = connected === null ? 'checking' : connected ? 'db connected' : 'db not configured'
  const state = connected === null ? 'checking' : connected ? 'ok' : 'off'

  return (
    <div className={`status-pill status-${state}`}>
      <span className="status-dot" />
      {label}
    </div>
  )
}
