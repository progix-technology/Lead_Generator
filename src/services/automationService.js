import api from './api';

const automationService = {
    // Get Autopilot settings (enabled status, subject, body templates)
    getSettings: async () => {
        const response = await api.get('/automation/settings');
        return response.data;
    },

    // Save/Update Autopilot settings
    updateSettings: async (settingsData) => {
        const response = await api.post('/automation/settings', settingsData);
        return response.data;
    },

    // Fetch history of automatically sent cold emails
    getRecords: async (skip = 0, limit = 100) => {
        const response = await api.get(`/automation/records?skip=${skip}&limit=${limit}`);
        return response.data;
    },

    // Manually run a single Autopilot crawl/send cycle now
    triggerAutopilot: async () => {
        const response = await api.post('/automation/trigger');
        return response.data;
    },

    // Fetch real-time log messages for the currently running cycle
    getProgress: async () => {
        const response = await api.get('/automation/progress');
        return response.data;
    },
    
    // Fetch live metrics for the queue system (Pending vs Sent)
    getQueueStatus: async () => {
        const response = await api.get('/automation/queue-status');
        return response.data;
    },

    // Resend a failed outreach email
    resendFailedEmail: async (recordId) => {
        const response = await api.post(`/automation/resend/${recordId}`);
        return response.data;
    }
};

export default automationService;
