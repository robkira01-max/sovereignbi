import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ProvenanceBadge, effectiveProvenance } from '../../components/ProvenanceBadge'
import { I18N } from '../i18n'

const txt = (l: 'fr' | 'en') => ({ calculated: I18N[l].provCalculated, exploratory: I18N[l].provExploratory, unavailable: I18N[l].provUnavailable, seeCalc: I18N[l].seeCalc })
const html = (info: Parameters<typeof ProvenanceBadge>[0]['info'], open?: (id: string) => void, l: 'fr' | 'en' = 'fr') =>
  renderToStaticMarkup(createElement(ProvenanceBadge, { info, text: txt(l), onOpenRun: open }))

describe('P-080 — pastille Calculé / Exploratoire', () => {
  it('shows « Calculé » with formula, version, run and the link only when a run exists', () => {
    const h = html({ provenance: 'calculated', formula: { code: 'BUD001', version: 1, label: 'x' }, runId: 'abcdef1234567890' }, () => {})
    expect(h).toContain('data-provenance="calculated"')
    expect(h).toContain('Calculé') ; expect(h).toContain('BUD001 v1') ; expect(h).toContain('abcdef12') ; expect(h).toContain('Voir le calcul')
  })
  it('never says « Calculé » without a run: falls back to exploratory', () => {
    expect(effectiveProvenance({ provenance: 'calculated', runId: null })).toBe('exploratory')
    const h = html({ provenance: 'calculated', formula: { code: 'BUD001', version: 1, label: 'x' } })
    expect(h).not.toContain('Calculé') ; expect(h).toContain('Exploratoire, non certifié') ; expect(h).not.toContain('Voir le calcul')
  })
  it('labels exploratory answers and blocked calculations distinctly, with no link', () => {
    expect(html({ provenance: 'exploratory' }, () => {})).toContain('Exploratoire, non certifié')
    const b = html({ provenance: 'formula_unavailable', runId: 'x' }, () => {})
    expect(b).toContain('Calcul non effectué') ; expect(b).not.toContain('Voir le calcul') ; expect(b).not.toContain('Calculé')
  })
  it('renders nothing when the server gave no provenance (general mode)', () => {
    expect(html({})).toBe('') ; expect(html({ provenance: null })).toBe('') ; expect(html({ provenance: 'weird' })).toBe('')
  })
  it('is translated in English', () => {
    expect(html({ provenance: 'exploratory' }, undefined, 'en')).toContain('Exploratory, not certified')
    expect(I18N.en.provCalculated).toBe('Calculated')
  })
})
