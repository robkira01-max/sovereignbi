import { useEffect, useRef, useState } from 'react'
import { api, ChatResponse, ChatTurn } from '../api/client'
import { ConfidenceBadge } from '../components/ConfidenceBadge'
import { ChartBlock } from '../components/ChartBlock'
import { SqlBlock } from '../components/SqlBlock'
import { useLocale } from '../hooks/useLocale'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  response?: ChatResponse
}

let _id = 0
const nextId = () => ++_id

export function ChatPage() {
  const { t, tpl } = useLocale()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useDataPipeline, setUseDataPipeline] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const buildHistory = (msgs: Message[]): ChatTurn[] =>
    msgs.slice(-10).map(m => ({
      role: m.role,
      content: m.role === 'assistant' ? (m.response?.answer ?? m.content) : m.content,
    }))

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading) return

    const userMsg: Message = { id: nextId(), role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const history = buildHistory(messages)
      const res = await api.chat(q, history, useDataPipeline)
      const assistantMsg: Message = {
        id: nextId(),
        role: 'assistant',
        content: res.answer,
        response: res,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg: Message = {
        id: nextId(),
        role: 'assistant',
        content: err instanceof Error ? err.message : t('chat.error_unknown'),
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    setMessages([])
    setInput('')
    textareaRef.current?.focus()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 56px)', maxWidth: '900px', margin: '0 auto', padding: '0 16px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 0',
        borderBottom: '1px solid var(--border)',
      }}>
        <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text)' }}>{t('chat.title')}</h2>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: 'var(--muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={useDataPipeline}
              onChange={e => setUseDataPipeline(e.target.checked)}
              style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
            />
            {t('chat.mode_data')}
          </label>
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              style={{
                padding: '4px 12px',
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                color: 'var(--muted)',
                fontFamily: 'inherit',
              }}
            >
              {t('chat.clear')}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 0', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--muted)', paddingTop: '60px' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>💬</div>
            <p style={{ margin: 0, fontSize: '0.9375rem' }}>{t('chat.empty_hint')}</p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '80%',
              padding: '12px 16px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '4px 16px 16px 16px',
              background: msg.role === 'user' ? 'oklch(95% 0.018 220)' : 'var(--surface)',
              border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
              color: 'var(--text)',
              fontSize: '0.9375rem',
              lineHeight: 1.6,
            }}>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {msg.role === 'assistant' ? (msg.response?.answer ?? msg.content) : msg.content}
              </div>

              {msg.response && msg.response.mode === 'data' && (
                <div style={{ marginTop: '12px' }}>
                  {msg.response.confidence && (
                    <ConfidenceBadge confidence={msg.response.confidence} />
                  )}
                  {msg.response.sql && (
                    <div style={{ marginTop: '8px' }}>
                      <SqlBlock sql={msg.response.sql} />
                    </div>
                  )}
                  {msg.response.columns.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <ChartBlock
                        columns={msg.response.columns}
                        rows={msg.response.rows as unknown[][]}
                      />
                    </div>
                  )}
                  {msg.response.columns.length > 0 && (
                    <div style={{ marginTop: '10px', overflowX: 'auto' }}>
                      <p style={{ margin: '0 0 6px', fontSize: '0.75rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 500 }}>
                        {tpl('chat.results', { n: msg.response.rows.length })}
                      </p>
                      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.8rem', background: 'var(--surface)', borderRadius: '8px', overflow: 'hidden' }}>
                        <thead>
                          <tr>
                            {msg.response.columns.map(c => (
                              <th key={c} style={{ border: '1px solid var(--border)', padding: '5px 10px', background: 'var(--surface-alt)', fontWeight: 600, color: 'var(--text)', textAlign: 'start' }}>{c}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {msg.response.rows.slice(0, 50).map((row, i) => (
                            <tr key={i} style={{ background: i % 2 === 1 ? 'var(--surface-alt)' : 'var(--surface)' }}>
                              {(row as unknown[]).map((cell, j) => (
                                <td key={j} style={{ border: '1px solid var(--border)', padding: '5px 10px', color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{String(cell ?? '')}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {msg.response.error && (
                    <p style={{ margin: '8px 0 0', fontSize: '0.8rem', color: 'var(--danger)' }}>{msg.response.error}</p>
                  )}
                </div>
              )}

              {msg.response && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: msg.response.mode === 'data' ? 'oklch(94% 0.04 220)' : 'oklch(94% 0.04 145)',
                    color: msg.response.mode === 'data' ? 'var(--brand)' : 'var(--success)',
                    fontWeight: 600,
                  }}>
                    {msg.response.mode === 'data' ? t('chat.mode_badge_data') : t('chat.mode_badge_general')}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '12px 16px',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '4px 16px 16px 16px',
              color: 'var(--muted)',
              fontSize: '0.9rem',
            }}>
              <span>…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 0', display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.placeholder')}
          rows={2}
          disabled={loading}
          style={{
            flex: 1,
            padding: '10px 14px',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            fontSize: '0.9375rem',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.5,
            background: loading ? 'var(--surface-alt)' : 'var(--surface)',
            color: 'var(--text)',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: '10px 20px',
            background: loading || !input.trim() ? 'oklch(72% 0.08 220)' : 'var(--brand)',
            color: '#fff',
            border: 'none',
            borderRadius: '12px',
            cursor: loading || !input.trim() ? 'default' : 'pointer',
            fontWeight: 600,
            fontSize: '0.9375rem',
            fontFamily: 'inherit',
            alignSelf: 'flex-end',
            minWidth: '80px',
            transition: 'background 0.15s',
          }}
        >
          {loading ? '…' : t('chat.submit')}
        </button>
      </div>
    </div>
  )
}
