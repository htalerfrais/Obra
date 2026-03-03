class ApiService {
    constructor(config, authService) {
        this.config = config;
        this.authService = authService;
    }
    
    async makeRequest(endpoint, options = {}) {
        const query = options.query || null;
        const urlBase = this.config.getEndpointUrl(endpoint);
        const url = query ? `${urlBase}?${new URLSearchParams(query).toString()}` : urlBase;
        const headers = this.config.getRequestHeaders();
        
        const requestOptions = {
            method: options.method || 'GET',
            headers: { ...headers, ...options.headers },
            ...options
        };
        
        let lastError;
        
        for (let attempt = 1; attempt <= this.config.REQUEST_CONFIG.retries; attempt++) {
            try {
                console.log(`API Request (attempt ${attempt}): ${requestOptions.method} ${url}`);
                
                const response = await fetch(url, requestOptions);
                
                if (!response.ok) {
                    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData.detail) {
                            errorMessage += ` - ${JSON.stringify(errorData.detail)}`;
                        } else if (errorData.message) {
                            errorMessage += ` - ${errorData.message}`;
                        } else {
                            errorMessage += ` - ${JSON.stringify(errorData)}`;
                        }
                    } catch (e) {}

                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                console.log(`API Response: Success`);
                return { success: true, data };
                
            } catch (error) {
                lastError = error;
                console.warn(`API Request failed (attempt ${attempt}):`, error.message);
                
                if (attempt < this.config.REQUEST_CONFIG.retries) {
                    const delayMs = this.config.REQUEST_CONFIG.retryDelay * attempt;
                    await this.delay(delayMs);
                }
            }
        }
        
        console.error('API Request failed after all retries:', lastError.message);
        return { success: false, error: lastError.message };
    }
    





    /**
     * Utility method for delays
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    







    /**
     * Check API health
     * @returns {Promise<{success: boolean, data?: any, error?: string}>}
     */
    async checkHealth() {
        return await this.makeRequest('health');
    }
    
    async authenticate(token) {
        return await this.makeRequest('authenticate', {
            method: 'POST',
            body: JSON.stringify({ token })
        });
    }
    
    /**
     * Send single session for clustering
     * @param {Object} session - Session object (formatted for API)
     * @param {Object} opts - Options (force: boolean)
     * @returns {Promise<{success: boolean, data?: any, error?: string}>}
     */
    async analyzeSession(session, opts = {}) {
        if (!session || !session.items || session.items.length === 0) {
            return { success: false, error: 'No valid session provided' };
        }
        
        // Validate session structure
        if (!session.session_identifier) {
            return { success: false, error: 'Session missing session_identifier' };
        }
        if (!session.start_time || !session.end_time) {
            return { success: false, error: 'Session missing start_time or end_time' };
        }
        
        const invalidItems = session.items.filter(item => !item.url || !item.title || !item.visit_time);
        if (invalidItems.length > 0) {
            console.warn(`Session has ${invalidItems.length} invalid items:`, invalidItems);
            // Filter out invalid items
            session.items = session.items.filter(item => item.url && item.title && item.visit_time);
            if (session.items.length === 0) {
                return { success: false, error: 'Session has no valid items after filtering' };
            }
        }
        

        // add the user token to the session objec to match the backend model
        
        // Get user token from auth service
        const userToken = await this.authService.getToken();
        if (!userToken) {
            return { success: false, error: 'User not authenticated' };
        }
        
        const sessionWithUser = {
            ...session,
            user_token: userToken
        };
        
        // Log first item for debugging
        if (session.items.length > 0) {
            console.log('First item sample:', {
                url: session.items[0].url,
                title: session.items[0].title,
                visit_time: session.items[0].visit_time,
                url_hostname: session.items[0].url_hostname
            });
        }
        
        console.log(`Sending session ${session.session_identifier} with ${session.items.length} items for clustering`);
        console.log('Session payload preview:', JSON.stringify({
            session_identifier: sessionWithUser.session_identifier,
            start_time: sessionWithUser.start_time,
            end_time: sessionWithUser.end_time,
            items_count: sessionWithUser.items.length,
            first_item: sessionWithUser.items[0],
            has_user_token: !!sessionWithUser.user_token
        }, null, 2));
        
        const result = await this.makeRequest('cluster-session', {
            method: 'POST',
            body: JSON.stringify(sessionWithUser),
            query: opts.force ? { force: 'true' } : undefined
        });
        
        if (result.success) {
            console.log(`Received clustering result for session ${session.session_identifier} with ${result.data.clusters?.length || 0} clusters`);
        } else {
            console.error(`Failed to cluster session ${session.session_identifier}:`, result.error);
        }
        
        return result;
    }
    



    async getTrackedTopics(userToken, dueOnly = false) {
        return this.makeRequest('tracking-topics', {
            query: { user_token: userToken, due_only: dueOnly }
        });
    }

    async recomputeTracking(userToken) {
        return this.makeRequest('tracking-recompute', {
            method: 'POST',
            body: JSON.stringify({}),
            query: { user_token: userToken }
        });
    }

    /**
     * Send chat message
     * @param {string} message - User message
     * @param {string|null} conversationId - Optional conversation ID
     * @param {Array} history - Optional conversation history
     * @returns {Promise<{success: boolean, data?: any, error?: string}>}
     */
    async sendChatMessage(message, conversationId = null, history = []) {
        if (!message || message.trim().length === 0) {
            return { success: false, error: 'Message cannot be empty' };
        }
        
        // same here we want to get user token to match the backend model
        // Get user token from auth service
        const userToken = await this.authService.getToken();
        
        console.log(`Sending chat message${conversationId ? ` for conversation ${conversationId}` : ''}`);
        
        const payload = {
            message: message,
            conversation_id: conversationId,
            history: history,
            provider: "google",
            user_token: userToken || null
        };
        
        const result = await this.makeRequest('chat', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (result.success) {
            console.log(`Received chat response for conversation ${result.data.conversation_id}`);
        }
        
        return result;
    }
}
