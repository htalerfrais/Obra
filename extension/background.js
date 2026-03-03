// Import utilities and configs
importScripts('config/constants.js');
importScripts('config/api.config.js');
importScripts('utils/preprocess.js');
importScripts('utils/session.utils.js');

// Import services
importScripts('services/api.service.js');
importScripts('services/auth.service.js');
importScripts('services/history.service.js');
importScripts('services/session.service.js');

// Create service instances with temporary authService to resolve circular dependency
let authService;
let apiService;
let historyService;
let sessionService;
async function initialize() {
    try {
        console.log('Initializing extension services...');
        
        const tempAuthService = {
            getToken: async () => {
                const stored = await chrome.storage.local.get(['userToken']);
                return stored.userToken || null;
            }
        };
        
        apiService = new ApiService(config, tempAuthService);
        authService = new AuthService(apiService);
        apiService.authService = authService;
        
        historyService = new HistoryService();
        sessionService = new SessionService(historyService, apiService);
        
        console.log('Initializing auth service...');
        await authService.initialize();
        
        console.log('Initializing history service...');
        await historyService.initialize();
        
        console.log('Initializing session service...');
        await sessionService.initialize();
        
        console.log('All services initialized successfully');
        
        self.Services = {
            historyService,
            sessionService,
            apiService,
            authService
        };
        
    } catch (error) {
        console.error('Error initializing services:', error);
    }
}

chrome.history.onVisited.addListener(async (rawItem) => {
    try {
        if (!historyService || !sessionService) {
            console.log('Services not yet initialized, skipping history item');
            return;
        }
        
        const processedItem = await historyService.addItem(rawItem);
        
        if (processedItem) {
            await sessionService.onNewItem();
        }
    } catch (error) {
        console.error('Error handling new history item:', error);
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    (async () => {
        try {
            if (!self.Services) {
                for (let i = 0; i < 25; i++) {
                    await new Promise(resolve => setTimeout(resolve, 200));
                    if (self.Services) break;
                }
                if (!self.Services) {
                    console.error('[BACKGROUND] Services still not initialized after 5s');
                    sendResponse({ error: 'Services not initialized' });
                    return;
                }
            }
            
            const { historyService, sessionService, apiService } = self.Services;
            
            switch (request.action) {
                case 'ping':
                    sendResponse({ success: true });
                    break;
                    
                case 'getAllSessions':
                    const sessions = await sessionService.getAllSessions();
                    sendResponse({ sessions });
                    break;
                    
                case 'analyzeSession':
                    const result = await apiService.analyzeSession(request.session, request.options);
                    sendResponse(result);
                    break;
                    
                case 'sendChatMessage':
                    const chatResult = await apiService.sendChatMessage(
                        request.message,
                        request.conversationId,
                        request.history
                    );
                    sendResponse(chatResult);
                    break;
                    
                case 'checkApiHealth':
                    const healthResult = await apiService.checkHealth();
                    sendResponse(healthResult);
                    break;

                case 'getTrackedTopics': {
                    const token = await self.Services.authService.getToken();
                    const topicsResult = await apiService.getTrackedTopics(token, request.dueOnly);
                    sendResponse(topicsResult);
                    break;
                }

                case 'recomputeTracking': {
                    const token = await self.Services.authService.getToken();
                    const recomputeResult = await apiService.recomputeTracking(token);
                    sendResponse(recomputeResult);
                    break;
                }
                    
                default:
                    sendResponse({ error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({ error: error.message });
        }
    })();
    
    return true;
});

initialize();
