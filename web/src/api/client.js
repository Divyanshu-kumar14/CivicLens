import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';
// Empty base = same origin (nginx proxies /jobs|/tickets|… to the API in
// prod). Dev uses vite.config.js proxy. Absolute URL only for local override.

export const api = axios.create({ baseURL: API_BASE, timeout: 15000 });

export const fetchTickets = (params = {}) => api.get('/tickets', { params }).then((r) => r.data);
export const fetchTicket = (id) => api.get(`/tickets/${id}`).then((r) => r.data);
export const overrideTicket = (id, payload) => api.post(`/tickets/${id}/override`, payload).then((r) => r.data);
export const fetchJob = (id) => api.get(`/jobs/${id}`).then((r) => r.data);
export const createJob = (payload) => api.post('/jobs', payload).then((r) => r.data);
// UploadZone path: { video: File, gps?: File, ward?: string } -> multipart /jobs/upload
export const uploadJob = ({ video, gps, ward = 'ward-12-demo' }) => {
  const form = new FormData();
  form.append('video', video);
  if (gps) form.append('gps', gps);
  form.append('ward', ward);
  return api.post('/jobs/upload', form).then((r) => r.data);
};
export const exportCSV = (status = 'filed') =>
  api.get('/export.csv', { params: { status }, responseType: 'blob' });
export const testWebhook = (url) => api.post('/webhooks/test', { url }).then((r) => r.data);
