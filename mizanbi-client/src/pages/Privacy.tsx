import type { Dict } from '../lib/i18n'

interface Props {
  t: Dict
  go: (page: string) => void
}

export default function PrivacyPage({ t, go }: Props) {
  return (
    <div style={{ maxWidth: 740, margin: '0 auto', padding: '32px 16px 64px' }}>
      <button className="btn-ghost" onClick={() => go('home')} style={{ marginBottom: 24 }}>
        ← {t.back}
      </button>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>{t.privacy.title}</h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 32 }}>{t.privacy.updated}</p>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.privacy.whoTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.privacy.whoText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.privacy.dataTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.privacy.dataText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.privacy.cookiesTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.privacy.cookiesText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.privacy.rightsTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.privacy.rightsText}</p>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{t.privacy.contactTitle}</h2>
        <p style={{ lineHeight: 1.7 }}>{t.privacy.contactText}</p>
      </section>
    </div>
  )
}
