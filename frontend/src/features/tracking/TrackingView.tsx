import { useEffect, useMemo } from 'react'
import { RefreshCw, Brain, TrendingDown } from 'lucide-react'
import { useTrackingStore } from '../../stores/useTrackingStore'
import type { TopicTrackingItem, RecallHistoryEvent } from '../../types/tracking'

const TOPIC_COLORS = [
  '#6366f1', '#ec4899', '#f97316', '#14b8a6',
  '#84cc16', '#eab308', '#06b6d4', '#a855f7',
]

// --- Curve computation ---

interface CurvePoint { x: number; y: number }

function computeCurve(
  events: RecallHistoryEvent[],
  now: Date,
  minTime: number,
  maxTime: number,
  chartW: number,
  chartH: number,
): CurvePoint[] {
  if (events.length === 0) return []
  const timeRange = maxTime - minTime || 1
  const toX = (d: Date) => ((d.getTime() - minTime) / timeRange) * chartW
  const toY = (v: number) => chartH - v * chartH

  const points: CurvePoint[] = []
  for (let i = 0; i < events.length; i++) {
    const recallTime = new Date(events[i].event_time)
    const nextTime = events[i + 1] ? new Date(events[i + 1].event_time) : now
    const strength = events[i].strength
    const segmentMs = nextTime.getTime() - recallTime.getTime()
    // At least 2 points per segment, max 60 (1 per 6h)
    const steps = Math.max(2, Math.min(60, Math.ceil(segmentMs / (6 * 3600 * 1000))))
    for (let s = 0; s <= steps; s++) {
      const t = new Date(recallTime.getTime() + (segmentMs * s) / steps)
      const daysSince = (t.getTime() - recallTime.getTime()) / 86400000
      const score = Math.min(1.0, daysSince / (14.0 * Math.max(0.1, strength)))
      points.push({ x: toX(t), y: toY(score) })
    }
  }
  return points
}

// --- Topic list item ---

