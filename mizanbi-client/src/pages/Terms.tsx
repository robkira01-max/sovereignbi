import type { Dict } from '../lib/i18n'

interface Props {
  t: Dict
  go: (page: string) => void
}

export default function TermsPage({ t, go }: Props) {
  return (
    <div style={{ maxWidth: 740, margin: '0 auto', padding: '32px 16px 64px' }}>
      <button className="btn-ghost" onClick={() => go('home')} style={{ marginBottom: 24 }}>
        ← {t.back}
      </button>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>{t.terms.title}</h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 32 }}>{t.terms.updated}</p>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.terms.objectTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.terms.objectText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.terms.accessTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.terms.accessText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.terms.licenceTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.terms.licenceText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.terms.liabilityTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.terms.liabilityText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.terms.lawTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.terms.lawText}</p>
      </section>
    </div>
  )
}
