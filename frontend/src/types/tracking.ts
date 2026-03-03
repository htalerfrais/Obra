export interface TopicTrackingItem {
  topic_id: number
  name: string
  description?: string
  forgetting_score: number
  strength: number
  repetitions: number
  next_review_at?: string
  last_reviewed_at?: string
}

export interface TopicTrackingResponse {
  topics: TopicTrackingItem[]
}

export interface RecallHistoryEvent {
  event_time: string
  event_type: string
  strength: number
  forgetting_score: number
  session_identifier?: string
}

export interface TopicHistoryResponse {
  topic_id: number
  events: RecallHistoryEvent[]
}
