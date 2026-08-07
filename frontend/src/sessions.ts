import type { ChatSession, Message } from './types'

const STORAGE_KEY = 'db-assistant.sessions.v1'
const TITLE_MAX_LEN = 42

export function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ChatSession[]
    if (!Array.isArray(parsed)) return []
    return parsed.sort((a, b) => b.updatedAt - a.updatedAt)
  } catch {
    return []
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch {
    // localStorage unavailable (private mode, quota, etc.) — fail silently,
    // chat still works for the current tab session.
  }
}

export function makeTitle(messages: Message[]): string {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser || !firstUser.text.trim()) return 'New chat'
  const text = firstUser.text.trim()
  return text.length > TITLE_MAX_LEN ? `${text.slice(0, TITLE_MAX_LEN).trimEnd()}…` : text
}

export function newSession(welcome: Message): ChatSession {
  const now = Date.now()
  return {
    id: crypto.randomUUID(),
    title: 'New chat',
    messages: [welcome],
    createdAt: now,
    updatedAt: now,
  }
}
