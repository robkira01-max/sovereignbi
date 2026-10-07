import { useState } from 'react'
import { api } from '../api/client'
import type { AskResponse } from '../api/client'
import { ConfidenceBadge } from '../components/ConfidenceBadge'
import { SqlBlock } from '../components/SqlBlock'

export function ChatPage() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [error, setError] = useState('')

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api.ask(question.trim())
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '800px', margin: '32px auto', padding: '0 16px' }}>
      <h2>Chat analytique</h2>
      <form onSubmit={handleAsk} style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Ex : Quel est le CA total par région ?"
          rows={3}
          style={{ flex: 1, padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '0.95rem', resize: 'vertical' }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '10px 20px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, alignSelf: 'flex-end' }}
        >
          {loading ? '…' : 'Poser'}
        </button>
      </form>

      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {result && (
        <div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Réponse</strong>
            <ConfidenceBadge confidence={result.confidence} />
            <p style={{ marginTop: '8px' }}>{result.answer}</p>
          </div>

          {result.sql && (
            <div style={{ marginBottom: '12px' }}>
              <strong>SQL</strong>
              <SqlBlock sql={result.sql} />
            </div>
          )}

          {result.columns.length > 0 && (
            <div>
              <strong>Résultats ({result.rows.length} lignes)</strong>
              <div style={{ overflowX: 'auto', marginTop: '8px' }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.85rem' }}>
                  <thead>
                    <tr>
                      {result.columns.map(c => (
                        <th key={c} style={{ border: '1px solid #e5e7eb', padding: '6px 10px', background: '#f9fafb' }}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, 50).map((row, i) => (
                      <tr key={i}>
                        {(row as unknown[]).map((cell, j) => (
                          <td key={j} style={{ border: '1px solid #e5e7eb', padding: '6px 10px' }}>{String(cell ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
