import api from './api';

const companyService = {
    // Fetch a paginated list of companies
    getCompanies: async (skip = 0, limit = 10) => {
        const response = await api.get(`/companies/?skip=${skip}&limit=${limit}`);
        return response.data;
    },

    // Search companies live using Google Places API
    searchLiveCompanies: async (query, location, pageToken = null) => {
        const response = await api.get(`/companies/search-live`, {
            params: { query, location, pageToken }
        });
        return response.data;
    },

    // Scrape email for a company
    findCompanyEmail: async (companyName, location) => {
        const response = await api.get(`/companies/find-email`, {
            params: { company_name: companyName, location: location }
        });
        return response.data;
    },

    // Fetch a single company by ID
    getCompanyById: async (id) => {
        const response = await api.get(`/companies/${id}`);
        return response.data;
    },

    // Create a new company lead
    createCompany: async (companyData) => {
        const response = await api.post('/companies/', companyData);
        return response.data;
    },

    // Update an existing company
    updateCompany: async (id, companyData) => {
        const response = await api.put(`/companies/${id}`, companyData);
        return response.data;
    },

    // Delete a company
    deleteCompany: async (id) => {
        const response = await api.delete(`/companies/${id}`);
        return response.data;
    },

    // Trigger an email campaign
    sendCampaign: async (subjectTemplate, bodyTemplate, companyId = null) => {
        const response = await api.post('/companies/send-campaign', {
            subject_template: subjectTemplate,
            body_template: bodyTemplate,
            company_id: companyId
        });
        return response.data;
    },

    // Fetch audits for a specific company
    getAuditsForCompany: async (companyId) => {
        const response = await api.get(`/audits/company/${companyId}`);
        return response.data;
    },

    // Fetch lead score for a specific company
    getLeadScoreForCompany: async (companyId) => {
        const response = await api.get(`/scores/company/${companyId}`);
        return response.data;
    },

    // Generate custom cold email templates via LLM
    generateAITemplate: async (agencyName, services, portfolio, cta) => {
        const response = await api.post('/companies/ai-template', {
            agency_name: agencyName,
            services: services,
            portfolio: portfolio,
            cta: cta
        });
        return response.data;
    }
};

export default companyService;
