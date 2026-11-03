import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useLocale } from '../hooks/useLocale'
import type { Page } from '../components/AppShell'

interface HomePageProps {
  onNavigate: (page: Exclude<Page, 'home'>) => void
}

export function HomePage({ onNavigate }: HomePageProps) {
  const { t } = useLocale()
  const [tables, setTables] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.health()
      .then((data: unknown) => setTables((data as { tables?: string[] }).tables ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const QUICK_ACTIONS: { icon: string; label: string; page: Exclude<Page, 'home'>; desc: string }[] = [
    { icon: '💬', label: t('home.action_chat'),      page: 'chat',       desc: t('home.action_chat_desc') },
    { icon: '📊', label: t('home.action_dashboard'),  page: 'dashboards', desc: t('home.action_dashboard_desc') },
    { icon: '📁', label: t('home.action_upload'),     page: 'data',       desc: t('home.action_upload_desc') },
  ]

  return (
    <div style={{ maxWidth: 900 }}>
      {/* Welcome */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 6px', color: 'var(--text)' }}>
          {t('home.welcome')}
        </h1>
        <p style={{ color: 'var(--muted)', margin: 0, fontSize: '0.9rem' }}>
          {t('home.subtitle')}
        </p>
      </div>

      {/* Quick actions */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 40,
      }}>
        {QUICK_ACTIONS.map(action => (
          <button
            key={action.page}
            onClick={() => onNavigate(action.page)}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-card)',
              padding: '20px',
              cursor: 'pointer',
              textAlign: 'left',
              boxShadow: 'var(--shadow-card)',
              transition: 'box-shadow 0.15s, transform 0.1s',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => {
              const b = e.currentTarget as HTMLButtonElement
              b.style.boxShadow = '0 4px 20px rgba(0,0,0,0.12)'
              b.style.transform = 'translateY(-1px)'
            }}
            onMouseLeave={e => {
              const b = e.currentTarget as HTMLButtonElement
              b.style.boxShadow = 'var(--shadow-card)'
              b.style.transform = 'none'
            }}
          >
            <div style={{ fontSize: '1.75rem', marginBottom: 10 }}>{action.icon}</div>
            <div style={{ fontWeight: 600, fontSize: '0.925rem', color: 'var(--text)', marginBottom: 4 }}>
              {action.label}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.4 }}>
              {action.desc}
            </div>
          </button>
        ))}
      </div>

      {/* Connected data sources */}
      <div>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12,
        }}>
          <h2 style={{
            fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)',
            textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0,
          }}>
            {t('home.data_sources')}
          </h2>
          <button
            onClick={() => onNavigate('data')}
            style={{
              fontSize: '0.8rem', color: 'var(--brand)',
              background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            + {t('home.add_source')}
          </button>
        </div>

        {loading ? (
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>…</p>
        ) : tables.length === 0 ? (
          <div style={{
            border: '2px dashed var(--border)',
            borderRadius: 'var(--radius-card)',
            padding: '40px 32px',
            textAlign: 'center',
            color: 'var(--muted)',
            fontSize: '0.875rem',
          }}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>📂</div>
            <div>{t('home.no_data')}</div>
            <button
              onClick={() => onNavigate('data')}
              style={{
                marginTop: 14,
                padding: '8px 20px',
                background: 'var(--brand)',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontFamily: 'inherit',
                fontWeight: 500,
              }}
            >
              {t('home.action_upload')}
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {tables.map(tb => (
              <div
                key={tb}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: '7px 14px',
                  fontSize: '0.825rem',
                  color: 'var(--text)',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <span>📄</span>
                <span style={{ fontWeight: 500 }}>{tb}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
