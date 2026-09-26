import { useMemo, useState } from 'react'
import type { TopicTrackingItem } from '../../../types/tracking'
import { CHART, daysSince, retentionAt, useElementWidth } from '../retention'

const HORIZON_DAYS = 30
const HEIGHT = 220
const M = { top: 12, right: 16, bottom: 24, left: 36 }
const X_TICKS = [0, 7, 14, 21, 30]
const Y_TICKS = [0, 0.25, 0.5, 0.75, 1]

interface Curve {
  topic: TopicTrackingItem
  age: number // days since last review
}

/**
 * Projected retention of every tracked topic over the next 30 days.
 * All topics are drawn as recessive context; one topic (hovered here or in the
 * list below) is highlighted in the accent color.
 */
export default function ForgettingCurvesChart({
  topics,
  highlightedId,
  onHighlight,
}: {
  topics: TopicTrackingItem[]
  highlightedId: number | null
  onHighlight: (topicId: number | null) => void
}) {
  const { ref, width } = useElementWidth<HTMLDivElement>()
  const [hoverDay, setHoverDay] = useState<number | null>(null)

  const curves: Curve[] = useMemo(() => {
    const now = Date.now()
    return topics
      .filter((t) => t.last_reviewed_at)
      .map((t) => ({ topic: t, age: daysSince(t.last_reviewed_at!, now) }))
  }, [topics])

  const plotW = Math.max(0, width - M.left - M.right)
  const plotH = HEIGHT - M.top - M.bottom
  const x = (day: number) => M.left + (day / HORIZON_DAYS) * plotW
  const y = (r: number) => M.top + (1 - r) * plotH

  const valueAt = (c: Curve, day: number) => retentionAt(c.age + day, c.topic.stability_days)

  const path = (c: Curve) => {
    const steps = 60
    let d = ''
    for (let i = 0; i <= steps; i++) {
      const day = (i / steps) * HORIZON_DAYS
      d += `${i === 0 ? 'M' : 'L'}${x(day).toFixed(1)},${y(valueAt(c, day)).toFixed(1)}`
    }
    return d
  }

  const highlighted = curves.find((c) => c.topic.topic_id === highlightedId) ?? null

  function handleMove(e: React.MouseEvent<SVGRectElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const day = Math.min(HORIZON_DAYS, Math.max(0, ((e.clientX - rect.left) / rect.width) * HORIZON_DAYS))
    const r = 1 - (e.clientY - rect.top) / rect.height
    // Highlight the curve closest to the pointer at this day
    let nearest: Curve | null = null
    let best = Infinity
    for (const c of curves) {
      const dist = Math.abs(valueAt(c, day) - r)
      if (dist < best) {
        best = dist
        nearest = c
      }
    }
    setHoverDay(day)
    if (nearest) onHighlight(nearest.topic.topic_id)
  }

  function handleLeave() {
    setHoverDay(null)
    onHighlight(null)
  }

  if (curves.length === 0) return null

  const nextReviewDay =
    highlighted?.topic.next_review_at != null
      ? -daysSince(highlighted.topic.next_review_at)
      : null
  const tooltipValue = highlighted && hoverDay != null ? valueAt(highlighted, hoverDay) : null
  const tooltipLeft = hoverDay != null ? x(hoverDay) : 0

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-text">Forgetting curves</p>
          <p className="text-xxs text-text-tertiary">Projected retention over the next 30 days if nothing is reviewed</p>
        </div>
        <div className="flex items-center gap-1.5 min-w-0">
          {highlighted ? (
            <>
              <span className="w-3 h-0.5 rounded-full shrink-0" style={{ backgroundColor: CHART.accent }} />
              <span className="text-xxs text-text-secondary truncate">{highlighted.topic.name}</span>
            </>
          ) : (
            <span className="text-xxs text-text-tertiary">Hover a curve or a topic to highlight it</span>
          )}
        </div>
      </div>

      <div ref={ref} className="relative w-full" style={{ height: HEIGHT }}>
        {width > 0 && (
          <svg width={width} height={HEIGHT} role="img" aria-label="Projected retention curves for tracked topics">
            {Y_TICKS.map((t) => (
              <g key={t}>
                <line x1={M.left} x2={M.left + plotW} y1={y(t)} y2={y(t)} stroke={CHART.grid} strokeWidth={1} />
                <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={10} fill={CHART.textMuted} style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {Math.round(t * 100)}%
                </text>
              </g>
            ))}
            {X_TICKS.map((d) => (
              <text key={d} x={x(d)} y={HEIGHT - 6} textAnchor={d === 0 ? 'start' : d === HORIZON_DAYS ? 'end' : 'middle'} fontSize={10} fill={CHART.textMuted}>
                {d === 0 ? 'Today' : `+${d}d`}
              </text>
            ))}

            {curves.map((c) =>
              c.topic.topic_id === highlightedId ? null : (
                <path key={c.topic.topic_id} d={path(c)} fill="none" stroke={CHART.context} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
              )
            )}

            {highlighted && (
              <g>
                <path d={path(highlighted)} fill="none" stroke={CHART.accent} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                <circle cx={x(0)} cy={y(valueAt(highlighted, 0))} r={4} fill={CHART.accent} stroke={CHART.surface} strokeWidth={2} />
                {nextReviewDay != null && nextReviewDay > 0 && nextReviewDay <= HORIZON_DAYS && (
                  <circle cx={x(nextReviewDay)} cy={y(valueAt(highlighted, nextReviewDay))} r={4} fill={CHART.surface} stroke={CHART.accent} strokeWidth={2} />
                )}
              </g>
            )}

            {hoverDay != null && (
              <line x1={x(hoverDay)} x2={x(hoverDay)} y1={M.top} y2={M.top + plotH} stroke={CHART.textMuted} strokeWidth={1} />
            )}
            {highlighted && tooltipValue != null && hoverDay != null && (
              <circle cx={x(hoverDay)} cy={y(tooltipValue)} r={4} fill={CHART.accent} stroke={CHART.surface} strokeWidth={2} pointerEvents="none" />
            )}

            <rect
              x={M.left}
              y={M.top}
              width={plotW}
              height={plotH}
              fill="transparent"
              onMouseMove={handleMove}
              onMouseLeave={handleLeave}
            />
          </svg>
        )}

        {highlighted && tooltipValue != null && hoverDay != null && (
          <div
            className="absolute top-2 pointer-events-none px-2.5 py-1.5 rounded-lg bg-bg-elevated border border-line-strong shadow-lg"
            style={{
              left: tooltipLeft,
              transform: tooltipLeft > width / 2 ? 'translateX(calc(-100% - 10px))' : 'translateX(10px)',
            }}
          >
            <p className="text-xxs font-medium text-text whitespace-nowrap max-w-48 truncate">{highlighted.topic.name}</p>
            <p className="text-xxs text-text-secondary whitespace-nowrap">
              {hoverDay < 0.5 ? 'Today' : `In ${Math.round(hoverDay)}d`} · {Math.round(tooltipValue * 100)}% retained
            </p>
          </div>
        )}
      </div>
      {highlighted && nextReviewDay != null && nextReviewDay > 0 && nextReviewDay <= HORIZON_DAYS && (
        <p className="text-xxs text-text-tertiary -mt-1">
          Hollow dot: next scheduled review ({Math.round(nextReviewDay)}d)
        </p>
      )}
    </div>
  )
}
