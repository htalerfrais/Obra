import { useEffect } from 'react';
import { RefreshCw, TrendingDown, Brain } from 'lucide-react';
import { useTrackingStore } from '../../stores/useTrackingStore';
import type { TopicTrackingItem } from '../../types/tracking';

function TopicCard({ topic }: { topic: TopicTrackingItem }) {
  const now = new Date();
  const isDue = topic.next_review_at ? new Date(topic.next_review_at) <= now : false;
  const score = Math.round(topic.forgetting_score * 100);

  const scoreColor =
    score < 30 ? 'bg-success' : score < 60 ? 'bg-yellow-400' : 'bg-error';

  const formattedNextReview = topic.next_review_at
    ? new Date(topic.next_review_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null;

  return (
    <div className="p-4 rounded-xl bg-surface border border-line hover:border-line-strong transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-text truncate">{topic.name}</span>
            {isDue && (
              <span className="shrink-0 text-xxs font-semibold text-error bg-error/10 px-2 py-0.5 rounded-full">
                Due
              </span>
            )}
          </div>
          {topic.description && (
            <p className="text-xs text-text-tertiary line-clamp-2">{topic.description}</p>
          )}
        </div>
        <div className="shrink-0 text-right">
          <span className="text-lg font-bold text-text">{score}%</span>
          <p className="text-xxs text-text-tertiary">forgotten</p>
        </div>
      </div>

      {/* Forgetting score bar */}
      <div className="h-1.5 rounded-full bg-surface-active overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all ${scoreColor}`}
          style={{ width: `${score}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xxs text-text-tertiary">
        <span>{topic.repetitions} review{topic.repetitions !== 1 ? 's' : ''}</span>
        {formattedNextReview && (
          <span className={isDue ? 'text-error font-medium' : ''}>
            Next: {formattedNextReview}
          </span>
        )}
      </div>
    </div>
  );
}

export default function TrackingView() {
  const { topics, isLoading, isRecomputing, error, showDueOnly, loadTopics, toggleDueOnly, recompute } =
    useTrackingStore();

  useEffect(() => {
    loadTopics();
  }, []);

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
      <div className="flex-1 overflow-y-auto thin-scrollbar px-5 py-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <RefreshCw size={20} className="text-accent animate-spin" />
            <p className="text-sm text-text-tertiary">Loading topics…</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <TrendingDown size={32} strokeWidth={1.2} className="text-error" />
            <p className="text-sm text-error">{error}</p>
            <button
              onClick={loadTopics}
              className="text-xs text-accent hover:text-accent-hover transition-colors"
            >
              Retry
            </button>
          </div>
        ) : topics.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
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
          <div className="space-y-2">
            {topics.map((topic) => (
              <TopicCard key={topic.topic_id} topic={topic} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
