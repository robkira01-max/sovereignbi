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

const SUGGESTIONS = [
  'Quel est le taux de chômage par région ?',
  'Quelle région a la plus forte croissance ?',
  'Montrez-moi les données démographiques de Djibouti',
]

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

  const handleSend = async (q?: string) => {
    const text = (q ?? input).trim()
    if (!text || loading) return

    const userMsg: Message = { id: nextId(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const isDemo = typeof localStorage !== 'undefined' && localStorage.getItem('mizan_token') === 'demo'

    try {
      let res: ChatResponse
      if (isDemo) {
        await new Promise(r => setTimeout(r, 600))
        res = {
          answer: `Réponse démo pour : « ${text} »\n\nCette instance est en mode démo — les vraies données nécessitent une connexion à l'API MizanBI.`,
          mode: 'general',
          confidence: 'medium',
          sql: undefined,
          columns: [],
          rows: [],
          error: undefined,
        }
      } else {
        const history = buildHistory(messages)
        res = await api.chat(text, history, useDataPipeline)
      }
      setMessages(prev => [...prev, { id: nextId(), role: 'assistant', content: res.answer, response: res }])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: nextId(), role: 'assistant',
        content: err instanceof Error ? err.message : t('chat.error_unknown'),
      }])
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void handleSend() }
  }

  const handleClear = () => { setMessages([]); setInput(''); textareaRef.current?.focus() }

  void tpl  // suppress unused warning

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 56px)', maxWidth: 900, margin: '0 auto' }}>

      {/* Mode pills */}
      <div style={{ display: 'flex', gap: 4, padding: '12px 0', alignItems: 'center' }}>
        <div style={{
          display: 'flex', gap: 4, padding: 4,
          background: 'oklch(13% 0.025 265 / 0.85)',
          border: '1px solid oklch(25% 0.04 265 / 0.6)',
          borderRadius: 12, width: 'fit-content',
        }}>
          {(['data', 'general'] as const).map(m => {
            const active = m === 'data' ? useDataPipeline : !useDataPipeline
            return (
              <button key={m}
                onClick={() => setUseDataPipeline(m === 'data')}
                style={{
                  cursor: 'pointer', border: 'none', borderRadius: 9,
                  padding: '7px 16px',
                  font: `600 13px inherit`,
                  color: '#f0f0fa',
                  background: active ? 'oklch(25% 0.08 265)' : 'transparent',
                  transition: 'background 0.15s',
                  fontFamily: 'inherit',
                }}
              >
                {m === 'data' ? t('chat.mode_data') : 'Général'}
              </button>
            )
          })}
        </div>

        {messages.length > 0 && (
          <button
            onClick={handleClear}
            style={{
              marginLeft: 8, padding: '6px 14px',
              background: 'transparent',
              border: '1px solid oklch(25% 0.04 265 / 0.6)',
              borderRadius: 8, cursor: 'pointer',
              fontSize: 12, color: 'var(--muted)', fontFamily: 'inherit',
            }}
          >{t('chat.clear')}</button>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: 48 }}>
            <div style={{ fontSize: 22, fontWeight: 600, color: '#f0f0fa', marginBottom: 12 }}>
              {t('chat.empty_hint')}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => void handleSend(s)}
                  style={{
                    cursor: 'pointer',
                    border: '1px solid oklch(25% 0.04 265 / 0.8)',
                    background: 'oklch(13% 0.025 265 / 0.85)',
                    color: '#f0f0fa', borderRadius: 999,
                    padding: '8px 14px', fontSize: 13, fontFamily: 'inherit',
                    transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'oklch(68% 0.18 155)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'oklch(25% 0.04 265 / 0.8)' }}
                >{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {msg.role === 'user' ? (
              <div style={{
                alignSelf: 'flex-end', maxWidth: '80%',
                background: 'oklch(65% 0.22 265)', color: '#fff',
                padding: '10px 16px',
                borderRadius: '16px 16px 4px 16px',
                fontSize: '0.9375rem', lineHeight: 1.6,
              }}>
                {msg.content}
              </div>
            ) : (
              <div style={{
                background: 'oklch(13% 0.025 265 / 0.85)',
                border: '1px solid oklch(25% 0.04 265 / 0.6)',
                borderRadius: 16, padding: 18,
                display: 'flex', flexDirection: 'column', gap: 14,
              }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 15, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {msg.response?.answer ?? msg.content}
                  </div>
                  {msg.response?.confidence && (
                    <ConfidenceBadge confidence={msg.response.confidence} />
                  )}
                </div>

                {msg.response?.mode === 'data' && (
                  <>
                    {msg.response.sql && <SqlBlock sql={msg.response.sql} />}
                    {msg.response.columns.length > 0 && (
                      <>
                        <ChartBlock columns={msg.response.columns} rows={msg.response.rows as unknown[][]} />
                        <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid oklch(25% 0.04 265 / 0.6)', borderRadius: 12 }}>
                          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
                            <thead>
                              <tr>
                                {msg.response.columns.map(c => (
                                  <th key={c} style={{ position: 'sticky', top: 0, textAlign: 'start', padding: '8px 12px', background: 'oklch(20% 0.05 265)', fontWeight: 600, whiteSpace: 'nowrap' }}>{c}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {msg.response.rows.slice(0, 50).map((row, i) => (
                                <tr key={i} style={{ background: i % 2 === 1 ? 'oklch(16% 0.03 265)' : 'transparent' }}>
                                  {(row as unknown[]).map((cell, j) => (
                                    <td key={j} style={{ padding: '7px 12px', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>{String(cell ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                    {msg.response.error && (
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--danger)' }}>{msg.response.error}</p>
                    )}
                  </>
                )}

                {msg.response && (
                  <span style={{
                    alignSelf: 'flex-start', fontSize: 10, padding: '2px 8px', borderRadius: 999,
                    background: msg.response.mode === 'data' ? 'oklch(20% 0.05 220)' : 'oklch(20% 0.05 145)',
                    color: msg.response.mode === 'data' ? 'var(--brand)' : 'var(--accent)',
                    fontWeight: 600,
                  }}>
                    {msg.response.mode === 'data' ? t('chat.mode_badge_data') : t('chat.mode_badge_general')}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{
            padding: '14px 18px', borderRadius: 16, fontSize: 14,
            background: 'oklch(13% 0.025 265 / 0.85)',
            border: '1px solid oklch(25% 0.04 265 / 0.6)',
            color: 'oklch(68% 0.03 265)',
          }}>Analyse en cours…</div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Sticky input */}
      <form
        onSubmit={e => { e.preventDefault(); void handleSend() }}
        style={{
          position: 'sticky', bottom: 16,
          display: 'flex', gap: 10, padding: 8,
          background: 'oklch(13% 0.025 265 / 0.95)',
          border: '1px solid oklch(25% 0.04 265 / 0.8)',
          borderRadius: 16, backdropFilter: 'blur(12px)',
          marginTop: 12,
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.placeholder')}
          rows={1}
          disabled={loading}
          style={{
            flex: 1, minWidth: 0, background: 'transparent',
            border: 'none', outline: 'none',
            color: '#f0f0fa', fontFamily: 'inherit',
            fontSize: 14, lineHeight: 1.5,
            padding: '8px 12px', resize: 'none',
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            cursor: loading || !input.trim() ? 'default' : 'pointer',
            border: 'none', borderRadius: 11, padding: '10px 20px',
            background: loading || !input.trim() ? 'oklch(45% 0.1 265)' : 'oklch(65% 0.22 265)',
            color: '#fff', fontFamily: 'inherit', fontWeight: 600, fontSize: 14,
            transition: 'background 0.15s',
          }}
        >
          {loading ? '…' : t('chat.submit')}
        </button>
      </form>
    </div>
  )
}
