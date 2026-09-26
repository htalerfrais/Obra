import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BrainCircuit, RefreshCw, Check, X, ArrowRight, RotateCcw, TrendingDown, Play } from 'lucide-react'
import { useQuizStore } from '../../stores/useQuizStore'
import { useTrackingStore } from '../../stores/useTrackingStore'
import { isDue, retentionPct } from '../tracking/retention'
import type { TopicTrackingItem } from '../../types/tracking'

const QUESTION_COUNTS = [5, 10]

function Header({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-line shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <BrainCircuit size={16} className="text-accent shrink-0" />
        <h1 className="text-sm font-semibold text-text truncate">{title}</h1>
      </div>
      {right}
    </div>
  )
}

function CenteredMessage({ icon, title, children }: { icon: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4 text-center px-6">
      {icon}
      <div className="space-y-1">
        <p className="text-sm font-medium text-text">{title}</p>
        {children}
      </div>
    </div>
  )
}

/* ---------- 1. Topic selection ---------- */

function TopicPicker() {
  const { topics, isLoading, error, loadTopics } = useTrackingStore()
  const { questionCount, setQuestionCount, startQuiz } = useQuizStore()

  useEffect(() => {
    if (topics.length === 0) loadTopics()
  }, [])

  // Due topics first, then the most forgotten ones
  const sorted = [...topics].sort((a, b) => {
    const dueDiff = Number(isDue(b)) - Number(isDue(a))
    return dueDiff !== 0 ? dueDiff : b.forgetting_score - a.forgetting_score
  })

  const countPicker = (
    <div className="flex items-center gap-1 bg-surface rounded-lg p-0.5">
      {QUESTION_COUNTS.map((n) => (
        <button
          key={n}
          onClick={() => setQuestionCount(n)}
          className={`text-xxs font-medium px-2.5 py-1 rounded-md transition-colors ${
            questionCount === n ? 'bg-accent text-white' : 'text-text-secondary hover:text-text'
          }`}
        >
          {n} questions
        </button>
      ))}
    </div>
  )

  return (
    <div className="flex flex-col h-full">
      <Header title="Quiz" right={countPicker} />
      {isLoading && topics.length === 0 ? (
        <CenteredMessage icon={<RefreshCw size={20} className="text-accent animate-spin" />} title="Loading topics…" />
      ) : error ? (
        <CenteredMessage icon={<TrendingDown size={32} strokeWidth={1.2} className="text-error" />} title={error}>
          <button onClick={loadTopics} className="text-xs text-accent hover:text-accent-hover transition-colors">
            Retry
          </button>
        </CenteredMessage>
      ) : sorted.length === 0 ? (
        <CenteredMessage
          icon={
            <div className="p-5 rounded-2xl bg-accent-subtle">
              <BrainCircuit size={36} strokeWidth={1.2} className="text-accent" />
            </div>
          }
          title="No topics to quiz yet"
        >
          <p className="text-xs text-text-tertiary max-w-xs leading-relaxed">
            Analyze a browsing session: learning topics will show up here.
          </p>
        </CenteredMessage>
      ) : (
        <div className="flex-1 overflow-y-auto thin-scrollbar">
          <p className="px-5 pt-5 pb-2 text-xs text-text-tertiary leading-relaxed">
            Pick a topic to test yourself. Your score updates its memory curve: a good score pushes the next review further away.
          </p>
          <div className="border-t border-line">
            {sorted.map((topic) => (
              <TopicPickRow key={topic.topic_id} topic={topic} onStart={() => startQuiz(topic.topic_id, topic.name)} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TopicPickRow({ topic, onStart }: { topic: TopicTrackingItem; onStart: () => void }) {
  const due = isDue(topic)
  return (
    <button
      onClick={onStart}
      className="group w-full px-5 py-3 flex items-center gap-3 border-b border-line hover:bg-surface-hover transition-colors text-left"
    >
      <span className="flex-1 text-sm font-medium text-text truncate min-w-0" title={topic.name}>
        {topic.name}
      </span>
      {due && (
        <span className="shrink-0 text-xxs font-semibold text-error/75 bg-error/8 px-1.5 py-0.5 rounded-full">Due</span>
      )}
      <span className="text-xs font-semibold w-9 text-right shrink-0 text-text-secondary">{retentionPct(topic)}%</span>
      <Play size={12} className="shrink-0 text-text-tertiary group-hover:text-accent transition-colors" />
    </button>
  )
}

/* ---------- 2. Answering ---------- */

function QuestionCard() {
  const { quiz, currentIndex, answers, topicName, phase, selectAnswer, next, reset } = useQuizStore()
  if (!quiz) return null

  const question = quiz.questions[currentIndex]
  const picked = answers[question.id]
  const hasAnswered = picked !== undefined
  const isLast = currentIndex === quiz.questions.length - 1
  const progress = ((currentIndex + (hasAnswered ? 1 : 0)) / quiz.questions.length) * 100

  function optionClass(option: string) {
    const base = 'w-full text-left px-4 py-3 rounded-xl border text-sm transition-colors flex items-center gap-3'
    if (!hasAnswered) return `${base} border-line bg-surface/40 text-text hover:bg-surface-hover hover:border-line-strong`
    if (option === question.answer) return `${base} border-success/50 bg-success/10 text-text`
    if (option === picked) return `${base} border-error/50 bg-error/10 text-text`
    return `${base} border-line bg-transparent text-text-tertiary`
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title={topicName ?? 'Quiz'}
        right={
          <button onClick={reset} className="text-xxs font-medium px-3 py-1.5 rounded-lg bg-surface text-text-secondary hover:bg-surface-hover transition-colors">
            Quit
          </button>
        }
      />
      <div className="h-0.5 bg-surface-active shrink-0">
        <div className="h-full bg-accent transition-all duration-300" style={{ width: `${progress}%` }} />
      </div>

      <div className="flex-1 overflow-y-auto thin-scrollbar px-5 py-6">
        <div className="max-w-xl mx-auto flex flex-col gap-5">
          <div className="flex items-center gap-2">
            <span className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide">
              Question {currentIndex + 1} / {quiz.questions.length}
            </span>
            {question.difficulty && (
              <span className="text-xxs text-text-tertiary bg-surface px-1.5 py-0.5 rounded-full capitalize">{question.difficulty}</span>
            )}
          </div>

          <p className="text-base font-medium text-text leading-relaxed">{question.question}</p>

          <div className="flex flex-col gap-2">
            {question.options.map((option) => (
              <button key={option} onClick={() => selectAnswer(option)} disabled={hasAnswered} className={optionClass(option)}>
                <span className="flex-1">{option}</span>
                {hasAnswered && option === question.answer && <Check size={14} className="text-success shrink-0" />}
                {hasAnswered && option === picked && option !== question.answer && <X size={14} className="text-error shrink-0" />}
              </button>
            ))}
          </div>

          {hasAnswered && (
            <div className="flex items-center justify-between gap-3">
              <p className={`text-xs font-medium ${picked === question.answer ? 'text-success' : 'text-error/80'}`}>
                {picked === question.answer ? 'Correct!' : 'Not quite: the right answer is highlighted.'}
              </p>
              <button
                onClick={next}
                disabled={phase === 'submitting'}
                className="flex items-center gap-1.5 text-xs font-medium px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 shrink-0"
              >
                {phase === 'submitting' ? (
                  <RefreshCw size={12} className="animate-spin" />
                ) : isLast ? (
                  'See results'
                ) : (
                  <>
                    Next <ArrowRight size={12} />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------- 3. Results ---------- */

function Results() {
  const navigate = useNavigate()
  const { quiz, result, answers, topicId, topicName, startQuiz, reset } = useQuizStore()
  if (!quiz || !result) return null

  const correct = result.results.filter((r) => r.is_correct).length
  const pct = Math.round(result.score * 100)
  const passed = result.score >= 0.6
  const nextReview = result.next_review_at
    ? new Date(result.next_review_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
    : null
  const outcomeById = Object.fromEntries(result.results.map((r) => [r.question_id, r]))

  return (
    <div className="flex flex-col h-full">
      <Header title={topicName ?? 'Quiz'} />
      <div className="flex-1 overflow-y-auto thin-scrollbar px-5 py-6">
        <div className="max-w-xl mx-auto flex flex-col gap-6">
          {/* Score */}
          <div className="px-5 py-5 rounded-xl bg-bg-raised border border-line flex items-center gap-5">
            <div>
              <p className="text-5xl font-semibold text-text">{pct}%</p>
              <p className="text-xs text-text-tertiary mt-1">
                {correct} / {result.total_items} correct
              </p>
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${passed ? 'text-success' : 'text-error/80'}`}>
                {passed ? 'Memory strengthened' : 'Needs another pass'}
              </p>
              {result.interval_days != null && nextReview && (
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  {result.interval_days <= 1 ? 'Review again tomorrow' : `Next review in ${result.interval_days} days`} · {nextReview}
                </p>
              )}
            </div>
          </div>

          {/* Recap */}
          <div className="flex flex-col gap-2">
            <p className="text-xxs font-semibold text-text-tertiary uppercase tracking-wide">Recap</p>
            {quiz.questions.map((q, i) => {
              const outcome = outcomeById[q.id]
              const ok = outcome?.is_correct
              return (
                <div key={q.id} className="px-4 py-3 rounded-xl border border-line flex gap-3">
                  <span className={`mt-0.5 shrink-0 ${ok ? 'text-success' : 'text-error'}`}>
                    {ok ? <Check size={14} /> : <X size={14} />}
                  </span>
                  <div className="min-w-0 space-y-1">
                    <p className="text-xs text-text leading-relaxed">
                      {i + 1}. {q.question}
                    </p>
                    {!ok && (
                      <p className="text-xxs text-text-tertiary">
                        Your answer: <span className="text-text-secondary">{answers[q.id] ?? '—'}</span> · Correct:{' '}
                        <span className="text-text-secondary">{outcome?.correct_answer ?? q.answer}</span>
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {topicId != null && topicName && (
              <button
                onClick={() => startQuiz(topicId, topicName)}
                className="flex items-center gap-1.5 text-xs font-medium px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors"
              >
                <RotateCcw size={12} /> New quiz on this topic
              </button>
            )}
            <button onClick={reset} className="text-xs font-medium px-4 py-2 rounded-lg bg-surface text-text-secondary hover:bg-surface-hover transition-colors">
              Other topic
            </button>
            <button
              onClick={() => {
                reset()
                navigate('/tracking')
              }}
              className="text-xs font-medium px-4 py-2 rounded-lg text-text-secondary hover:text-text transition-colors"
            >
              See tracking
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------- Router ---------- */

export default function QuizView() {
  const { phase, topicName, error, reset } = useQuizStore()

  if (phase === 'generating') {
    return (
      <div className="flex flex-col h-full">
        <Header title={topicName ?? 'Quiz'} />
        <CenteredMessage icon={<RefreshCw size={20} className="text-accent animate-spin" />} title="Generating questions…">
          <p className="text-xs text-text-tertiary">This can take a few seconds.</p>
        </CenteredMessage>
      </div>
    )
  }
  if (phase === 'error') {
    return (
      <div className="flex flex-col h-full">
        <Header title={topicName ?? 'Quiz'} />
        <CenteredMessage icon={<TrendingDown size={32} strokeWidth={1.2} className="text-error" />} title="Something went wrong">
          <p className="text-xs text-text-tertiary max-w-sm break-words">{error}</p>
          <button onClick={reset} className="mt-2 text-xs text-accent hover:text-accent-hover transition-colors">
            Back to topics
          </button>
        </CenteredMessage>
      </div>
    )
  }
  if (phase === 'answering' || phase === 'submitting') return <QuestionCard />
  if (phase === 'results') return <Results />
  return <TopicPicker />
}
