import { useState } from 'react'
import { useLocale } from '../hooks/useLocale'

interface Props {
  sql: string
}

export function SqlBlock({ sql }: Props) {
  const { t } = useLocale()
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
          background: 'oklch(20% 0.02 220)',
          color: 'oklch(88% 0.02 220)',
          borderRadius: '10px',
          padding: '16px',
          overflowX: 'auto',
          fontSize: '0.825rem',
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          margin: 0,
          lineHeight: 1.6,
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
          insetInlineEnd: '8px',
          fontSize: '0.7rem',
          padding: '3px 8px',
          cursor: 'pointer',
          background: 'oklch(30% 0.02 220)',
          color: 'oklch(80% 0.02 220)',
          border: '1px solid oklch(38% 0.02 220)',
          borderRadius: '6px',
          fontFamily: 'inherit',
        }}
      >
        {copied ? t('sql.copied') : t('sql.copy')}
      </button>
    </div>
  )
}
