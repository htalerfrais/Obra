export interface TopicTrackingItem {
  topic_id: number
  name: string
  description?: string
  forgetting_score: number
  strength: number
  repetitions: number
  next_review_at?: string
}

export interface TopicTrackingResponse {
  topics: TopicTrackingItem[]
}
