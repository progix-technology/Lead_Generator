import api from './api';

const notificationService = {
  getNotifications: async () => {
    const res = await api.get('/notifications/');
    return res.data;
  },

  markAllRead: async () => {
    const res = await api.post('/notifications/read-all');
    return res.data;
  },

  clearAll: async () => {
    const res = await api.delete('/notifications/clear');
    return res.data;
  }
};

export default notificationService;
