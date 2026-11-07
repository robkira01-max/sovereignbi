import { ReactNode, useEffect, useRef, useState } from 'react'

export interface ScrollyStep {
  title?: string
  body: ReactNode
}

interface Props {
  steps: ScrollyStep[]
  figure: (activeIndex: number) => ReactNode
  figureWidth?: string
}

export function ScrollySection({ steps, figure, figureWidth = '42%' }: Props) {
  const [active, setActive] = useState(0)
  const stepRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const els = stepRefs.current.filter(Boolean) as HTMLDivElement[]
    if (!els.length) return

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const idx = Number(entry.target.getAttribute('data-step-index'))
            if (!Number.isNaN(idx)) setActive(idx)
          }
        })
      },
      { rootMargin: '-45% 0px -45% 0px', threshold: 0 }
    )
    els.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [steps.length])

  return (
    <div data-testid="scrolly-section" style={{ display: 'flex', gap: 32, alignItems: 'flex-start' }}>
      <div
        data-testid="scrolly-figure"
        style={{ flex: `0 0 ${figureWidth}`, position: 'sticky', top: 24, alignSelf: 'flex-start' }}
      >
        {figure(active)}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {steps.map((step, i) => (
          <div
            key={i}
            ref={el => { stepRefs.current[i] = el }}
            data-step-index={i}
            data-testid={`scrolly-step-${i}`}
            style={{
              minHeight: '70vh',
              paddingBottom: 48,
              paddingTop: 16,
              paddingLeft: 20,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              borderLeft: `2px solid ${i === active ? 'oklch(65% 0.22 265 / 0.6)' : 'oklch(27% 0.05 265)'}`,
              transition: 'border-color 0.3s',
            }}
          >
            {step.title && (
              <h3 style={{ margin: '0 0 12px', fontSize: 18, fontWeight: 700, color: 'var(--text)', lineHeight: 1.3 }}>
                {step.title}
              </h3>
            )}
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.75, color: 'oklch(85% 0.03 265)' }}>
              {step.body}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
