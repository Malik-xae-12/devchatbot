import type { Message } from '../types'
import { exportUrl } from '../api'
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

function ExportAction({ exportId, exportRowCount }: { exportId: string; exportRowCount: number | null | undefined }) {
  return (
    <a className="export-action" href={exportUrl(exportId)} download>
      <span className="export-icon" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
          <path
            d="M8 1.5v8.4m0 0L4.7 6.6M8 9.9l3.3-3.3M2.5 12v1.4c0 .6.4 1.1 1 1.1h9c.6 0 1-.5 1-1.1V12"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      Download full results{typeof exportRowCount === 'number' ? ` · ${exportRowCount} rows` : ''} (.xlsx)
    </a>
  )
}

/** Inline markdown: **bold** only — kept intentionally minimal. */
function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>
  })
}

function isTableSeparator(line: string) {
  return /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$/.test(line.trim())
}

function splitTableRow(line: string) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

/** Very small Markdown renderer covering exactly what the assistant is
 * instructed to produce: paragraphs, **bold**, "- " bullet lists, and
 * pipe tables. Anything else falls back to plain text. */
function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const blocks: JSX.Element[] = []
  let i = 0
  let blockKey = 0

  while (i < lines.length) {
    const line = lines[i]

    if (line.trim() === '') {
      i++
      continue
    }

    // Table: a header row immediately followed by a separator row
    if (line.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const header = splitTableRow(line)
      const rows: string[][] = []
      i += 2
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        rows.push(splitTableRow(lines[i]))
        i++
      }
      blockKey++
      blocks.push(
        <div className="md-table-wrap" key={`table-${blockKey}`}>
          <table className="md-table">
            <thead>
              <tr>
                {header.map((h, idx) => (
                  <th key={idx}>{renderInline(h, `th-${blockKey}-${idx}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{renderInline(cell, `td-${blockKey}-${rIdx}-${cIdx}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      continue
    }

    // Bullet list
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''))
        i++
      }
      blockKey++
      blocks.push(
        <ul className="md-list" key={`list-${blockKey}`}>
          {items.map((item, idx) => (
            <li key={idx}>{renderInline(item, `li-${blockKey}-${idx}`)}</li>
          ))}
        </ul>
      )
      continue
    }

    // Paragraph (collect contiguous non-empty, non-table, non-list lines)
    const paraLines: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^[-*]\s+/.test(lines[i]) &&
      !(lines[i].includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      paraLines.push(lines[i])
      i++
    }
    blockKey++
    blocks.push(
      <p className="md-p" key={`p-${blockKey}`}>
        {renderInline(paraLines.join(' '), `p-${blockKey}`)}
      </p>
    )
  }

  return blocks
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
        ) : isUser ? (
          <p className="bubble-text">{message.text}</p>
        ) : (
          <>
            <div className="bubble-markdown">{renderMarkdown(message.text)}</div>
            {message.exportId && (
              <ExportAction exportId={message.exportId} exportRowCount={message.exportRowCount} />
            )}
            {message.sql && <QueryTrace sql={message.sql} rowCount={message.rowCount} />}
          </>
        )}
      </div>
    </div>
  )
}
