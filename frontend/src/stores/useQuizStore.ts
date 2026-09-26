import { create } from 'zustand';
import { extensionBridge } from '../services/extensionBridge';
import { useTrackingStore } from './useTrackingStore';
import type { GenerateQuizResponse, SubmitQuizResponse } from '../types/quiz';

type QuizPhase = 'select' | 'generating' | 'answering' | 'submitting' | 'results' | 'error';

interface QuizStore {
  phase: QuizPhase;
  topicId: number | null;
  topicName: string | null;
  questionCount: number;
  quiz: GenerateQuizResponse | null;
  currentIndex: number;
  answers: Record<number, string>;
  result: SubmitQuizResponse | null;
  error: string | null;

  setQuestionCount: (count: number) => void;
  startQuiz: (topicId: number, topicName: string) => Promise<void>;
  selectAnswer: (answer: string) => void;
  next: () => Promise<void>;
  reset: () => void;
}

export const useQuizStore = create<QuizStore>((set, get) => ({
  phase: 'select',
  topicId: null,
  topicName: null,
  questionCount: 5,
  quiz: null,
  currentIndex: 0,
  answers: {},
  result: null,
  error: null,

  setQuestionCount: (count: number) => set({ questionCount: count }),

  startQuiz: async (topicId: number, topicName: string) => {
    set({
      phase: 'generating',
      topicId,
      topicName,
      quiz: null,
      currentIndex: 0,
      answers: {},
      result: null,
      error: null,
    });
    try {
      const quiz = await extensionBridge.generateQuiz(topicId, get().questionCount);
      // Ignore a late response if the user already left or started another quiz
      if (get().topicId !== topicId || get().phase !== 'generating') return;
      if (quiz.questions.length === 0) throw new Error('No questions were generated');
      set({ quiz, phase: 'answering' });
    } catch (error) {
      if (get().topicId !== topicId) return;
      set({ phase: 'error', error: error instanceof Error ? error.message : 'Unknown error' });
    }
  },

  // An answer is final once picked: the correction is shown right away
  selectAnswer: (answer: string) => {
    const { quiz, currentIndex, answers } = get();
    const question = quiz?.questions[currentIndex];
    if (!question || answers[question.id] !== undefined) return;
    set({ answers: { ...answers, [question.id]: answer } });
  },

  next: async () => {
    const { quiz, currentIndex, answers } = get();
    if (!quiz) return;
    if (currentIndex < quiz.questions.length - 1) {
      set({ currentIndex: currentIndex + 1 });
      return;
    }
    try {
      set({ phase: 'submitting' });
      const result = await extensionBridge.submitQuiz(
        quiz.quiz_set_id,
        Object.entries(answers).map(([questionId, answer]) => ({ question_id: Number(questionId), answer })),
      );
      set({ result, phase: 'results' });
      // The quiz updated the topic's memory: refresh the tracking dashboard
      useTrackingStore.getState().loadTopics();
    } catch (error) {
      set({ phase: 'error', error: error instanceof Error ? error.message : 'Unknown error' });
    }
  },

  reset: () =>
    set({
      phase: 'select',
      topicId: null,
      topicName: null,
      quiz: null,
      currentIndex: 0,
      answers: {},
      result: null,
      error: null,
    }),
}));
