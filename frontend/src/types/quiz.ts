export interface QuizQuestion {
  id: number
  question: string
  options: string[]
  answer: string
  difficulty?: string
}

export interface GenerateQuizResponse {
  quiz_set_id: number
  title: string
  questions: QuizQuestion[]
  created_at: string
}

export interface QuizAnswerItem {
  question_id: number
  answer: string
}

export interface QuizItemOutcome {
  question_id: number
  is_correct: boolean
  correct_answer: string
}

export interface SubmitQuizResponse {
  attempt_id: number
  score: number
  total_items: number
  results: QuizItemOutcome[]
  next_review_at?: string
  interval_days?: number
}
