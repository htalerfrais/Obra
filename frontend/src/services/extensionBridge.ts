/// <reference types="chrome"/>

import type { TopicTrackingResponse } from '../types/tracking';

declare global {
  interface Window {
    ExtensionConstants: any;
    ExtensionConfig: any;
  }
}

class ExtensionBridge {
  private isReady: boolean = false;
  private readyPromise: Promise<void> | null = null;

  async waitForReady(timeout: number = 10000): Promise<void> {
    if (this.isReady) {
      return;
    }

    if (this.readyPromise) {
      return this.readyPromise;
    }

    this.readyPromise = new Promise((resolve, reject) => {
      const startTime = Date.now();
      const retryDelay = 200; // Wait 200ms between retries

      const checkReady = () => {
        const elapsed = Date.now() - startTime;
        
        // Check timeout before attempting ping
        if (elapsed > timeout) {
          reject(new Error('Timeout waiting for extension services'));
          return;
        }

        if (typeof chrome !== 'undefined' && chrome.runtime) {
          chrome.runtime.sendMessage({ action: 'ping' }, (pingResponse) => {
            if (chrome.runtime.lastError) {
              if (Date.now() - startTime > timeout) {
                reject(new Error(`Chrome runtime error: ${chrome.runtime.lastError.message}`));
                return;
              }
              setTimeout(checkReady, retryDelay);
              return;
            }

            // Check if service worker responded successfully
            if (pingResponse?.success) {
              this.isReady = true;
              resolve();
              return;
            }

            if (Date.now() - startTime > timeout) {
              reject(new Error('Service worker responded but services not ready'));
              return;
            }
            
            setTimeout(checkReady, retryDelay);
          });
        } else {
          // Chrome runtime not available
          reject(new Error('Chrome runtime not available'));
        }
      };

      checkReady();
    });

    return this.readyPromise;
  }

  private sendMessage<T>(message: any): Promise<T> {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response);
        }
      });
    });
  }

  /**
   * Get all sessions (completed + current)
   * Returns completedSessions[] + currentSession (if exists)
   */
  async getAllSessions(): Promise<any[]> {
    try {
      await this.waitForReady();
      const response = await this.sendMessage<{ sessions: any[] }>({ action: 'getAllSessions' });
      console.log(`Retrieved ${response.sessions.length} sessions from service worker`);
      return response.sessions || [];
    } catch (error) {
      console.error('Error getting all sessions:', error);
      throw error;
    }
  }

  async getProcessedHistory(): Promise<any[]> {
    return new Promise((resolve, reject) => {
      if (!chrome?.storage?.local) {
        reject(new Error('Chrome storage not available'));
        return;
      }

      chrome.storage.local.get({ historyItems: [] }, (data: any) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          console.log(`Retrieved ${data.historyItems.length} preprocessed items from storage`);
          resolve(data.historyItems);
        }
      });
    });
  }

  /**
   * Process history items into sessions
   * Kept for backward compatibility (fallback)
   */
  async processHistoryIntoSessions(_historyItems: any[]): Promise<any[]> {
    // Fallback: use getAllSessions instead
    return await this.getAllSessions();
  }

  async clusterSession(session: any, options?: { force?: boolean }): Promise<any> {
    try {
      await this.waitForReady();
      const result = await this.sendMessage({ 
        action: 'analyzeSession', 
        session, 
        options 
      });
      console.log('Session clustering result:', result);
      return result;
    } catch (error) {
      console.error('Error clustering session:', error);
      throw error;
    }
  }

  /**
   * Check API health
   */
  async checkApiHealth(): Promise<any> {
    try {
      await this.waitForReady();
      const result = await this.sendMessage({ action: 'checkApiHealth' });
      console.log('API health check:', result);
      return result;
    } catch (error) {
      console.error('Error checking API health:', error);
      throw error;
    }
  }

  async sendChatMessage(message: string, conversationId?: string, history?: any[]): Promise<any> {
    if (!message || message.trim().length === 0) {
      throw new Error('Message cannot be empty');
    }

    try {
      await this.waitForReady();
      const result = await this.sendMessage({
        action: 'sendChatMessage',
        message,
        conversationId: conversationId || null,
        history: history || []
      });
      console.log('Chat message result:', result);
      return result;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  }

  async getTrackedTopics(dueOnly = false): Promise<TopicTrackingResponse> {
    try {
      await this.waitForReady();
      const result = await this.sendMessage<{ success: boolean; data?: TopicTrackingResponse; error?: string }>({
        action: 'getTrackedTopics',
        dueOnly,
      });
      if (!result.success) throw new Error((result as any).error || 'Failed to get tracked topics');
      return result.data as TopicTrackingResponse;
    } catch (error) {
      console.error('Error getting tracked topics:', error);
      throw error;
    }
  }

  async recomputeTracking(): Promise<{ success: boolean; data?: { updated: number } }> {
    try {
      await this.waitForReady();
      return await this.sendMessage<{ success: boolean; data?: { updated: number } }>({
        action: 'recomputeTracking',
      });
    } catch (error) {
      console.error('Error recomputing tracking:', error);
      throw error;
    }
  }

  /**
   * Get extension configuration
   */
  getConfig() {
    if (!window.ExtensionConfig) {
      console.warn('ExtensionConfig not available, using defaults');
      return {
        currentEnvironment: 'development',
        getApiBaseUrl: () => 'http://localhost:8000'
      };
    }
    return window.ExtensionConfig;
  }

  getConstants() {
    if (!window.ExtensionConstants) {
      console.warn('ExtensionConstants not available, using defaults');
      return {
        SESSION_GAP_MINUTES: 120,
        HISTORY_DAYS_BACK: 7,
        DAY_MS: 24 * 60 * 60 * 1000,
        MAX_CLUSTER_ITEMS_DISPLAY: 5,
        STATUS_CHECKING_API: 'Checking API connection...',
        STATUS_FETCHING_HISTORY: 'Fetching history...',
        STATUS_PROCESSING_SESSIONS: 'Processing sessions...',
        STATUS_ANALYZING_PATTERNS: 'Analyzing patterns...',
        STATUS_ANALYSIS_COMPLETE: 'Analysis complete',
        STATUS_ANALYSIS_FAILED: 'Analysis failed',
        ERROR_NO_HISTORY: 'No history found',
        ERROR_NO_SESSIONS: 'No sessions could be created',
        ERROR_CLUSTERING_FAILED: 'Clustering failed'
      };
    }
    return window.ExtensionConstants;
  }

  areExtensionServicesReady(): boolean {
    return !!(
      chrome?.runtime &&
      window.ExtensionConstants && 
      window.ExtensionConfig &&
      chrome?.storage?.local
    );
  }

  /**
   * Wait for extension services to be ready
   * @param timeoutMs - Timeout in milliseconds (default: 10 seconds)
   */
  async waitForExtensionServices(timeoutMs: number = 10000): Promise<void> {
    return this.waitForReady(timeoutMs);
  }
}

export const extensionBridge = new ExtensionBridge();

if (typeof window !== 'undefined') {
  (window as any).extensionBridge = extensionBridge;
}
