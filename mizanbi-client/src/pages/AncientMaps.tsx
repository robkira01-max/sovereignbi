// P-029 — Import de cartes anciennes scannées (JPG/PNG/WebP/PDF).
// Géoréférencement par points de contrôle, 100 % côté client et hors ligne :
// aucun envoi serveur, les fichiers restent sur la machine de l'utilisateur.
// Le scan est affiché tel quel, en couche par-dessus la carte de référence
// Djibouti ADM1 : les contours d'origine sont préservés, rien n'est retracé.
import { useMemo, useRef, useState } from 'react'
import type { Dict } from '../lib/i18n'
import { buildDjiboutiMap, djiboutiBounds, inDjiboutiBounds, projectLonLat, unprojectView } from '../lib/geo'
import {
  REFERENCE_PLACES, compressImage, demoMap, exportMapJson, fitAffine, loadMaps,
  readFileAsDataUrl, renderPdfPage, saveMaps, uid,
  type AncientMapMeta, type ControlPoint,
} from '../lib/ancientMaps'

type ViewMode = 'overlay' | 'scan' | 'ref'

const EMPTY_DRAFT = (): AncientMapMeta => {
  const now = new Date().toISOString()
  return {
    id: `new-${uid()}`, title: '', year: '', source: '', zone: 'Djibouti',
    scale: '', notes: '', fileName: '', image: '', imgWidth: 0, imgHeight: 0,
    points: [], createdAt: now, updatedAt: now,
  }
}

function download(filename: string, text: string, mime = 'application/json') {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: mime }))
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

