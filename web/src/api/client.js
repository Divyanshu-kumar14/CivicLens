import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';
// Empty base = same origin (nginx proxies /jobs|/tickets|… to the API in
// prod). Dev uses vite.config.js proxy. Absolute URL only for local override.

export const api = axios.create({ baseURL: API_BASE, timeout: 15000 });

const num = (v, fallback = 0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

// DynamoDB round-trips can surface numbers as strings — coerce once at the
// boundary so render code can trust types (drawer crashed on .toFixed of a
// string before this existed).
export const normalizeTicket = (t = {}) => ({
  ...t,
  severity: num(t.severity),
  repeat_count: num(t.repeat_count, 1),
  centroid: [num(t.centroid?.[0]), num(t.centroid?.[1])],
  signals: Object.fromEntries(
    Object.entries(t.signals || {}).map(([k, v]) => {
      const n = Number(v);
      return [k, v === '' || v === null || v === undefined || Number.isNaN(n) ? v : n];
    }),
  ),
  trace: Array.isArray(t.trace) ? t.trace : [],
});

export const fetchTickets = (params = {}) =>
  api.get('/tickets', { params }).then((r) => (r.data || []).map(normalizeTicket));
export const fetchTicket = (id) => api.get(`/tickets/${id}`).then((r) => normalizeTicket(r.data));
export const overrideTicket = (id, payload) =>
  api.post(`/tickets/${id}/override`, payload).then((r) => normalizeTicket(r.data));
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
