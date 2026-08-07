import type { ChatSession } from '../types'
import './ChatHistoryPanel.css'

interface Props {
  sessions: ChatSession[]
  activeId: string
  collapsed: boolean
  onToggleCollapsed: () => void
  onSelect: (id: string) => void
  onNewChat: () => void
  onDelete: (id: string) => void
}

function formatWhen(ts: number): string {
  const diffMs = Date.now() - ts
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function ChatHistoryPanel({
  sessions,
  activeId,
  collapsed,
  onToggleCollapsed,
  onSelect,
  onNewChat,
  onDelete,
}: Props) {
  return (
    <aside className={`history-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="history-panel-inner">
        <div className="history-header">
          {!collapsed && <span className="history-header-label">Chats</span>}
          <button
            type="button"
            className="icon-btn"
            onClick={onToggleCollapsed}
            title={collapsed ? 'Expand chat history' : 'Collapse chat history'}
            aria-label={collapsed ? 'Expand chat history' : 'Collapse chat history'}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d={collapsed ? 'M6 3l5 5-5 5' : 'M10 3l-5 5 5 5'}
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <button type="button" className="new-chat-btn" onClick={onNewChat} title="New chat">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          {!collapsed && <span>New chat</span>}
        </button>

        {!collapsed && (
          <div className="history-list">
            {sessions.length === 0 && <div className="history-empty">No conversations yet</div>}
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`history-item ${s.id === activeId ? 'active' : ''}`}
                onClick={() => onSelect(s.id)}
              >
                <div className="history-item-main">
                  <span className="history-item-title">{s.title}</span>
                  <span className="history-item-when">{formatWhen(s.updatedAt)}</span>
                </div>
                <button
                  type="button"
                  className="history-item-delete"
                  title="Delete chat"
                  aria-label="Delete chat"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(s.id)
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path
                      d="M2 3.5h9M5 3.5V2h3v1.5M3.5 3.5l.5 8h5l.5-8"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