export default function AncientMapsPage({ t }: { t: Dict }) {
  const [maps, setMaps] = useState<AncientMapMeta[]>(() => loadMaps())
  const [draft, setDraft] = useState<AncientMapMeta | null>(null)
  const [pendingSource, setPendingSource] = useState<{ sx: number; sy: number } | null>(null)
  const [replacingId, setReplacingId] = useState<string | null>(null)
  const [replaceSide, setReplaceSide] = useState<'scan' | 'ref' | null>(null)
  const [opacity, setOpacity] = useState(0.7)
  const [viewMode, setViewMode] = useState<ViewMode>('overlay')
  const [zoom, setZoom] = useState(1)
  const [notice, setNotice] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [pdfPages, setPdfPages] = useState(0)
  const [pdfPage, setPdfPage] = useState(1)
  const fileRef = useRef<HTMLInputElement>(null)
  const geo = useMemo(() => buildDjiboutiMap(), [])
  const bounds = useMemo(() => djiboutiBounds(), [])

  const fit = useMemo(() => (draft ? fitAffine(draft.points) : null), [draft])

  // Transformation affine (pixels du scan -> coordonnées viewBox de la carte).
  const viewAffine = useMemo(() => {
    if (!fit?.affine) return null
    const a = fit.affine
    const k = bounds.k * bounds.sc
    return {
      A: k * a.a, B: k * a.b, C: k * (a.c - bounds.x0),
      D: -bounds.sc * a.d, E: -bounds.sc * a.e, F: bounds.sc * (bounds.y1 - a.f),
    }
  }, [fit, bounds])

  const setDraftField = (patch: Partial<AncientMapMeta>) => setDraft((d) => (d ? { ...d, ...patch, updatedAt: new Date().toISOString() } : d))

  const openDraft = (m: AncientMapMeta) => {
    setDraft({ ...m, points: m.points.map((p) => ({ ...p })) })
    setPendingSource(null); setReplacingId(null); setReplaceSide(null)
    setPdfFile(null); setPdfPages(m.pdfPages ?? 0); setPdfPage(m.pdfPage ?? 1)
    setNotice(''); setZoom(1); setViewMode('overlay')
  }

  const loadDemo = () => { openDraft(demoMap()); setNotice('Exemple démo chargé : schéma fictif, 3 repères fictifs. Testez le calage, puis importez votre vrai scan.') }

  const onFile = async (file: File) => {
    if (!draft) return
    setNotice('')
    try {
      if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        const rendered = await renderPdfPage(file, 1)
        const comp = await compressImage(rendered.dataUrl)
        setPdfFile(file); setPdfPages(rendered.pages); setPdfPage(1)
        setDraftField({ image: comp.dataUrl, imgWidth: comp.width, imgHeight: comp.height, fileName: file.name, pdfPages: rendered.pages, pdfPage: 1, points: [] })
        setNotice(rendered.pages > 1 ? `PDF de ${rendered.pages} pages : seule la page 1 est rendue pour le calage. Choisissez une autre page ci-dessous si besoin (les points sont effacés au changement de page).` : 'PDF importé (page 1 rendue en image).')
      } else if (file.type.startsWith('image/')) {
        const raw = await readFileAsDataUrl(file)
        const comp = await compressImage(raw)
        setPdfFile(null); setPdfPages(0)
        setDraftField({ image: comp.dataUrl, imgWidth: comp.width, imgHeight: comp.height, fileName: file.name })
      } else {
        setNotice('Format non pris en charge : JPG, PNG, WebP ou PDF uniquement.')
      }
    } catch (e) {
      setNotice(`Import impossible : ${e instanceof Error ? e.message : 'erreur inconnue'}`)
    }
  }

  const onPdfPage = async (page: number) => {
    if (!draft || !pdfFile) return
    setPdfPage(page)
    try {
      const rendered = await renderPdfPage(pdfFile, page)
      const comp = await compressImage(rendered.dataUrl)
      setDraftField({ image: comp.dataUrl, imgWidth: comp.width, imgHeight: comp.height, pdfPage: page, points: [] })
      setNotice(`Page ${page} rendue. Les points de contrôle ont été effacés (ils appartenaient à la page précédente).`)
    } catch (e) {
      setNotice(`Rendu de la page ${page} impossible : ${e instanceof Error ? e.message : 'erreur inconnue'}`)
    }
  }

  // Clic sur le scan : position du repère en pixels de l'image.
  const onScanClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!draft || !draft.image) return
    const img = e.currentTarget
    const rect = img.getBoundingClientRect()
    const sx = Math.round(((e.clientX - rect.left) / rect.width) * draft.imgWidth)
    const sy = Math.round(((e.clientY - rect.top) / rect.height) * draft.imgHeight)
    if (replacingId && replaceSide === 'scan') {
      setDraftField({ points: draft.points.map((p) => (p.id === replacingId ? { ...p, sx, sy } : p)) })
      setReplacingId(null); setReplaceSide(null)
      return
    }
    setPendingSource({ sx, sy })
    setNotice('Repère placé sur le scan. Cliquez maintenant sa position sur la carte de référence (à droite), ou choisissez une ville ci-dessous.')
  }

  // Clic sur la carte de référence : lon/lat du repère.
  const onRefClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!draft) return
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const vx = -6 + ((e.clientX - rect.left) / rect.width) * geo.w
    const vy = -6 + ((e.clientY - rect.top) / rect.height) * geo.h
    const { lon, lat } = unprojectView(vx, vy, bounds)
    placeTarget(lon, lat)
  }

  const placeTarget = (lon: number, lat: number, label?: string) => {
    if (!draft) return
    const rLon = Math.round(lon * 1000) / 1000
    const rLat = Math.round(lat * 1000) / 1000
    if (replacingId && replaceSide === 'ref') {
      setDraftField({ points: draft.points.map((p) => (p.id === replacingId ? { ...p, lon: rLon, lat: rLat } : p)) })
      setReplacingId(null); setReplaceSide(null)
      return
    }
    if (!pendingSource) { setNotice('Placez d’abord un repère sur le scan (cliquez sur l’image).'); return }
    const pt: ControlPoint = { id: uid(), sx: pendingSource.sx, sy: pendingSource.sy, lon: rLon, lat: rLat, label: label ?? `Point ${draft.points.length + 1}` }
    setDraftField({ points: [...draft.points, pt] })
    setPendingSource(null)
    if (!inDjiboutiBounds(rLon, rLat, bounds)) setNotice('Attention : ce repère est hors de l’emprise Djibouti de la carte de référence — l’aperçu superposé sera partiel. Les coordonnées sont quand même enregistrées.')
  }

  const updatePoint = (id: string, patch: Partial<ControlPoint>) =>
    setDraftField({ points: (draft?.points ?? []).map((p) => (p.id === id ? { ...p, ...patch } : p)) })
  const deletePoint = (id: string) => setDraftField({ points: (draft?.points ?? []).filter((p) => p.id !== id) })

  const saveDraft = () => {
    if (!draft) return
    if (!draft.image) { setNotice('Importez d’abord un scan (image ou PDF).'); return }
    if (!draft.title.trim()) { setNotice('Donnez un titre à la carte avant de l’enregistrer.'); return }
    const next = maps.some((m) => m.id === draft.id)
      ? maps.map((m) => (m.id === draft.id ? draft : m))
      : [...maps, draft]
    const res = saveMaps(next)
    if (!res.ok) {
      // Retente sans l'image (fiche + points conservés).
      const slim = next.map((m) => (m.id === draft.id ? { ...m, image: '' } : m))
      saveMaps(slim)
      setMaps(slim)
      setNotice(res.error ?? 'Stockage local plein.')
      return
    }
    setMaps(next)
    setNotice(`Carte « ${draft.title} » enregistrée localement (${draft.points.length} point(s) de contrôle).`)
  }

  const deleteMap = (id: string) => {
    const next = maps.filter((m) => m.id !== id)
    saveMaps(next); setMaps(next)
    if (draft?.id === id) setDraft(null)
  }

  const vw = geo.w / zoom; const vh = geo.h / zoom
  const cx = -6 + geo.w / 2; const cy = -6 + geo.h / 2
  const viewBox = `${cx - vw / 2} ${cy - vh / 2} ${vw} ${vh}`

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 1100 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.ancientMaps}</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{t.ancientMapsSub}</p>
        </div>
        <span className="badge badge-volet2">{t.ancientBadge}</span>
      </div>

      <div style={{ padding: '12px 16px', borderRadius: 12, background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, lineHeight: 1.6 }}>
        <b>Comment ça marche :</b> 1) importez le scan (image ou PDF, 100 % local, aucun envoi serveur) ·
        2) cliquez un repère sur le scan, puis sa position réelle sur la carte de référence (ou une ville prédéfinie) ·
        3) répétez pour au moins 3 repères, si possible 4 ou plus, bien répartis aux quatre coins ·
        4) vérifiez l’erreur résiduelle, puis enregistrez. Le scan est affiché tel quel : <b>rien n’est retracé</b>.
      </div>

      {/* Bibliothèque des cartes importées */}
      <section className="card-solid">
        <h3>Mes cartes anciennes ({maps.length})</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
          <button className="btn-ghost" onClick={() => openDraft(EMPTY_DRAFT())}>+ Nouvelle carte</button>
          <button className="btn-ghost" onClick={loadDemo}>Charger l’exemple démo</button>
        </div>
        {maps.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Aucune carte importée pour l’instant. Chargez l’exemple démo pour tester, ou importez votre premier scan.</p>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
          {maps.map((m) => (
            <div key={m.id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12, background: 'var(--surface)' }}>
              {m.image && <img src={m.image} alt={m.title} style={{ width: '100%', height: 110, objectFit: 'cover', borderRadius: 8 }} />}
              <div style={{ fontWeight: 700, marginTop: 8 }}>{m.title || '(sans titre)'}</div>
              <div className="muted" style={{ fontSize: 12 }}>{m.year || 'Année inconnue'} · {m.zone} · {m.points.length} point(s){m.demo ? ' · DÉMO' : ''}</div>
              <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                <button className="btn-ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => openDraft(m)}>Ouvrir / caler</button>
                <button className="btn-ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => download(`${(m.title || 'carte').replace(/[^\w-]+/g, '_')}.json`, exportMapJson(m))}>Exporter la fiche (JSON)</button>
                <button className="btn-ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => deleteMap(m.id)}>Supprimer</button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {draft && (
        <>
          {/* Fiche de la carte */}
          <section className="card-solid">
            <h3>Fiche de la carte {draft.demo ? '— Exemple démo, pas une vraie carte ancienne' : ''}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginTop: 12 }}>
              <label style={{ fontSize: 13 }}>Titre<br /><input value={draft.title} onChange={(e) => setDraftField({ title: e.target.value })} placeholder="Ex. Carte de Djibouti, 1962" style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
              <label style={{ fontSize: 13 }}>Année<br /><input value={draft.year} onChange={(e) => setDraftField({ year: e.target.value })} placeholder="Ex. 1962" style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
              <label style={{ fontSize: 13 }}>Source / auteur<br /><input value={draft.source} onChange={(e) => setDraftField({ source: e.target.value })} placeholder="Ex. Archives, auteur…" style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
              <label style={{ fontSize: 13 }}>Zone<br /><input value={draft.zone} onChange={(e) => setDraftField({ zone: e.target.value })} style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
              <label style={{ fontSize: 13 }}>Échelle (si connue)<br /><input value={draft.scale} onChange={(e) => setDraftField({ scale: e.target.value })} placeholder="Ex. 1:250 000" style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
              <label style={{ fontSize: 13 }}>Notes<br /><input value={draft.notes} onChange={(e) => setDraftField({ notes: e.target.value })} placeholder="État du papier, déformations…" style={{ width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></label>
            </div>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) void onFile(f) }}
              onClick={() => fileRef.current?.click()}
              style={{ marginTop: 14, border: '1px dashed var(--border)', borderRadius: 12, padding: 18, textAlign: 'center', cursor: 'pointer', fontSize: 13, color: 'var(--muted)' }}
            >
              Glissez un scan ici ou cliquez pour choisir — JPG, PNG, WebP ou PDF. {draft.fileName ? `Fichier : ${draft.fileName}` : 'Aucun fichier.'}
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf" style={{ display: 'none' }} onChange={(e) => { const f = e.target.files?.[0]; if (f) void onFile(f); e.target.value = '' }} />
            </div>
            {pdfFile && pdfPages > 1 && (
              <div style={{ marginTop: 10, fontSize: 13 }}>
                Page du PDF à caler :{' '}
                <select value={pdfPage} onChange={(e) => void onPdfPage(Number(e.target.value))} style={{ padding: 6, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }}>
                  {Array.from({ length: pdfPages }, (_, i) => i + 1).map((p) => <option key={p} value={p}>Page {p} / {pdfPages}</option>)}
                </select>
                <span className="muted"> — seule la page choisie est rendue ; les autres pages ne sont pas importées.</span>
              </div>
            )}
          </section>

          {/* Calage : scan + carte de référence */}
          <section className="card-solid">
            <h3>2 — Calage par points de contrôle ({draft.points.length} point(s))</h3>
            <p className="muted" style={{ marginTop: 6 }}>
              {pendingSource
                ? `Repère placé sur le scan à (${pendingSource.sx}, ${pendingSource.sy}) px — cliquez maintenant sa position sur la carte de référence, ou choisissez une ville ci-dessous.`
                : replacingId
                  ? `Déplacement du point : cliquez sur ${replaceSide === 'scan' ? 'le scan' : 'la carte de référence'}.`
                  : 'Cliquez un repère sur le scan, puis sa position réelle sur la carte de référence. Minimum 3 points ; 4 ou plus, bien répartis, conseillés.'}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: 16, marginTop: 12 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Scan — cliquez un repère</div>
                {draft.image ? (
                  <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
                    <img src={draft.image} alt="Scan de la carte ancienne" onClick={onScanClick} style={{ maxWidth: '100%', display: 'block', borderRadius: 10, cursor: 'crosshair' }} />
                    {draft.points.map((p, i) => (
                      <span key={p.id} style={{ position: 'absolute', left: `${(p.sx / draft.imgWidth) * 100}%`, top: `${(p.sy / draft.imgHeight) * 100}%`, transform: 'translate(-50%,-50%)', width: 22, height: 22, borderRadius: '50%', background: '#b03030', color: '#fff', fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff', pointerEvents: 'none' }}>{i + 1}</span>
                    ))}
                    {pendingSource && (
                      <span style={{ position: 'absolute', left: `${(pendingSource.sx / draft.imgWidth) * 100}%`, top: `${(pendingSource.sy / draft.imgHeight) * 100}%`, transform: 'translate(-50%,-50%)', width: 22, height: 22, borderRadius: '50%', background: 'oklch(68% 0.18 155)', color: '#070711', fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff', pointerEvents: 'none' }}>?</span>
                    )}
                  </div>
                ) : <p className="muted">Importez d’abord un scan.</p>}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Carte de référence — Djibouti ADM1 (cliquez la position réelle)</div>
                <svg viewBox={geo.view} onClick={onRefClick} style={{ width: '100%', maxWidth: 420, display: 'block', cursor: 'crosshair', background: 'var(--surface)', borderRadius: 10 }} role="img" aria-label="Carte de référence de Djibouti">
                  {geo.shapes.map((g) => (
                    <path key={g.key} d={g.d} fill="oklch(30% 0.04 265)" stroke="oklch(85% 0.03 265)" strokeWidth={0.8} strokeLinejoin="round"><title>{g.name}</title></path>
                  ))}
                  {draft.points.map((p, i) => {
                    const v = projectLonLat(p.lon, p.lat, bounds)
                    return (
                      <g key={p.id}>
                        <circle cx={v.x} cy={v.y} r={7} fill="#b03030" stroke="#fff" strokeWidth={1.5} />
                        <text x={v.x} y={v.y - 10} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--text)">{i + 1}</text>
                      </g>
                    )
                  })}
                </svg>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
                  {REFERENCE_PLACES.map((pl) => (
                    <button key={pl.name} className="btn-ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => placeTarget(pl.lon, pl.lat, pl.name)}>{pl.name}</button>
                  ))}
                </div>
                <p className="muted" style={{ marginTop: 8 }}>Les boutons ci-dessus placent la cible sur une ville connue (coordonnées arrondies au millième de degré).</p>
              </div>
            </div>

            {/* Liste des points + erreurs résiduelles */}
            {draft.points.length > 0 && (
              <div className="table-wrap" style={{ marginTop: 14 }}>
                <table className="data">
                  <thead><tr><th>#</th><th>Repère</th><th>Scan (px)</th><th>Lon</th><th>Lat</th><th>Erreur résiduelle</th><th></th></tr></thead>
                  <tbody>
                    {draft.points.map((p, i) => {
                      const res = fit?.residualsKm.find((r) => r.id === p.id)
                      return (
                        <tr key={p.id}>
                          <td>{i + 1}</td>
                          <td><input value={p.label ?? ''} onChange={(e) => updatePoint(p.id, { label: e.target.value })} style={{ width: 130, padding: 4, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></td>
                          <td>{p.sx}, {p.sy}</td>
                          <td><input type="number" step={0.001} value={p.lon} onChange={(e) => updatePoint(p.id, { lon: Number(e.target.value) })} style={{ width: 80, padding: 4, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></td>
                          <td><input type="number" step={0.001} value={p.lat} onChange={(e) => updatePoint(p.id, { lat: Number(e.target.value) })} style={{ width: 80, padding: 4, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }} /></td>
                          <td>{res ? `${res.km.toFixed(2).replace('.', ',')} km` : '—'}</td>
                          <td>
                            <button className="btn-ghost" style={{ padding: '3px 8px', fontSize: 12 }} onClick={() => { setReplacingId(p.id); setReplaceSide('scan'); setPendingSource(null) }}>↺ scan</button>{' '}
                            <button className="btn-ghost" style={{ padding: '3px 8px', fontSize: 12 }} onClick={() => { setReplacingId(p.id); setReplaceSide('ref'); setPendingSource(null) }}>↺ carte</button>{' '}
                            <button className="btn-ghost" style={{ padding: '3px 8px', fontSize: 12 }} onClick={() => deletePoint(p.id)}>✕</button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {fit && (
              <div style={{ marginTop: 12, fontSize: 13, lineHeight: 1.7 }}>
                {draft.points.length < 3 && <p style={{ color: 'oklch(72% 0.19 55)' }}>Il faut au moins 3 points de contrôle pour calculer le calage ({draft.points.length}/3).</p>}
                {fit.affine && (
                  <>
                    <p>Erreur résiduelle : RMS <b>{fit.rmsKm.toFixed(2).replace('.', ',')} km</b> · max <b>{fit.maxKm.toFixed(2).replace('.', ',')} km</b> (approximations, 111 km/degré). {fit.rmsKm > 5 ? 'Erreur élevée : vérifiez les repères (un point mal placé fausse tout le calage).' : fit.rmsKm > 2 ? 'Erreur modérée : acceptable pour une carte ancienne, ajoutez un 4e point bien réparti si possible.' : 'Bon calage pour une carte ancienne.'}</p>
                    {fit.collinear && <p style={{ color: 'oklch(72% 0.19 55)' }}>Attention : vos points sont presque alignés — le calage n’est pas fiable. Écartez-les aux quatre coins de la carte.</p>}
                    {fit.degenerate && <p style={{ color: 'oklch(58% 0.22 25)' }}>Calage impossible : transformation dégénérée. Déplacez les points.</p>}
                  </>
                )}
              </div>
            )}
          </section>

          {/* Aperçu superposé */}
          <section className="card-solid">
            <h3>3 — Aperçu superposé</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginTop: 12 }}>
              <div className="view-switch" role="tablist" aria-label="Mode d'aperçu">
                <button className={viewMode === 'overlay' ? 'active' : ''} onClick={() => setViewMode('overlay')}>Superposition</button>
                <button className={viewMode === 'scan' ? 'active' : ''} onClick={() => setViewMode('scan')}>Scan seul</button>
                <button className={viewMode === 'ref' ? 'active' : ''} onClick={() => setViewMode('ref')}>Carte seule</button>
              </div>
              <label style={{ fontSize: 13, display: 'flex', gap: 8, alignItems: 'center' }}>
                Opacité du scan
                <input type="range" min={0} max={100} value={Math.round(opacity * 100)} onChange={(e) => setOpacity(Number(e.target.value) / 100)} />
                {Math.round(opacity * 100)} %
              </label>
              <label style={{ fontSize: 13, display: 'flex', gap: 8, alignItems: 'center' }}>
                Zoom
                <input type="range" min={1} max={4} step={0.5} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} />
                ×{zoom}
              </label>
            </div>
            {viewAffine && draft.image ? (
              <svg viewBox={viewBox} style={{ width: '100%', maxWidth: 760, display: 'block', marginTop: 14, background: 'var(--surface)', borderRadius: 10 }} role="img" aria-label="Aperçu du scan géoréférencé sur la carte de Djibouti">
                {viewMode !== 'scan' && geo.shapes.map((g) => (
                  <path key={g.key} d={g.d} fill="oklch(30% 0.04 265)" stroke="oklch(85% 0.03 265)" strokeWidth={0.8 / zoom} strokeLinejoin="round"><title>{g.name}</title></path>
                ))}
                {viewMode !== 'ref' && (
                  <image href={draft.image} width={draft.imgWidth} height={draft.imgHeight} opacity={viewMode === 'overlay' ? opacity : 1} transform={`matrix(${viewAffine.A} ${viewAffine.D} ${viewAffine.B} ${viewAffine.E} ${viewAffine.C} ${viewAffine.F})`} preserveAspectRatio="none" />
                )}
              </svg>
            ) : (
              <p className="muted" style={{ marginTop: 12 }}>L’aperçu apparaît quand le scan est importé et qu’au moins 3 points de contrôle sont placés.</p>
            )}
            <p className="muted" style={{ marginTop: 10 }}>Le scan est affiché tel quel, sans retracé. Le calage affine ne corrige pas les déformations du papier ni les projections anciennes très différentes de la projection actuelle.</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <button className="btn-ghost" onClick={saveDraft}>Enregistrer localement</button>
              <button className="btn-ghost" onClick={() => download(`${(draft.title || 'carte').replace(/[^\w-]+/g, '_')}.json`, exportMapJson(draft))}>Exporter la fiche (JSON)</button>
              <button className="btn-ghost" onClick={() => { setDraft(null); setPendingSource(null); setReplacingId(null) }}>Fermer</button>
            </div>
          </section>
        </>
      )}
      {notice && <p style={{ fontSize: 13, color: 'var(--muted)' }}>{notice}</p>}
      <p className="muted">Stockage : localStorage du navigateur (métadonnées, points de contrôle et image compressée). Rien n’est envoyé sur un serveur. Limite : si l’image est trop lourde pour le stockage local, la fiche est gardée sans l’image — réimportez le scan pour la revoir. Carte de référence : Djibouti ADM1, geoBoundaries, licence ouverte. {t.loi25}.</p>
    </div>
  )
}
