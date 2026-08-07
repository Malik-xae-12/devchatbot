export interface ChatResponse {
  reply: string
  intent: 'db_query' | 'off_topic'
  sql?: string | null
  row_count?: number | null
  export_id?: string | null
  export_row_count?: number | null
}

export function exportUrl(exportId: string): string {
  const API_BASE = import.meta.env.VITE_API_BASE || '';
  return `${API_BASE}/api/export/${exportId}`
}

export interface HealthResponse {
  status: string
  db_configured: boolean
  schema_loaded: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function sendMessage(message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat?t=${new Date().getTime()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`)
  }
  return res.json()
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health?t=${new Date().getTime()}`, {
    mode: 'cors'
  })
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`)
  }
  return res.json()
}
