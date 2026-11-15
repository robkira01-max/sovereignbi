import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { iconOf, labelOf, parseAiMode, titleOf, toneOf } from '../aiMode'
import { I18N } from '../i18n'
import AiModeBadge from '../../components/AiModeBadge'

const notice = (o: Record<string, unknown>) => ({
  ai_provider: 'kimi', ai_external: true, ai_strict_mode: true, data_location: "Infrastructure de l'opérateur",
  purposes: [{ id: 'analytics', description: 'x' }, { id: 'ai_processing', description: 'Traitement IA par un fournisseur externe (kimi) en mode strict' }], ...o,
})

describe('parseAiMode', () => {
  it('classifies the three situations', () => {
    expect(parseAiMode(notice({ ai_external: false, ai_provider: 'ollama', ai_strict_mode: false }))?.kind).toBe('local')
    expect(parseAiMode(notice({}))?.kind).toBe('external-strict')
    expect(parseAiMode(notice({ ai_strict_mode: false }))?.kind).toBe('external-open')
  })
  it('a local model never reads as external even if strict is on', () => {
    expect(parseAiMode(notice({ ai_external: false, ai_strict_mode: true }))?.kind).toBe('local')
  })
  it('shows nothing for missing or inconsistent data: never a reassuring default', () => {
    for (const bad of [null, undefined, 'x', 3, {}, { ai_strict_mode: true }, notice({ ai_external: 'true' }), notice({ ai_external: undefined }),
      notice({ ai_strict_mode: undefined }), notice({ ai_strict_mode: 'yes' }), notice({ ai_strict_mode: null })]) {
      expect(parseAiMode(bad)).toBeNull()
    }
  })
  it('keeps the provider, location and the AI description for the tooltip, ignoring malformed parts', () => {
    const m = parseAiMode(notice({}))!
    expect(m.provider).toBe('kimi')
    expect(m.dataLocation).toContain('opérateur')
    expect(m.description).toContain('mode strict')
    const odd = parseAiMode(notice({ ai_provider: 42, data_location: null, purposes: 'nope' }))!
    expect(odd).toMatchObject({ provider: '', dataLocation: '', description: '' })
  })
})

describe('labels, tones, tooltip', () => {
  for (const lang of ['fr', 'en'] as const) {
    const t = I18N[lang]
    it(`${lang}: each state has its own label and only the non-strict external state is a warning`, () => {
      const labels = (['local', 'external-strict', 'external-open'] as const).map((k) => labelOf(k, t))
      expect(new Set(labels).size).toBe(3)
      expect(toneOf('external-open')).toBe('warn')
      expect(toneOf('external-strict')).toBe('ok')
      expect(toneOf('local')).toBe('ok')
    })
    it(`${lang}: the tooltip names the provider and the data location`, () => {
      const title = titleOf(parseAiMode(notice({}))!, t)
      expect(title).toContain('kimi')
      expect(title).toContain(t.aiProvider)
      expect(title).toContain(t.aiLocation)
      expect(title).toContain('mode strict')
    })
  }
  it('uses a different icon for the warning (colour is never the only signal)', () => {
    expect(iconOf('external-open')).toBe('⚠')
    expect(new Set([iconOf('local'), iconOf('external-strict'), iconOf('external-open')]).size).toBe(3)
  })
  it('fr and en define all AI mode texts', () => {
    for (const k of ['aiLocal', 'aiExternalStrict', 'aiExternalOpen', 'aiProvider', 'aiLocation'] as const) {
      expect(I18N.fr[k]).toBeTruthy(); expect(I18N.en[k]).toBeTruthy(); expect(I18N.en[k]).not.toBe(I18N.fr[k])
    }
  })
})

describe('AiModeBadge', () => {
  it('renders nothing before data is known (no API in tests): no state is claimed', () => {
    const html = renderToStaticMarkup(createElement(QueryClientProvider, { client: new QueryClient() }, createElement(AiModeBadge, { t: I18N.fr })))
    expect(html).toBe('')
  })
})
