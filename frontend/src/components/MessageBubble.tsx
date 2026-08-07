import type { Message } from '../types'
import './MessageBubble.css'

function QueryTrace({ sql, rowCount }: { sql: string; rowCount: number | null | undefined }) {
  return (
    <details className="query-trace">
      <summary>
        <span className="trace-dot" />
        query trace{typeof rowCount === 'number' ? ` · ${rowCount} row${rowCount === 1 ? '' : 's'}` : ''}
      </summary>
      <pre>{sql}</pre>
    </details>
  )
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`bubble-row ${isUser ? 'from-user' : 'from-assistant'}`}>
      <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        {message.status === 'pending' ? (
          <span className="typing-dots" aria-label="Assistant is thinking">
            <span />
            <span />
            <span />
          </span>
        ) : (
          <>
            <p className="bubble-text">{message.text}</p>
            {message.sql && <QueryTrace sql={message.sql} rowCount={message.rowCount} />}
          </>
        )}
      </div>
    </div>
  )
}
