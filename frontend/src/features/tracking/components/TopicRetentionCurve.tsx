import { useMemo, useState } from 'react'
import type { RecallHistoryEvent, TopicTrackingItem } from '../../../types/tracking'
import { CHART, DAY_MS, retentionAt, useElementWidth } from '../retention'

const HEIGHT = 130
const M = { top: 10, right: 12, bottom: 20, left: 32 }
const MAX_PAST_DAYS = 60
const MIN_FUTURE_DAYS = 7

interface Segment {
  start: number // ms
  end: number // ms
  stability: number
}

/**
 * Reconstructs a topic's memory over time: each recall event resets retention
 * to 100%, then it decays exponentially until the next one. The part after
 * today is a projection and is drawn fainter.
 */
export default function TopicRetentionCurve({
  topic,
  events,
}: {
  topic: TopicTrackingItem
  events: RecallHistoryEvent[]
}) {
  const { ref, width } = useElementWidth<HTMLDivElement>()
  const [hoverT, setHoverT] = useState<number | null>(null)

  const model = useMemo(() => {
    const now = Date.now()
    const sorted = [...events]
      .map((e) => ({ ...e, t: new Date(e.event_time).getTime() }))
      .sort((a, b) => a.t - b.t)
    if (sorted.length === 0) return null

    const nextReview = topic.next_review_at ? new Date(topic.next_review_at).getTime() : null
    const futureEnd = Math.max(
      now + MIN_FUTURE_DAYS * DAY_MS,
      nextReview ? nextReview + 2 * DAY_MS : 0,
    )
    const start = Math.max(sorted[0].t, now - MAX_PAST_DAYS * DAY_MS) - 0.5 * DAY_MS
    const segments: Segment[] = sorted.map((e, i) => ({
      start: e.t,
      end: i + 1 < sorted.length ? sorted[i + 1].t : futureEnd,
      stability: e.stability_days,
    }))
    return { now, start, end: futureEnd, segments, points: sorted, nextReview }
  }, [events, topic.next_review_at])

  if (!model) return null

  const plotW = Math.max(0, width - M.left - M.right)
  const plotH = HEIGHT - M.top - M.bottom
  const x = (t: number) => M.left + ((t - model.start) / (model.end - model.start)) * plotW
  const y = (r: number) => M.top + (1 - r) * plotH

  const valueAt = (t: number): number | null => {
    const seg = model.segments.find((s) => t >= s.start && t <= s.end)
    return seg ? retentionAt((t - seg.start) / DAY_MS, seg.stability) : null
  }

  // Build the sawtooth, split at "now" into observed and projected parts.
  // Segments are chained with L so each review draws its vertical jump back to 100%.
  const buildPath = (from: number, to: number) => {
    let d = ''
    for (const seg of model.segments) {
      const a = Math.max(seg.start, from)
      const b = Math.min(seg.end, to)
      if (b <= a) continue
      const steps = 40
      for (let i = 0; i <= steps; i++) {
        const t = a + ((b - a) * i) / steps
        const r = retentionAt((t - seg.start) / DAY_MS, seg.stability)
        d += `${d === '' ? 'M' : 'L'}${x(t).toFixed(1)},${y(r).toFixed(1)}`
      }
    }
    return d
  }
  const pastPath = buildPath(model.start, model.now)
  const futurePath = buildPath(model.now, model.end)
  // Area wash under the observed part only
  const firstVisible = Math.max(model.segments[0].start, model.start)
  const areaPath = pastPath
    ? `${pastPath}L${x(model.now).toFixed(1)},${y(0)}L${x(firstVisible).toFixed(1)},${y(0)}Z`
    : ''

  function handleMove(e: React.MouseEvent<SVGRectElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    setHoverT(model!.start + ratio * (model!.end - model!.start))
  }

  const hoverValue = hoverT != null ? valueAt(hoverT) : null
  const fmt = (t: number) => new Date(t).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const tooltipLeft = hoverT != null ? x(hoverT) : 0

  return (
    <div ref={ref} className="relative w-full" style={{ height: HEIGHT }}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={`Retention history for ${topic.name}`}>
          {[0, 0.5, 1].map((t) => (
            <g key={t}>
              <line x1={M.left} x2={M.left + plotW} y1={y(t)} y2={y(t)} stroke={CHART.grid} strokeWidth={1} />
              <text x={M.left - 6} y={y(t)} dy="0.32em" textAnchor="end" fontSize={10} fill={CHART.textMuted}>
                {Math.round(t * 100)}%
              </text>
            </g>
          ))}
          <text x={M.left} y={HEIGHT - 5} fontSize={10} fill={CHART.textMuted}>{fmt(model.start)}</text>
          <text x={M.left + plotW} y={HEIGHT - 5} textAnchor="end" fontSize={10} fill={CHART.textMuted}>{fmt(model.end)}</text>

          <line x1={x(model.now)} x2={x(model.now)} y1={M.top} y2={M.top + plotH} stroke={CHART.textMuted} strokeWidth={1} />
          <text x={x(model.now)} y={HEIGHT - 5} textAnchor="middle" fontSize={10} fill={CHART.textSecondary}>Today</text>

          {areaPath && <path d={areaPath} fill={CHART.accent} fillOpacity={0.1} />}
          {pastPath && <path d={pastPath} fill="none" stroke={CHART.accent} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />}
          {futurePath && <path d={futurePath} fill="none" stroke={CHART.accent} strokeOpacity={0.4} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />}

          {model.points
            .filter((p) => p.t >= model.start)
            .map((p, i) => (
              <circle key={i} cx={x(p.t)} cy={y(1)} r={4} fill={CHART.accent} stroke={CHART.surface} strokeWidth={2} />
            ))}
          {model.nextReview && model.nextReview > model.now && model.nextReview <= model.end && (
            <circle cx={x(model.nextReview)} cy={y(valueAt(model.nextReview) ?? 0)} r={4} fill={CHART.surface} stroke={CHART.accent} strokeWidth={2} />
          )}

          {hoverT != null && hoverValue != null && (
            <g pointerEvents="none">
              <line x1={x(hoverT)} x2={x(hoverT)} y1={M.top} y2={M.top + plotH} stroke={CHART.textMuted} strokeWidth={1} />
              <circle cx={x(hoverT)} cy={y(hoverValue)} r={4} fill={CHART.accent} stroke={CHART.surface} strokeWidth={2} />
            </g>
          )}

          <rect x={M.left} y={M.top} width={plotW} height={plotH} fill="transparent" onMouseMove={handleMove} onMouseLeave={() => setHoverT(null)} />
        </svg>
      )}

      {hoverT != null && hoverValue != null && (
        <div
          className="absolute top-1 pointer-events-none px-2.5 py-1.5 rounded-lg bg-bg-elevated border border-line-strong shadow-lg"
          style={{
            left: tooltipLeft,
            transform: tooltipLeft > width / 2 ? 'translateX(calc(-100% - 10px))' : 'translateX(10px)',
          }}
        >
          <p className="text-xxs text-text whitespace-nowrap">
            {fmt(hoverT)}{hoverT > model.now ? ' (projected)' : ''}
          </p>
          <p className="text-xxs text-text-secondary whitespace-nowrap">{Math.round(hoverValue * 100)}% retained</p>
        </div>
      )}
    </div>
  )
}
