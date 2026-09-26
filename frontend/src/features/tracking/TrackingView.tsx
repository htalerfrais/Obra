import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Brain, TrendingDown, ChevronDown, ExternalLink, CheckCircle2, BrainCircuit } from 'lucide-react'
import { useTrackingStore } from '../../stores/useTrackingStore'
import { useSessionStore } from '../../stores/useSessionStore'
import { useQuizStore } from '../../stores/useQuizStore'
import type { TopicTrackingItem, RecallHistoryEvent } from '../../types/tracking'
import ForgettingCurvesChart from './components/ForgettingCurvesChart'
import TopicRetentionCurve from './components/TopicRetentionCurve'
import { CHART, isDue, retentionPct } from './retention'

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

function EventTimeline({ events }: { events: RecallHistoryEvent[] }) {
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
            <span className="mt-0.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: CHART.accent }} />
            <div className="min-w-0 flex items-center gap-1.5 flex-wrap">
              <span className="text-xxs font-medium text-text capitalize">{e.event_type}</span>
              <span className="text-xxs text-text-tertiary">· {date}</span>
              <span className="text-xxs text-text-tertiary">
                · {e.event_type === 'quiz' && e.score != null ? `scored ${Math.round(e.score * 100)}%` : `${ret}% retained`}
              </span>
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
  isHighlighted,
  events,
  isLoadingHistory,
  onOpen,
  onHover,
}: {
  topic: TopicTrackingItem
  isHighlighted: boolean
  events: RecallHistoryEvent[] | undefined
  isLoadingHistory: boolean
  onOpen: () => void
  onHover: (topicId: number | null) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { pct, label, cls } = retentionLabel(topic.forgetting_score)
  const due = isDue(topic)
  const navigate = useNavigate()
  const startQuiz = useQuizStore((s) => s.startQuiz)
  const lastSeen = topic.last_reviewed_at ? daysAgo(topic.last_reviewed_at) : null
  const nextReview = topic.next_review_at
    ? new Date(topic.next_review_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null

  function handleToggle() {
    if (!isOpen && events === undefined) onOpen()
    setIsOpen((v) => !v)
  }

  return (
    <div
      className="border-b border-line last:border-b-0"
      onMouseEnter={() => onHover(topic.topic_id)}
      onMouseLeave={() => onHover(null)}
    >
      {/* Row header */}
      <button
        onClick={handleToggle}
        className="w-full px-5 py-3 flex items-center gap-3 hover:bg-surface-hover transition-colors text-left"
      >
        <span
          className="w-2 h-2 rounded-full shrink-0 transition-colors"
          style={{ backgroundColor: isHighlighted ? CHART.accent : CHART.context }}
        />

        <span className="flex-1 text-sm font-medium text-text truncate min-w-0" title={topic.name}>{topic.name}</span>

        {due && (
          <span className="shrink-0 text-xxs font-semibold text-error/75 bg-error/8 px-1.5 py-0.5 rounded-full">
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

        <span className="text-xs font-semibold w-9 text-right shrink-0 text-text-secondary">{pct}%</span>

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
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <div>
                <p className="text-xxs text-text-tertiary mb-0.5">Retention</p>
                <p className={`text-xs font-medium ${cls}`}>{label}</p>
              </div>
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
                  <p className={`text-xs font-medium ${due ? 'text-error/75' : 'text-text'}`}>{nextReview}</p>
                </div>
              )}
              {lastSeen && (
                <div>
                  <p className="text-xxs text-text-tertiary mb-0.5">Last recall</p>
                  <p className="text-xs font-medium text-text">{lastSeen}</p>
                </div>
              )}
              <button
                onClick={() => {
                  startQuiz(topic.topic_id, topic.name)
                  navigate('/quiz')
                }}
                className="ml-auto flex items-center gap-1.5 text-xxs font-medium px-3 py-1.5 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors shrink-0"
              >
                <BrainCircuit size={11} />
                Quiz me
              </button>
            </div>

            {/* Retention curve */}
            {events && events.length > 0 && (
              <div>
                <p className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Retention over time</p>
                <TopicRetentionCurve topic={topic} events={events} />
              </div>
            )}

            {/* History */}
            <div>
              <p className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide mb-2">History</p>
              {isLoadingHistory ? (
                <div className="flex items-center gap-1.5">
                  <RefreshCw size={10} className="text-text-tertiary animate-spin" />
                  <span className="text-xxs text-text-tertiary">Loading…</span>
                </div>
              ) : (
                <EventTimeline events={events ?? []} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatTile({ label, value, hint, hintCls = 'text-text-tertiary' }: {
  label: string
  value: string
  hint?: string
  hintCls?: string
}) {
  return (
    <div className="flex-1 min-w-[120px] px-4 py-3 rounded-xl bg-surface/60 border border-line">
      <p className="text-xxs text-text-tertiary">{label}</p>
      <p className="text-xl font-semibold text-text mt-0.5">{value}</p>
      {hint && <p className={`text-xxs mt-0.5 ${hintCls}`}>{hint}</p>}
    </div>
  )
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="px-5 pt-5 pb-2 flex items-center gap-2">
      <h2 className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide">{title}</h2>
      <span className="text-xxs text-text-tertiary">· {count}</span>
    </div>
  )
}

export default function TrackingView() {
  const {
    topics,
    isLoading,
    isRecomputing,
    error,
    topicHistories,
    loadingHistories,
    loadTopics,
    recompute,
    loadTopicHistory,
  } = useTrackingStore()
  const [highlightedId, setHighlightedId] = useState<number | null>(null)

  useEffect(() => {
    loadTopics()
  }, [])

  // Due: most forgotten first. Upcoming: soonest review first.
  const dueTopics = topics.filter((t) => isDue(t)).sort((a, b) => b.forgetting_score - a.forgetting_score)
  const upcomingTopics = topics
    .filter((t) => !isDue(t))
    .sort((a, b) => {
      const at = a.next_review_at ? new Date(a.next_review_at).getTime() : Infinity
      const bt = b.next_review_at ? new Date(b.next_review_at).getTime() : Infinity
      return at - bt
    })

  const avgRetention = topics.length
    ? Math.round(topics.reduce((sum, t) => sum + retentionPct(t), 0) / topics.length)
    : 0
  const criticalCount = topics.filter((t) => retentionPct(t) < 40).length

  const renderRow = (topic: TopicTrackingItem) => (
    <TopicRow
      key={topic.topic_id}
      topic={topic}
      isHighlighted={highlightedId === topic.topic_id}
      events={topicHistories[topic.topic_id]}
      isLoadingHistory={loadingHistories.has(topic.topic_id)}
      onOpen={() => loadTopicHistory(topic.topic_id)}
      onHover={setHighlightedId}
    />
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-line shrink-0">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-accent" />
          <h1 className="text-sm font-semibold text-text">Memory Tracking</h1>
        </div>
        <button
          onClick={recompute}
          disabled={isRecomputing}
          className="flex items-center gap-1.5 text-xxs font-medium px-3 py-1.5 rounded-lg bg-surface text-text-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          <RefreshCw size={11} className={isRecomputing ? 'animate-spin' : ''} />
          Recompute
        </button>
      </div>

      {/* Content */}
      {isLoading && topics.length === 0 ? (
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
            <p className="text-sm font-medium text-text">No topics tracked yet</p>
            <p className="text-xs text-text-tertiary max-w-xs leading-relaxed">
              Analyze a browsing session to start tracking learning topics.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto thin-scrollbar">
          {/* KPIs */}
          <div className="px-5 pt-5 flex flex-wrap gap-3">
            <StatTile label="Tracked topics" value={String(topics.length)} />
            <StatTile
              label="Due for review"
              value={String(dueTopics.length)}
              hint={dueTopics.length === 0 ? 'All caught up' : 'Review to strengthen memory'}
            />
            <StatTile label="Average retention" value={`${avgRetention}%`} />
            <StatTile
              label="Critical"
              value={String(criticalCount)}
              hint="Below 40% retention"
              hintCls={criticalCount > 0 ? 'text-error/75' : 'text-text-tertiary'}
            />
          </div>

          {/* Overview chart */}
          <div className="mx-5 mt-3 px-4 py-4 rounded-xl bg-bg-raised border border-line">
            <ForgettingCurvesChart topics={topics} highlightedId={highlightedId} onHighlight={setHighlightedId} />
          </div>

          {/* Due now */}
          <SectionHeader title="Due for review" count={dueTopics.length} />
          {dueTopics.length === 0 ? (
            <div className="px-5 pb-2 flex items-center gap-2 text-xs text-text-tertiary">
              <CheckCircle2 size={13} className="text-success" />
              Nothing to review right now. Come back later.
            </div>
          ) : (
            <div className="border-y border-line">{dueTopics.map(renderRow)}</div>
          )}

          {/* Upcoming */}
          {upcomingTopics.length > 0 && (
            <>
              <SectionHeader title="Upcoming reviews" count={upcomingTopics.length} />
              <div className="border-t border-line mb-5">{upcomingTopics.map(renderRow)}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
