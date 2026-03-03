class Config {
    constructor() {
        this.API_ENDPOINTS = {
            development: {
                baseUrl: 'http://localhost:8000',
                'cluster-session': '/cluster-session',
                'chat': '/chat',
                'authenticate': '/authenticate',
                'health': '/health',
                'tracking-topics': '/tracking/topics',
                'tracking-recompute': '/tracking/recompute'
            },
            production: {
                baseUrl: 'https://your-production-api.com',
                'cluster-session': '/cluster-session',
                'chat': '/chat',
                'authenticate': '/authenticate',
                'health': '/health',
                'tracking-topics': '/tracking/topics',
                'tracking-recompute': '/tracking/recompute'
            }
        };
        
        this.currentEnvironment = 'development';
        
        const constants = (typeof window !== 'undefined' ? window.ExtensionConstants : 
                          typeof self !== 'undefined' ? self.ExtensionConstants : {});
        
        this.REQUEST_CONFIG = {
            timeout: constants.API_REQUEST_TIMEOUT_MS || 30000,
            retries: constants.API_RETRIES || 3,
            retryDelay: constants.API_RETRY_DELAY_MS || 1000
        };
        
        this.CLUSTERING_CONFIG = {
            maxClusters: constants.MAX_CLUSTERS_DEFAULT || 10,
            minClusterSize: constants.MIN_CLUSTER_SIZE_DEFAULT || 2,
            confidenceThreshold: 0.5
        };
    }
    
    // Get current API base URL
    getApiBaseUrl() {
        return this.API_ENDPOINTS[this.currentEnvironment].baseUrl;
    }
    
    getEndpointUrl(endpoint) {
        const baseUrl = this.getApiBaseUrl();
        const path = this.API_ENDPOINTS[this.currentEnvironment][endpoint];
        return `${baseUrl}${path}`;
    }
    
    // Switch environment
    setEnvironment(env) {
        if (this.API_ENDPOINTS[env]) {
            this.currentEnvironment = env;
            console.log(`Switched to ${env} environment`);
        } else {
            console.warn(`Unknown environment: ${env}`);
        }
    }
    
    async checkApiHealth() {
        try {
            const response = await fetch(this.getEndpointUrl('health'), {
                method: 'GET',
                timeout: constants.API_TIMEOUT_MS || 5000
            });
            
            if (response.ok) {
                const data = await response.json();
                return { available: true, data };
            } else {
                return { available: false, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            return { available: false, error: error.message };
        }
    }
    
    // Get request headers
    getRequestHeaders() {
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }
}

const config = new Config();

if (typeof chrome !== 'undefined' && chrome.runtime) {
    config.checkApiHealth().then(result => {
        if (!result.available) {
            console.warn('Development API not available, consider switching to production');
            // Uncomment the next line to auto-switch to production
            // config.setEnvironment('production');
        } else {
            console.log('Development API is available');
        }
    });
}

if (typeof window !== 'undefined') {
    window.ExtensionConfig = config;
}

// For service workers (background scripts)
if (typeof self !== 'undefined') {
    self.ExtensionConfig = config;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}
