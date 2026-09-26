import { create } from 'zustand';
import { extensionBridge } from '../services/extensionBridge';
import type { TopicTrackingItem, RecallHistoryEvent } from '../types/tracking';

interface TrackingStore {
  topics: TopicTrackingItem[];
  isLoading: boolean;
  isRecomputing: boolean;
  error: string | null;
  topicHistories: Record<number, RecallHistoryEvent[]>;
  loadingHistories: Set<number>;

  loadTopics: () => Promise<void>;
  recompute: () => Promise<void>;
  loadTopicHistory: (topicId: number) => Promise<void>;
}

export const useTrackingStore = create<TrackingStore>((set, get) => ({
  topics: [],
  isLoading: false,
  isRecomputing: false,
  error: null,
  topicHistories: {},
  loadingHistories: new Set(),

  loadTopics: async () => {
    try {
      set({ isLoading: true, error: null });
      await extensionBridge.waitForExtensionServices();
      const response = await extensionBridge.getTrackedTopics();
      set({ topics: response.topics ?? [], isLoading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', isLoading: false });
    }
  },

  recompute: async () => {
    try {
      set({ isRecomputing: true, error: null });
      await extensionBridge.recomputeTracking();
      await get().loadTopics();
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      set({ isRecomputing: false });
    }
  },

  loadTopicHistory: async (topicId: number) => {
    if (get().loadingHistories.has(topicId)) return;
    set((state) => ({ loadingHistories: new Set([...state.loadingHistories, topicId]) }));
    try {
      const response = await extensionBridge.getTopicHistory(topicId);
      set((state) => ({
        topicHistories: { ...state.topicHistories, [topicId]: response.events },
        loadingHistories: new Set([...state.loadingHistories].filter((id) => id !== topicId)),
      }));
    } catch {
      set((state) => ({
        loadingHistories: new Set([...state.loadingHistories].filter((id) => id !== topicId)),
      }));
    }
  },
}));
