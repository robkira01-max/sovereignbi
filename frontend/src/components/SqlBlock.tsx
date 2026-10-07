import { useState } from 'react'

interface Props {
  sql: string
}

export function SqlBlock({ sql }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard?.writeText(sql).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div style={{ position: 'relative', margin: '8px 0' }}>
      <pre
        data-testid="sql-block"
        style={{
          background: '#f3f4f6',
          borderRadius: '6px',
          padding: '12px',
          overflowX: 'auto',
          fontSize: '0.85rem',
          fontFamily: 'monospace',
          margin: 0,
        }}
      >
        <code>{sql}</code>
      </pre>
      <button
        data-testid="copy-button"
        onClick={handleCopy}
        style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          fontSize: '0.7rem',
          padding: '2px 6px',
          cursor: 'pointer',
        }}
      >
        {copied ? 'Copié !' : 'Copier'}
      </button>
    </div>
  )
}
