import axios from "axios";

const configuredBackendUrl = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");
const isLocalBackend = configuredBackendUrl
  ? ["localhost", "127.0.0.1", "::1"].includes(new URL(configuredBackendUrl).hostname)
  : true;
const BACKEND_URL = import.meta.env.DEV && isLocalBackend ? "" : configuredBackendUrl;

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api/v1`,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

export async function ensureCsrf() {
  const { data } = await api.get("/auth/csrf/");
  if (!data?.csrfToken) {
    throw new Error("The server did not provide a CSRF token.");
  }
  api.defaults.headers.common["X-CSRFToken"] = data.csrfToken;
}

export function apiError(err) {
  const data = err?.response?.data;
  if (!data) return "Cannot reach the server. Please try again.";
  if (typeof data === "string") {
    if (/^\s*<(?:!doctype html|html)\b/i.test(data)) {
      return err.response.status === 403
        ? "Your security token could not be verified. Refresh the page and try again."
        : `The server returned an error (${err.response.status}). Please try again.`;
    }
    return data;
  }
  if (data.detail) return String(data.detail);
  return Object.entries(data)
    .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(" ") : msgs}`)
    .join(" | ");
}