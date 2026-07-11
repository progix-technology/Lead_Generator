import api from './api';

const authService = {
    login: async (email, password) => {
        // FastAPI's OAuth2 expects form data with 'username' and 'password' fields
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        // If successful, save the token to local storage
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
        }
        return response.data;
    },

    register: async (userData) => {
        // userData should be { email, password, first_name, last_name }
        const response = await api.post('/auth/register', userData);
        return response.data;
    },

    logout: () => {
        localStorage.removeItem('token');
        window.location.href = '/login';
    },

    getCurrentUser: async () => {
        const response = await api.get('/users/me');
        return response.data;
    },

    updateProfile: async (profileData) => {
        const response = await api.put('/users/me', profileData);
        return response.data;
    }
};

export default authService;
