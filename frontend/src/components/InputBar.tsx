import { useState, type FormEvent, type KeyboardEvent } from 'react'
import './InputBar.css'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
}

export default function InputBar({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form className="input-bar" onSubmit={submit}>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about project budgets, hours remaining, member utilization…"
        rows={1}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M4 12L20 4L13 20L11 13L4 12Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        </svg>
      </button>
    </form>
  )
}
