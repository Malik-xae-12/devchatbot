import { useEffect, useRef, useState } from 'react'
import MessageBubble from './components/MessageBubble'
import InputBar from './components/InputBar'
import StatusPill from './components/StatusPill'
import ChatHistoryPanel from './components/ChatHistoryPanel'
import { sendMessage, checkHealth } from './api'
import type { ChatSession, Message } from './types'
import { loadSessions, saveSessions, makeTitle, newSession } from './sessions'
import './App.css'

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  text:
    "Hi, I'm your database assistant. Ask me about project budgets, hours remaining, or member utilization — I'll query the database and answer in plain language.",
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const stored = loadSessions()
    return stored.length > 0 ? stored : [newSession(WELCOME)]
  })
  const [activeId, setActiveId] = useState<string>(() => sessions[0].id)
  const [collapsed, setCollapsed] = useState(false)
  const [dbConnected, setDbConnected] = useState<boolean | null>(null)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const activeSession = sessions.find((s) => s.id === activeId) ?? sessions[0]
  const messages = activeSession.messages

  useEffect(() => {
    checkHealth()
      .then((h) => setDbConnected(h.db_configured && h.schema_loaded))
      .catch(() => setDbConnected(false))
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    saveSessions(sessions)
  }, [sessions])

  const updateSession = (id: string, updater: (msgs: Message[]) => Message[]) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s
        const nextMessages = updater(s.messages)
        return {
          ...s,
          messages: nextMessages,
          title: s.title === 'New chat' ? makeTitle(nextMessages) : s.title,
          updatedAt: Date.now(),
        }
      })
    )
  }

  const handleSend = async (text: string) => {
    const sessionId = activeSession.id
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', text }
    const pendingId = crypto.randomUUID()
    const pendingMsg: Message = { id: pendingId, role: 'assistant', text: '', status: 'pending' }

    updateSession(sessionId, (msgs) => [...msgs, userMsg, pendingMsg])
    setSending(true)

    try {
      const res = await sendMessage(text)
      updateSession(sessionId, (msgs) =>
        msgs.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                text: res.reply,
                sql: res.sql,
                rowCount: res.row_count,
                intent: res.intent,
                status: 'done',
              }
            : m
        )
      )
    } catch {
      updateSession(sessionId, (msgs) =>
        msgs.map((m) =>
          m.id === pendingId
            ? { ...m, text: 'Something went wrong reaching the server. Please try again.', status: 'error' }
            : m
        )
      )
    } finally {
      setSending(false)
    }
  }

  const handleNewChat = () => {
    const session = newSession(WELCOME)
    setSessions((prev) => [session, ...prev])
    setActiveId(session.id)
  }

  const handleSelect = (id: string) => setActiveId(id)

  const handleDelete = (id: string) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id)
      if (next.length === 0) {
        const fresh = newSession(WELCOME)
        setActiveId(fresh.id)
        return [fresh]
      }
      if (id === activeId) setActiveId(next[0].id)
      return next
    })
  }

  return (
    <div className="page-shell">
      <ChatHistoryPanel
        sessions={sessions}
        activeId={activeSession.id}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((c) => !c)}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
      />

      <div className="app-shell">
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark" />
            <span className="brand-name">DB Assistant</span>
          </div>
          <StatusPill connected={dbConnected} />
        </header>

        <main className="chat-area" ref={scrollRef}>
          <div className="chat-inner">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>
        </main>

        <footer className="composer">
          <div className="composer-inner">
            <InputBar onSend={handleSend} disabled={sending} />
          </div>
        </footer>
      </div>
    </div>
  )
}
