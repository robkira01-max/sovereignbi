interface Props {
  source: string
  year?: string | number
  note?: string
}

export default function SourceAttribution({ source, year, note }: Props) {
  return (
    <p
      style={{
        margin: '8px 0 0',
        fontSize: 11,
        color: 'var(--muted)',
        lineHeight: 1.5,
        borderTop: '1px solid var(--border)',
        paddingTop: 6,
      }}
    >
      <span aria-label="Source">📄</span>{' '}
      <strong>Source :</strong> {source}
      {year ? ` (${year})` : ''}
      {note ? ` — ${note}` : ''}
    </p>
  )
}
