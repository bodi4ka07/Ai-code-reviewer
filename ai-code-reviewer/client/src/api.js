// Усі запити йдуть на /api: у розробці його проксує Vite, у Docker nginx.
const BASE = '/api';
const TOKEN_KEY = 'token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // Помилки валідації FastAPI: [{ msg, loc }]
    return detail.map((d) => String(d.msg || '').replace(/^Value error, /, '')).join('. ');
  }
  return `Помилка сервера (${status})`;
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: payload });
  } catch {
    throw new ApiError('Немає зв’язку з сервером', 0);
  }
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(errorMessage(data, res.status), res.status);
  }
  return data;
}

export const api = {
  register: (email, password) => request('/auth/register', { method: 'POST', body: { email, password } }),
  login: (email, password) => request('/auth/login', { method: 'POST', form: { username: email, password } }),
  me: () => request('/users/me'),

  projects: () => request('/projects/'),
  project: (id) => request(`/projects/${id}`),
  createProject: (body) => request('/projects/', { method: 'POST', body }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),
  projectStats: (id) => request(`/projects/${id}/stats`),
  projectReviews: (id) => request(`/projects/${id}/reviews`),

  createReview: (body) => request('/reviews/', { method: 'POST', body }),
  review: (id) => request(`/reviews/${id}`),
  ask: (id, question, commentId) =>
    request(`/reviews/${id}/ask`, { method: 'POST', body: { question, comment_id: commentId || null } }),

  chats: () => request('/chats/'),
  createChat: (title) => request('/chats/', { method: 'POST', body: { title: title || null } }),
  chat: (id) => request(`/chats/${id}`),
  renameChat: (id, title) => request(`/chats/${id}`, { method: 'PATCH', body: { title } }),
  deleteChat: (id) => request(`/chats/${id}`, { method: 'DELETE' }),
  sendChatMessage: (id, content) => request(`/chats/${id}/messages`, { method: 'POST', body: { content } }),

  forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: { email } }),
  resetPassword: (token, password) => request('/auth/reset-password', { method: 'POST', body: { token, password } }),
};
