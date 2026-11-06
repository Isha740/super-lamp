const BASE = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "shortly_token";
const USER_KEY = "shortly_user";

export const session = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get username() { return localStorage.getItem(USER_KEY); },
  save(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, username);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data, fallback) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => e.msg).join(". ");
  return fallback;
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && session.token) headers.Authorization = `Bearer ${session.token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", 0);
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(data, `Request failed (${res.status})`), res.status);
  return data;
}

export const api = {
  register: (username, password) =>
    request("/api/auth/register", { method: "POST", body: { username, password }, auth: false }),
  login: (username, password) =>
    request("/api/auth/login", { method: "POST", body: { username, password }, auth: false }),
  listLinks: () => request("/api/links"),
  createLink: (long_url) => request("/api/links", { method: "POST", body: { long_url } }),
  getClicks: (code) => request(`/api/links/${code}/clicks`),
  deleteLink: (code) => request(`/api/links/${code}`, { method: "DELETE" }),
};
