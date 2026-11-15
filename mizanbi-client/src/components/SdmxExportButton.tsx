import { useState } from 'react'
import type { Dict } from '../lib/i18n'
import { authHeaders, getApiBase, isApiConfigured } from '../lib/api'
import { SDMX_FREQS, sdmxFilename, sdmxIssues, sdmxPath } from '../lib/sdmx'

interface Props {
  dashId: string
  tileId: string
  t: Dict['dashboard']
  onError: (message: string) => void
}

const freqLabel = (t: Dict['dashboard'], f: string): string =>
  ({ A: t.sdmxFreqA, S: t.sdmxFreqS, Q: t.sdmxFreqQ, M: t.sdmxFreqM, W: t.sdmxFreqW, D: t.sdmxFreqD } as Record<string, string>)[f] ?? f

/** Bouton « ↓ SDMX » d'une tuile : petit formulaire (identifiant, unité, périodicité) puis téléchargement SDMX-CSV 2.0. */
export default function SdmxExportButton({ dashId, tileId, t, onError }: Props) {
  const [open, setOpen] = useState(false)
  const [structureId, setStructureId] = useState('')
  const [unit, setUnit] = useState('')
  const [freq, setFreq] = useState('')
  const [busy, setBusy] = useState(false)

  const opts = { structureId, unit, freq }
  const issues = sdmxIssues(opts)
  const path = sdmxPath(dashId, tileId, opts)

  const download = async () => {
    if (!path || !isApiConfigured()) return
    setBusy(true)
    try {
      const res = await fetch(`${getApiBase()}${path}`, { headers: authHeaders() })
      if (!res.ok) {
        let detail = ''
        try { const b = (await res.json()) as { detail?: unknown }; if (typeof b.detail === 'string') detail = b.detail } catch { /* corps non JSON */ }
        throw new Error(detail || `HTTP ${res.status}`)
      }
      const url = URL.createObjectURL(await res.blob())
      const a = document.createElement('a')
      a.href = url
      a.download = sdmxFilename(dashId, tileId)
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
      setOpen(false)
    } catch (e) {
      onError(e instanceof Error ? e.message : t.sdmxError)
    } finally {
      setBusy(false)
    }
  }

  const field = { display: 'flex', flexDirection: 'column', gap: 3, fontSize: 11 } as const

  return (
    <span style={{ position: 'relative' }}>
      <button data-testid={`export-sdmx-${tileId}`} onClick={() => setOpen((o) => !o)} aria-expanded={open}
        title={t.sdmxTitle}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 10, padding: '0 3px', lineHeight: 1 }}>
        {t.sdmxButton}
      </button>
      {open && (
        <form noValidate role="dialog" aria-label={t.sdmxTitle}
          onSubmit={(e) => { e.preventDefault(); void download() }}
          style={{ position: 'absolute', insetInlineEnd: 0, top: '120%', zIndex: 20, width: 260, display: 'flex', flexDirection: 'column', gap: 8,
            padding: 12, background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: '0 8px 24px #0006', cursor: 'default' }}>
          <div style={{ fontWeight: 600, fontSize: 12 }}>{t.sdmxTitle}</div>
          <label style={field}>{t.sdmxStructure}
            <input className="input" value={structureId} onChange={(e) => setStructureId(e.target.value)} dir="ltr" placeholder="INSTAD:CHOMAGE(1.0)"
              aria-invalid={issues.includes('structure')} />
            {issues.includes('structure') && <span role="alert" style={{ color: 'oklch(78% 0.15 25)' }}>{t.sdmxErrStructure}</span>}
          </label>
          <label style={field}>{t.sdmxUnit}
            <input className="input" value={unit} onChange={(e) => setUnit(e.target.value)} dir="ltr" placeholder="PCT" maxLength={40}
              aria-invalid={issues.includes('unit')} />
            {issues.includes('unit') && <span role="alert" style={{ color: 'oklch(78% 0.15 25)' }}>{t.sdmxErrUnit}</span>}
          </label>
          <label style={field}>{t.sdmxFreq}
            <select className="input" value={freq} onChange={(e) => setFreq(e.target.value)}>
              <option value="">{t.sdmxFreqAuto}</option>
              {SDMX_FREQS.map((f) => <option key={f} value={f}>{f} — {freqLabel(t, f)}</option>)}
            </select>
          </label>
          <span className="muted" style={{ fontSize: 10, lineHeight: 1.4 }}>{t.sdmxNote}</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn" type="submit" disabled={busy || !path} style={{ fontSize: 12, padding: '4px 12px' }}>{busy ? '…' : t.sdmxDownload}</button>
            <button className="btn-ghost" type="button" onClick={() => setOpen(false)} style={{ fontSize: 12, padding: '4px 12px' }}>{t.sdmxCancel}</button>
          </div>
        </form>
      )}
    </span>
  )
}
