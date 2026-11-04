import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Page } from '../components/AppShell'

interface HomePageProps {
  onNavigate: (page: Exclude<Page, 'home'>) => void
}

function Sparkline({ heights, color = 'var(--brand)' }: { heights: number[]; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 28, marginTop: 14 }}>
      {heights.map((h, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: `${h}%`,
            borderRadius: '3px 3px 0 0',
            background: i === heights.length - 1 ? color : `oklch(from ${color} l c h / 0.3)`,
            transition: 'height 0.3s',
          }}
        />
      ))}
    </div>
  )
}

interface KpiCardProps {
  label: string
  value: string
  delta?: string
  deltaUp?: boolean
  sparkHeights?: number[]
  accentColor?: string
}

function KpiCard({ label, value, delta, deltaUp, sparkHeights, accentColor = 'var(--brand)' }: KpiCardProps) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-card)',
      padding: '24px',
      backdropFilter: 'blur(12px)',
      position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 'var(--radius-card)',
        background: `linear-gradient(135deg, oklch(from ${accentColor} l c h / 0.05) 0%, transparent 60%)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
        textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 32, fontWeight: 500, color: 'var(--text)', lineHeight: 1,
      }}>
        {value}
        {delta && (
          <span style={{
            fontSize: 14, marginLeft: 8,
            color: deltaUp === false ? 'var(--warning)' : accentColor,
            fontFamily: 'inherit',
          }}>
            {delta}
          </span>
        )}
      </div>
      {sparkHeights && <Sparkline heights={sparkHeights} color={accentColor} />}
    </div>
  )
}

export function HomePage({ onNavigate }: HomePageProps) {
  const [tables, setTables] = useState<string[]>([])
  const [loadingTables, setLoadingTables] = useState(true)

  useEffect(() => {
    api.health()
      .then((data: unknown) => setTables((data as { tables?: string[] }).tables ?? []))
      .catch(() => {})
      .finally(() => setLoadingTables(false))
  }, [])

  const activityHeights = [40, 65, 50, 80, 60, 90, 75]
  const activityDays = ['LUN', 'MAR', 'MER', 'JEU', 'VEN', 'SAM', 'DIM']

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Welcome */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontSize: 28, fontWeight: 700, letterSpacing: '-0.5px',
          margin: '0 0 4px',
          background: 'linear-gradient(135deg, #f0f0fa, oklch(75% 0.15 265))',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>
          Bonjour, Robleh 👋
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-muted)', margin: 0 }}>
          Que voulez-vous analyser aujourd'hui ?
        </p>
      </div>

      {/* Bento grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr 1fr',
        gridTemplateRows: 'auto auto',
        gap: 16,
      }}>
        {/* KPI 1 — Lignes */}
        <KpiCard
          label="Lignes analysées"
          value={loadingTables ? '—' : '24 580'}
          delta="▲ 12%"
          deltaUp={true}
          sparkHeights={[40, 55, 35, 70, 60, 80, 65, 100]}
          accentColor="var(--brand)"
        />

        {/* KPI 2 — Précision */}
        <KpiCard
          label="Précision IA"
          value="98.2%"
          delta="▲ Optimal"
          deltaUp={true}
          sparkHeights={[90, 85, 92, 88, 95, 96, 94, 100]}
          accentColor="var(--accent)"
        />

        {/* Chat panel — 2×2 */}
        <div style={{
          gridColumn: 'span 2', gridRow: 'span 2',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-card)',
          backdropFilter: 'blur(12px)',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 0 40px oklch(65% 0.22 265 / 0.06)',
        }}>
          <div style={{
            padding: '20px 24px 16px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--text-muted)',
            }}>Q&A — Intelligence analytique</span>
            <span style={{
              marginLeft: 'auto',
              background: 'var(--accent-dim)', color: 'var(--accent)',
              border: '1px solid oklch(68% 0.18 155 / 0.3)',
              borderRadius: 999, padding: '2px 10px',
              fontSize: 10, fontWeight: 600,
            }}>En ligne</span>
          </div>

          <div style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
            {/* User message */}
            <div style={{
              alignSelf: 'flex-end',
              background: 'var(--brand-dim)',
              border: '1px solid var(--brand-glow)',
              borderRadius: '12px 12px 4px 12px',
              padding: '10px 14px', fontSize: 13,
              color: 'var(--text)', maxWidth: '80%',
            }}>
              Quel est le total des ventes par région ce trimestre ?
            </div>

            {/* AI response */}
            <div style={{ maxWidth: '90%' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: 'var(--accent)',
                  boxShadow: '0 0 8px var(--accent)',
                  display: 'inline-block', flexShrink: 0,
                }} />
                <span style={{
                  fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
                  textTransform: 'uppercase', color: 'var(--accent)',
                }}>Raisonnement</span>
              </div>
              {/* SQL block */}
              <div style={{
                background: 'oklch(10% 0.02 265 / 0.6)',
                border: '1px solid oklch(68% 0.18 155 / 0.2)',
                borderRadius: 8, padding: '10px 14px',
                marginBottom: 8,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11, lineHeight: 1.7,
                color: 'oklch(68% 0.18 155 / 0.8)',
              }}>
                <div style={{ fontSize: 10, color: 'oklch(68% 0.18 155 / 0.6)', marginBottom: 4, letterSpacing: '0.1em' }}>↳ SQL GÉNÉRÉ</div>
                <div><span style={{ color: 'var(--brand)' }}>SELECT</span> region, SUM(ventes) <span style={{ color: 'var(--brand)' }}>AS</span> total</div>
                <div><span style={{ color: 'var(--brand)' }}>FROM</span> transactions</div>
                <div><span style={{ color: 'var(--brand)' }}>WHERE</span> date &gt;= <span style={{ color: 'var(--warning)' }}>'2026-01-01'</span></div>
                <div><span style={{ color: 'var(--brand)' }}>GROUP BY</span> region <span style={{ color: 'var(--brand)' }}>ORDER BY</span> total <span style={{ color: 'var(--brand)' }}>DESC</span></div>
              </div>
              <div style={{ fontSize: 13, color: 'oklch(85% 0.02 265)', lineHeight: 1.6 }}>
                J'ai trouvé{' '}
                <strong style={{ color: 'var(--text)' }}>4 régions</strong>
                {' '}avec un total combiné de{' '}
                <strong style={{ color: 'oklch(75% 0.2 265)' }}>170 800 €</strong>.
                {' '}L'Est domine avec +24% vs N-1.
              </div>
            </div>
          </div>

          {/* Input */}
          <div style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex', gap: 10,
          }}>
            <button
              onClick={() => onNavigate('chat')}
              style={{
                flex: 1, background: 'oklch(10% 0.02 265 / 0.8)',
                border: '1px solid var(--border)',
                borderRadius: 10, padding: '10px 14px',
                fontSize: 13, color: 'var(--text-muted)',
                fontFamily: 'inherit', cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              Posez une question sur vos données…
            </button>
            <button
              onClick={() => onNavigate('chat')}
              style={{
                width: 38, height: 38, borderRadius: 10, flexShrink: 0,
                background: 'var(--brand)', border: 'none',
                color: '#fff', fontSize: 16, cursor: 'pointer',
                fontFamily: 'inherit',
                boxShadow: '0 0 16px var(--brand-glow)',
              }}
            >↑</button>
          </div>
        </div>

        {/* KPI 3 — Requêtes */}
        <KpiCard
          label="Requêtes / jour"
          value="847"
          delta="↗"
          deltaUp={true}
          sparkHeights={[30, 50, 45, 65, 55, 75, 70, 100]}
          accentColor="var(--warning)"
        />

        {/* KPI 4 — Sources */}
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-card)',
          padding: '24px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12,
          }}>
            Tables connectées
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 32, fontWeight: 500, color: 'var(--text)', lineHeight: 1, marginBottom: 14,
          }}>
            {loadingTables ? '—' : tables.length}
            {' '}<span style={{ fontSize: 12, color: 'var(--accent)', fontFamily: 'inherit' }}>
              {tables.length > 0 ? 'actives' : 'aucune'}
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {tables.length > 0 ? tables.slice(0, 3).map((tb, i) => (
              <div key={tb} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                  background: i < 2 ? 'var(--accent)' : 'var(--warning)',
                  boxShadow: `0 0 6px ${i < 2 ? 'var(--accent)' : 'var(--warning)'}`,
                  display: 'inline-block',
                }} />
                {tb}
              </div>
            )) : (
              <button
                onClick={() => onNavigate('data')}
                style={{
                  fontSize: 12, color: 'var(--brand)',
                  background: 'none', border: 'none',
                  cursor: 'pointer', fontFamily: 'inherit',
                  padding: 0, textAlign: 'left',
                }}
              >+ Importer des données</button>
            )}
          </div>
        </div>

        {/* Activity chart — 2 wide */}
        <div style={{
          gridColumn: 'span 2',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-card)',
          padding: '24px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16,
          }}>
            Activité — 7 derniers jours
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 60 }}>
            {activityHeights.map((h, i) => (
              <div
                key={i}
                style={{
                  flex: 1, borderRadius: '4px 4px 0 0',
                  background: 'var(--brand-dim)',
                  position: 'relative', overflow: 'hidden', height: '100%',
                }}
              >
                <div style={{
                  position: 'absolute', bottom: 0, left: 0, right: 0,
                  height: `${h}%`,
                  borderRadius: '4px 4px 0 0',
                  background: 'linear-gradient(to top, var(--brand), oklch(70% 0.18 290))',
                  transition: 'height 0.5s',
                }} />
              </div>
            ))}
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', marginTop: 8,
            fontSize: 10, color: 'var(--text-dim)',
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {activityDays.map(d => <span key={d}>{d}</span>)}
          </div>
        </div>
      </div>

      {/* Quick links row */}
      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        {([
          { id: 'dashboards', icon: '▦', label: 'Rapports & Dashboards' },
          { id: 'data',       icon: '⬆', label: 'Importer des données' },
        ] as const).map(item => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id as Exclude<Page, 'home'>)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 12, padding: '14px 20px',
              fontSize: 13, color: 'var(--text)',
              cursor: 'pointer', fontFamily: 'inherit',
              backdropFilter: 'blur(12px)',
              transition: 'border-color 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--brand-glow)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)' }}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            <span style={{ fontWeight: 500 }}>{item.label}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--text-dim)', fontSize: 12 }}>→</span>
          </button>
        ))}
      </div>
    </div>
  )
}