function TopicPill({
  topic,
  color,
  isSelected,
  onClick,
}: {
  topic: TopicTrackingItem
  color: string
  isSelected: boolean
  onClick: () => void
}) {
  const score = Math.round(topic.forgetting_score * 100)
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center gap-2 ${
        isSelected ? 'bg-accent/15 border border-accent/40' : 'hover:bg-surface-hover border border-transparent'
      }`}
    >
      <span className="shrink-0 w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span className="flex-1 min-w-0">
        <span className="block text-xs font-medium text-text truncate">{topic.name}</span>
        <span className="block text-xxs text-text-tertiary">{score}% forgotten</span>
      </span>
    </button>
  )
}

// --- Chart ---

const CHART_W = 260
const CHART_H = 140
const PAD = { top: 8, right: 8, bottom: 28, left: 28 }

function ForgettingChart({
  topics,
  histories,
  selectedTopicId,
}: {
  topics: TopicTrackingItem[]
  histories: Record<number, RecallHistoryEvent[]>
  selectedTopicId: number | null
}) {
  const now = new Date()

  // Determine global time range across all loaded topics
  const { minTime, maxTime } = useMemo(() => {
    let min = now.getTime()
    let max = now.getTime()
    for (const topic of topics) {
      const events = histories[topic.topic_id]
      if (events && events.length > 0) {
        const first = new Date(events[0].event_time).getTime()
        if (first < min) min = first
      } else if (topic.last_reviewed_at) {
        const t = new Date(topic.last_reviewed_at).getTime()
        if (t < min) min = t
      }
    }
    // Show at least 14 days of context
    const fourteenDaysMs = 14 * 24 * 3600 * 1000
    if (max - min < fourteenDaysMs) min = max - fourteenDaysMs
    return { minTime: min, maxTime: max }
  }, [topics, histories])

  const timeRange = maxTime - minTime || 1
  const toX = (d: Date) => PAD.left + ((d.getTime() - minTime) / timeRange) * CHART_W
  const toY = (v: number) => PAD.top + (1 - v) * CHART_H

  // X-axis tick labels
  const xTicks = useMemo(() => {
    const ticks = []
    const totalDays = (maxTime - minTime) / 86400000
    const tickCount = Math.min(5, Math.max(2, Math.floor(totalDays / 2)))
    for (let i = 0; i <= tickCount; i++) {
      const t = new Date(minTime + (i / tickCount) * (maxTime - minTime))
      ticks.push({ x: toX(t), label: t.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) })
    }
    return ticks
  }, [minTime, maxTime])

  const svgW = CHART_W + PAD.left + PAD.right
  const svgH = CHART_H + PAD.top + PAD.bottom

  return (
    <svg
      viewBox={`0 0 ${svgW} ${svgH}`}
      className="w-full h-full"
      style={{ maxHeight: '100%' }}
    >
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <line
          key={v}
          x1={PAD.left}
          x2={PAD.left + CHART_W}
          y1={toY(v)}
          y2={toY(v)}
          stroke="currentColor"
          strokeOpacity={0.08}
          strokeWidth={1}
        />
      ))}

      {/* Y-axis labels */}
      {[0, 0.5, 1].map((v) => (
        <text
          key={v}
          x={PAD.left - 4}
          y={toY(v) + 3}
          fontSize={7}
          textAnchor="end"
          fill="currentColor"
          opacity={0.4}
        >
          {Math.round(v * 100)}%
        </text>
      ))}

      {/* X-axis ticks */}
      {xTicks.map((tick, i) => (
        <text
          key={i}
          x={tick.x}
          y={PAD.top + CHART_H + 16}
          fontSize={7}
          textAnchor="middle"
          fill="currentColor"
          opacity={0.4}
        >
          {tick.label}
        </text>
      ))}

      {/* Axes */}
      <line
        x1={PAD.left} x2={PAD.left + CHART_W}
        y1={PAD.top + CHART_H} y2={PAD.top + CHART_H}
        stroke="currentColor" strokeOpacity={0.2} strokeWidth={1}
      />
      <line
        x1={PAD.left} x2={PAD.left}
        y1={PAD.top} y2={PAD.top + CHART_H}
        stroke="currentColor" strokeOpacity={0.2} strokeWidth={1}
      />

      {/* Curves */}
      {topics.map((topic, idx) => {
        const color = TOPIC_COLORS[idx % TOPIC_COLORS.length]
        const events = histories[topic.topic_id]
        const isSelected = topic.topic_id === selectedTopicId
        const opacity = selectedTopicId === null ? 1 : isSelected ? 1 : 0.18

        let polylinePoints = ''
        let dotX: number | null = null
        let dotY: number | null = null

        if (events && events.length > 0) {
          const pts = computeCurve(events, now, minTime, maxTime, CHART_W, CHART_H)
          // Offset into padded space
          polylinePoints = pts
            .map((p) => `${(p.x + PAD.left).toFixed(1)},${(p.y + PAD.top).toFixed(1)}`)
            .join(' ')
          const last = pts[pts.length - 1]
          if (last) {
            dotX = last.x + PAD.left
            dotY = last.y + PAD.top
          }
        } else if (topic.last_reviewed_at) {
          // Fallback: draw from last_reviewed_at to now using current state
          const recallDate = new Date(topic.last_reviewed_at)
          const days = (now.getTime() - recallDate.getTime()) / 86400000
          const score = Math.min(1.0, days / (14.0 * Math.max(0.1, topic.strength)))
          const x0 = toX(recallDate)
          const x1 = toX(now)
          const y0 = toY(0)
          const y1 = toY(score)
          polylinePoints = `${x0.toFixed(1)},${y0.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`
          dotX = x1
          dotY = y1
        }

        if (!polylinePoints) return null

        return (
          <g key={topic.topic_id} opacity={opacity}>
            <polyline
              points={polylinePoints}
              fill="none"
              stroke={color}
              strokeWidth={isSelected ? 2 : 1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {dotX !== null && dotY !== null && (
              <circle
                cx={dotX}
                cy={dotY}
                r={isSelected ? 4.5 : 3}
                fill={color}
                stroke="white"
                strokeWidth={1}
              />
            )}
          </g>
        )
      })}
    </svg>
  )
}

// --- Main view ---

export default function TrackingView() {
  const {
    topics,
    isLoading,
    isRecomputing,
    error,
    showDueOnly,
    topicHistories,
    selectedTopicId,
    loadTopics,
    toggleDueOnly,
    recompute,
    loadTopicHistory,
    selectTopic,
  } = useTrackingStore()

  useEffect(() => {
    loadTopics()
  }, [])

  // Load histories for all topics once they are available
  useEffect(() => {
    for (const topic of topics) {
      if (!(topic.topic_id in topicHistories)) {
        loadTopicHistory(topic.topic_id)
      }
    }
  }, [topics])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-line shrink-0">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-accent" />
          <h1 className="text-sm font-semibold text-text">Memory Tracking</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleDueOnly}
            className={`text-xxs font-medium px-3 py-1.5 rounded-lg transition-colors ${
              showDueOnly
                ? 'bg-accent text-white'
                : 'bg-surface text-text-secondary hover:bg-surface-hover'
            }`}
          >
            Due only
          </button>
          <button
            onClick={recompute}
            disabled={isRecomputing}
            className="flex items-center gap-1.5 text-xxs font-medium px-3 py-1.5 rounded-lg bg-surface text-text-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
          >
            <RefreshCw size={11} className={isRecomputing ? 'animate-spin' : ''} />
            Recompute
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-3">
          <RefreshCw size={20} className="text-accent animate-spin" />
          <p className="text-sm text-text-tertiary">Loading topics…</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-3">
          <TrendingDown size={32} strokeWidth={1.2} className="text-error" />
          <p className="text-sm text-error">{error}</p>
          <button onClick={loadTopics} className="text-xs text-accent hover:text-accent-hover transition-colors">
            Retry
          </button>
        </div>
      ) : topics.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 text-center">
          <div className="p-5 rounded-2xl bg-accent-subtle">
            <TrendingDown size={36} strokeWidth={1.2} className="text-accent" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-text">
              {showDueOnly ? 'No topics due for review' : 'No topics tracked yet'}
            </p>
            <p className="text-xs text-text-tertiary max-w-xs leading-relaxed">
              {showDueOnly
                ? 'All caught up! Come back later.'
                : 'Analyze a browsing session to start tracking learning topics.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 min-h-0">
          {/* Topic list */}
          <div className="w-36 shrink-0 border-r border-line overflow-y-auto thin-scrollbar p-2 flex flex-col gap-0.5">
            {topics.map((topic, idx) => (
              <TopicPill
                key={topic.topic_id}
                topic={topic}
                color={TOPIC_COLORS[idx % TOPIC_COLORS.length]}
                isSelected={topic.topic_id === selectedTopicId}
                onClick={() => selectTopic(topic.topic_id === selectedTopicId ? null : topic.topic_id)}
              />
            ))}
          </div>

          {/* Chart area */}
          <div className="flex-1 min-w-0 flex flex-col p-3 gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xxs text-text-tertiary">Forgetting score over time</span>
              {selectedTopicId !== null && (
                <button
                  onClick={() => selectTopic(null)}
                  className="text-xxs text-text-tertiary hover:text-text transition-colors"
                >
                  Show all
                </button>
              )}
            </div>
            <div className="flex-1 min-h-0">
              <ForgettingChart
                topics={topics}
                histories={topicHistories}
                selectedTopicId={selectedTopicId}
              />
            </div>
            {/* Selected topic detail */}
            {selectedTopicId !== null && (() => {
              const idx = topics.findIndex((t) => t.topic_id === selectedTopicId)
              const topic = topics[idx]
              if (!topic) return null
              const color = TOPIC_COLORS[idx % TOPIC_COLORS.length]
              const isDue = topic.next_review_at ? new Date(topic.next_review_at) <= new Date() : false
              const score = Math.round(topic.forgetting_score * 100)
              const lastSeen = topic.last_reviewed_at
                ? new Date(topic.last_reviewed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                : null
              return (
                <div className="rounded-xl bg-surface border border-line p-3 shrink-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-xs font-semibold text-text truncate">{topic.name}</span>
                    {isDue && (
                      <span className="shrink-0 text-xxs font-semibold text-error bg-error/10 px-2 py-0.5 rounded-full">
                        Due
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xxs text-text-tertiary">
                    <span><span className="font-medium text-text">{score}%</span> forgotten</span>
                    <span><span className="font-medium text-text">{topic.repetitions}</span> review{topic.repetitions !== 1 ? 's' : ''}</span>
                    {lastSeen && <span>Last seen <span className="font-medium text-text">{lastSeen}</span></span>}
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}
