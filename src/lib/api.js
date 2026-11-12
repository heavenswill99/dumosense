import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api/v1`,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

export async function ensureCsrf() {
  try {
    await api.get("/auth/csrf/");
  } catch {
    // the later request will show the real error
  }
}

export function apiError(err) {
  const data = err?.response?.data;
  if (!data) return "Cannot reach the server. Please try again.";
  if (typeof data === "string") return data;
  if (data.detail) return String(data.detail);
  return Object.entries(data)
    .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(" ") : msgs}`)
    .join(" | ");
}