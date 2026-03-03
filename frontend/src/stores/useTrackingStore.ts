import { create } from 'zustand';
import { extensionBridge } from '../services/extensionBridge';
import type { TopicTrackingItem } from '../types/tracking';

interface TrackingStore {
  topics: TopicTrackingItem[];
  isLoading: boolean;
  isRecomputing: boolean;
  error: string | null;
  showDueOnly: boolean;

  loadTopics: () => Promise<void>;
  toggleDueOnly: () => Promise<void>;
  recompute: () => Promise<void>;
}

export const useTrackingStore = create<TrackingStore>((set, get) => ({
  topics: [],
  isLoading: false,
  isRecomputing: false,
  error: null,
  showDueOnly: false,

  loadTopics: async () => {
    try {
      set({ isLoading: true, error: null });
      await extensionBridge.waitForExtensionServices();
      const response = await extensionBridge.getTrackedTopics(get().showDueOnly);
      set({ topics: response.topics ?? [], isLoading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', isLoading: false });
    }
  },

  toggleDueOnly: async () => {
    set((state) => ({ showDueOnly: !state.showDueOnly }));
    await get().loadTopics();
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
}));
