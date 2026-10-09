import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: API_BASE, timeout: 15000 });

export const fetchTickets = (params = {}) => api.get('/tickets', { params }).then((r) => r.data);
export const fetchTicket = (id) => api.get(`/tickets/${id}`).then((r) => r.data);
export const overrideTicket = (id, payload) => api.post(`/tickets/${id}/override`, payload).then((r) => r.data);
export const fetchJob = (id) => api.get(`/jobs/${id}`).then((r) => r.data);
export const createJob = (payload) => api.post('/jobs', payload).then((r) => r.data);
export const exportCSV = (status = 'filed') =>
  api.get('/export.csv', { params: { status }, responseType: 'blob' });
export const testWebhook = (url) => api.post('/webhooks/test', { url }).then((r) => r.data);
