import { loadStaticApi } from "./staticApi.js";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/** Build a query string, dropping empty values. */
export function toQuery(params = {}) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") qs.set(key, String(value));
  }
  const str = qs.toString();
  return str ? `?${str}` : "";
}

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // keep statusText
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

const httpApi = {
  filters: () => request("/filters"),
  skills: () => request("/skills"),
  trending: (params) => request(`/skills/trending${toQuery(params)}`),
  salaries: (params) => request(`/salaries${toQuery(params)}`),
  postings: (params) => request(`/postings${toQuery(params)}`),
  skillGap: (body) => request("/skills/gap", { method: "POST", body: JSON.stringify(body) }),
};

// VITE_STATIC_DATA=1 builds a backend-free site that reads exported JSON files
// (see backend/app/export_static.py); otherwise the app talks to the FastAPI server.
export const api = import.meta.env.VITE_STATIC_DATA
  ? loadStaticApi(import.meta.env.BASE_URL)
  : httpApi;
