import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Brain, TrendingDown, ChevronDown, ExternalLink } from 'lucide-react'
import { useTrackingStore } from '../../stores/useTrackingStore'
import { useSessionStore } from '../../stores/useSessionStore'
import type { TopicTrackingItem, RecallHistoryEvent } from '../../types/tracking'

const TOPIC_COLORS = [
  '#6366f1', '#ec4899', '#f97316', '#14b8a6',
  '#84cc16', '#eab308', '#06b6d4', '#a855f7',
]

function daysAgo(dateStr: string): string {
  const diff = (Date.now() - new Date(dateStr).getTime()) / 86400000
  if (diff < 1) return 'today'
  if (diff < 2) return '1d ago'
  return `${Math.floor(diff)}d ago`
}

function retentionLabel(forgettingScore: number): { pct: number; label: string; cls: string } {
  const pct = Math.round((1 - forgettingScore) * 100)
  if (pct >= 70) return { pct, label: 'Healthy', cls: 'text-success' }
  if (pct >= 40) return { pct, label: 'At risk', cls: 'text-yellow-500' }
  return { pct, label: 'Critical', cls: 'text-error' }
}

function StrengthDots({ strength }: { strength: number }) {
  const filled = Math.round(strength * 5)
  return (
    <span className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < filled ? 'bg-text-secondary' : 'bg-surface-active'}`}
        />
      ))}
    </span>
  )
}

function EventTimeline({ events, color }: { events: RecallHistoryEvent[]; color: string }) {
  const navigate = useNavigate()
  const setActiveSession = useSessionStore((s) => s.setActiveSession)

  if (events.length === 0) {
    return <p className="text-xxs text-text-tertiary italic">No recall events yet.</p>
  }

  const sorted = [...events].sort(
    (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime()
  )

  async function goToSession(sessionIdentifier: string) {
    await setActiveSession(sessionIdentifier)
    navigate('/sessions')
  }

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((e, i) => {
        const ret = Math.round((1 - e.forgetting_score) * 100)
        const date = new Date(e.event_time).toLocaleDateString(undefined, {
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })
        const isObserved = e.event_type === 'observed' && !!e.session_identifier

        return (
          <div key={i} className="flex items-start gap-2 group">
            <span className="mt-0.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
            <div className="min-w-0 flex items-center gap-1.5 flex-wrap">
              <span className="text-xxs font-medium text-text capitalize">{e.event_type}</span>
              <span className="text-xxs text-text-tertiary">· {date}</span>
              <span className="text-xxs text-text-tertiary">· {ret}% retained</span>
              {isObserved && (
                <button
                  onClick={() => goToSession(e.session_identifier!)}
                  className="flex items-center gap-0.5 text-xxs text-accent hover:text-accent-hover transition-colors opacity-0 group-hover:opacity-100"
                  title="Open session"
                >
                  <ExternalLink size={9} />
                  <span>View session</span>
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function TopicRow({
  topic,
  color,
  events,
  isLoadingHistory,
  onOpen,
}: {
  topic: TopicTrackingItem
  color: string
  events: RecallHistoryEvent[] | undefined
  isLoadingHistory: boolean
  onOpen: () => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { pct, cls } = retentionLabel(topic.forgetting_score)
  const isDue = topic.next_review_at ? new Date(topic.next_review_at) <= new Date() : false
  const lastSeen = topic.last_reviewed_at ? daysAgo(topic.last_reviewed_at) : null
  const nextReview = topic.next_review_at
    ? new Date(topic.next_review_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null

  function handleToggle() {
    if (!isOpen && events === undefined) onOpen()
    setIsOpen((v) => !v)
  }

  return (
    <div className="border-b border-line last:border-b-0">
      {/* Row header */}
      <button
        onClick={handleToggle}
        className="w-full px-5 py-3 flex items-center gap-3 hover:bg-surface-hover transition-colors text-left"
      >
        <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />

        <span className="flex-1 text-sm font-medium text-text truncate min-w-0">{topic.name}</span>

        {isDue && (
          <span className="shrink-0 text-xxs font-semibold text-error bg-error/10 px-1.5 py-0.5 rounded-full">
            Due
          </span>
        )}

        {/* Retention bar */}
        <div className="w-16 h-1 bg-surface-active rounded-full overflow-hidden shrink-0">
          <div
            className="h-full rounded-full transition-all bg-accent/85"
            style={{ width: `${pct}%` }}
          />
        </div>

        <span className={`text-xs font-semibold w-9 text-right shrink-0 ${cls}`}>{pct}%</span>

        {lastSeen && (
          <span className="text-xxs text-text-tertiary w-14 text-right shrink-0 hidden sm:block">
            {lastSeen}
          </span>
        )}

        <ChevronDown
          size={12}
          className={`text-text-tertiary shrink-0 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Accordion panel */}
      <div
        className={`grid transition-all duration-300 ease-in-out ${
          isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        }`}
      >
        <div className="overflow-hidden">
          <div className="px-5 pb-4 pt-2 flex flex-col gap-4">
            {/* KPIs */}
            <div className="flex items-center gap-6">
              <div>
                <p className="text-xxs text-text-tertiary mb-0.5">Strength</p>
                <StrengthDots strength={topic.strength} />
              </div>
              <div>
                <p className="text-xxs text-text-tertiary mb-0.5">Reviews</p>
                <p className="text-xs font-medium text-text">{topic.repetitions}</p>
              </div>
              {nextReview && (
                <div>
                  <p className="text-xxs text-text-tertiary mb-0.5">Next review</p>
                  <p className={`text-xs font-medium ${isDue ? 'text-error' : 'text-text'}`}>{nextReview}</p>
                </div>
              )}
              {lastSeen && (
                <div>
                  <p className="text-xxs text-text-tertiary mb-0.5">Last recall</p>
                  <p className="text-xs font-medium text-text">{lastSeen}</p>
                </div>
              )}
            </div>

            {/* History */}
            <div>
              <p className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide mb-2">History</p>
              {isLoadingHistory ? (
                <div className="flex items-center gap-1.5">
                  <RefreshCw size={10} className="text-text-tertiary animate-spin" />
                  <span className="text-xxs text-text-tertiary">Loading…</span>
                </div>
              ) : (
                <EventTimeline events={events ?? []} color={color} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TrackingView() {
  const {
    topics,
    isLoading,
    isRecomputing,
    error,
    showDueOnly,
    topicHistories,
    loadingHistories,
    loadTopics,
    toggleDueOnly,
    recompute,
    loadTopicHistory,
  } = useTrackingStore()

  useEffect(() => {
    loadTopics()
  }, [])

  // Sort: due first, then by retention ascending
  const sorted = [...topics].sort((a, b) => {
    const aDue = a.next_review_at && new Date(a.next_review_at) <= new Date() ? 0 : 1
    const bDue = b.next_review_at && new Date(b.next_review_at) <= new Date() ? 0 : 1
    if (aDue !== bDue) return aDue - bDue
    return a.forgetting_score - b.forgetting_score
  })

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
      ) : sorted.length === 0 ? (
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
        <div className="flex-1 overflow-y-auto thin-scrollbar">
          {sorted.map((topic) => {
            // Use original index for stable color
            const colorIdx = topics.findIndex((t) => t.topic_id === topic.topic_id)
            return (
              <TopicRow
                key={topic.topic_id}
                topic={topic}
                color={TOPIC_COLORS[colorIdx % TOPIC_COLORS.length]}
                events={topicHistories[topic.topic_id]}
                isLoadingHistory={loadingHistories.has(topic.topic_id)}
                onOpen={() => loadTopicHistory(topic.topic_id)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
