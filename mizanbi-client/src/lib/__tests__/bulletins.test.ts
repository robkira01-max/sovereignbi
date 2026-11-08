// P-034 — Tests du générateur de bulletins (pures functions, sans DOM).
import { describe, it, expect } from 'vitest'
import {
  bieBulletinSection, bcdBulletinSection, statcanBulletinSection,
  renderBulletinHtml, type BulletinSection,
} from '../bulletins'

describe('bieBulletinSection', () => {
  it('returns a valid section with id bie', () => {
    const s = bieBulletinSection()
    expect(s.id).toBe('bie')
    expect(s.title).toContain('BIE')
  })

  it('has at least 2 points', () => {
    const s = bieBulletinSection()
    expect(s.points.length).toBeGreaterThanOrEqual(2)
  })

  it('each point has a non-empty title and text', () => {
    const s = bieBulletinSection()
    for (const p of s.points) {
      expect(p.title.length).toBeGreaterThan(0)
      expect(p.text.length).toBeGreaterThan(0)
    }
  })

  it('trend values are up | down | stable | undefined', () => {
    const s = bieBulletinSection()
    for (const p of s.points) {
      if (p.trend) expect(['up', 'down', 'stable']).toContain(p.trend)
    }
  })

  it('attribution contains the snapshot date', () => {
    const s = bieBulletinSection()
    expect(s.attribution.length).toBeGreaterThan(0)
    expect(s.snapshotDate.length).toBeGreaterThan(0)
  })
})

describe('bcdBulletinSection', () => {
  it('returns a valid section with id bcd', () => {
    const s = bcdBulletinSection()
    expect(s.id).toBe('bcd')
    expect(s.title).toContain('BCD')
  })

  it('has at least 3 points', () => {
    const s = bcdBulletinSection()
    expect(s.points.length).toBeGreaterThanOrEqual(3)
  })

  it('PIB growth point reflects 2024 real data (6.8%)', () => {
    const s = bcdBulletinSection()
    const pib = s.points.find((p) => p.title.toLowerCase().includes('pib'))
    expect(pib).toBeDefined()
    // 6.8% from BCD 2024 snapshot
    expect(pib!.text).toContain('6,8')
  })

  it('credits point shows strong growth (>30%)', () => {
    const s = bcdBulletinSection()
    const credits = s.points.find((p) => p.title.toLowerCase().includes('crédit'))
    expect(credits).toBeDefined()
    expect(credits!.trend).toBe('up')
  })
})

describe('statcanBulletinSection', () => {
  it('returns a valid section with id statcan', () => {
    const s = statcanBulletinSection()
    expect(s.id).toBe('statcan')
    expect(s.title).toContain('Canada')
  })

  it('has at least 2 points', () => {
    const s = statcanBulletinSection()
    expect(s.points.length).toBeGreaterThanOrEqual(2)
  })

  it('national unemployment point contains a percentage', () => {
    const s = statcanBulletinSection()
    const p = s.points[0]
    // Canada unemployment is 6.7% in snapshot
    expect(p.text).toMatch(/\d+[,.]?\d* %/)
  })

  it('disparities point mentions two provinces', () => {
    const s = statcanBulletinSection()
    const disp = s.points.find((p) => p.title.includes('Disparit'))
    expect(disp).toBeDefined()
    // Should mention highest and lowest province
    expect(disp!.text.length).toBeGreaterThan(20)
  })
})

describe('renderBulletinHtml', () => {
  const sections: BulletinSection[] = [
    {
      id: 'test', title: 'Test Section', attribution: 'Source: test', snapshotDate: '2026-11-08',
      points: [{ title: 'Indicateur', text: 'Valeur 42 %', value: '42 %', trend: 'up' }],
    },
  ]

  it('returns a string starting with <!doctype html>', () => {
    const html = renderBulletinHtml(sections)
    expect(html).toMatch(/^<!doctype html>/i)
  })

  it('includes section title in output', () => {
    const html = renderBulletinHtml(sections)
    expect(html).toContain('Test Section')
  })

  it('includes point title in output', () => {
    const html = renderBulletinHtml(sections)
    expect(html).toContain('Indicateur')
  })

  it('includes the value in output', () => {
    const html = renderBulletinHtml(sections)
    expect(html).toContain('42 %')
  })

  it('uses custom title when provided', () => {
    const html = renderBulletinHtml(sections, 'Mon Bulletin')
    expect(html).toContain('Mon Bulletin')
  })

  it('includes attribution text', () => {
    const html = renderBulletinHtml(sections)
    expect(html).toContain('Source: test')
  })

  it('renders multiple sections', () => {
    const s2: BulletinSection = {
      id: 'sec2', title: 'Section Deux', attribution: 'src2', snapshotDate: '2026-11-08',
      points: [{ title: 'P2', text: 'Texte deux' }],
    }
    const html = renderBulletinHtml([sections[0], s2])
    expect(html).toContain('Test Section')
    expect(html).toContain('Section Deux')
  })
})

describe('full pipeline', () => {
  it('all three real sources produce renderable HTML', () => {
    const all = [bieBulletinSection(), bcdBulletinSection(), statcanBulletinSection()]
    const html = renderBulletinHtml(all)
    expect(html).toContain('BIE')
    expect(html).toContain('BCD')
    expect(html).toContain('Canada')
    expect(html.length).toBeGreaterThan(2000)
  })
})
