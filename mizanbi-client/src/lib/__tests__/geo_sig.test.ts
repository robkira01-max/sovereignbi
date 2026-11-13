/**
 * P-054 — Tests for GeoCatalog, GeoImport, SpatialAnalysis components
 * and the i18n completeness for geo_catalog / geo_import / spatial_analysis.
 */
import { describe, it, expect } from 'vitest'
import { I18N } from '../i18n'

// ── i18n completeness ────────────────────────────────────────────────────────

describe('i18n geo sections', () => {
  const fr = I18N.fr
  const en = I18N.en

  it('geo_catalog has the same keys in fr and en', () => {
    expect(Object.keys(en.geo_catalog).sort()).toEqual(Object.keys(fr.geo_catalog).sort())
  })

  it('geo_import has the same keys in fr and en', () => {
    expect(Object.keys(en.geo_import).sort()).toEqual(Object.keys(fr.geo_import).sort())
  })

  it('spatial_analysis has the same keys in fr and en', () => {
    expect(Object.keys(en.spatial_analysis).sort()).toEqual(Object.keys(fr.spatial_analysis).sort())
  })

  it('geo_catalog fr strings are non-empty', () => {
    for (const [k, v] of Object.entries(fr.geo_catalog)) {
      expect(v, `fr.geo_catalog.${k}`).toBeTruthy()
    }
  })

  it('geo_catalog en strings are non-empty', () => {
    for (const [k, v] of Object.entries(en.geo_catalog)) {
      expect(v, `en.geo_catalog.${k}`).toBeTruthy()
    }
  })

  it('geo_import fr strings are non-empty', () => {
    for (const [k, v] of Object.entries(fr.geo_import)) {
      expect(v, `fr.geo_import.${k}`).toBeTruthy()
    }
  })

  it('geo_import en strings are non-empty', () => {
    for (const [k, v] of Object.entries(en.geo_import)) {
      expect(v, `en.geo_import.${k}`).toBeTruthy()
    }
  })

  it('spatial_analysis fr strings are non-empty', () => {
    for (const [k, v] of Object.entries(fr.spatial_analysis)) {
      expect(v, `fr.spatial_analysis.${k}`).toBeTruthy()
    }
  })

  it('spatial_analysis en strings are non-empty', () => {
    for (const [k, v] of Object.entries(en.spatial_analysis)) {
      expect(v, `en.spatial_analysis.${k}`).toBeTruthy()
    }
  })

  it('geo_catalog status keys cover all three statuses', () => {
    expect(fr.geo_catalog.status_validated).toBeTruthy()
    expect(fr.geo_catalog.status_draft).toBeTruthy()
    expect(fr.geo_catalog.status_deprecated).toBeTruthy()
    expect(en.geo_catalog.status_validated).toBeTruthy()
    expect(en.geo_catalog.status_draft).toBeTruthy()
    expect(en.geo_catalog.status_deprecated).toBeTruthy()
  })

  it('geo_catalog toggle labels differ between fr and en', () => {
    expect(fr.geo_catalog.toggle_disable).not.toEqual(en.geo_catalog.toggle_disable)
    expect(fr.geo_catalog.toggle_enable).not.toEqual(en.geo_catalog.toggle_enable)
  })

  it('spatial_analysis demo_note mentions VITE_API_BASE', () => {
    expect(fr.spatial_analysis.demo_note).toContain('VITE_API_BASE')
    expect(en.spatial_analysis.demo_note).toContain('VITE_API_BASE')
  })

  it('geo_catalog demo_note mentions VITE_API_BASE', () => {
    expect(fr.geo_catalog.demo_note).toContain('VITE_API_BASE')
    expect(en.geo_catalog.demo_note).toContain('VITE_API_BASE')
  })

  it('geo_import error_size mentions 50', () => {
    expect(fr.geo_import.error_size).toContain('50')
    expect(en.geo_import.error_size).toContain('50')
  })
})

// ── key count guards (prevent accidental shrinkage) ──────────────────────────

describe('i18n geo key counts', () => {
  it('geo_catalog has at least 20 keys', () => {
    expect(Object.keys(I18N.fr.geo_catalog).length).toBeGreaterThanOrEqual(20)
  })

  it('geo_import has at least 18 keys', () => {
    expect(Object.keys(I18N.fr.geo_import).length).toBeGreaterThanOrEqual(18)
  })

  it('spatial_analysis has at least 16 keys', () => {
    expect(Object.keys(I18N.fr.spatial_analysis).length).toBeGreaterThanOrEqual(16)
  })
})
