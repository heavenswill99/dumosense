const normalizePayload = (payload) => ({
  full_name: String(payload.full_name ?? "").trim(),
  email: String(payload.email ?? "").trim().toLowerCase(),
  phone_number: String(payload.phone_number ?? "").trim() || null,
  city: String(payload.city ?? "").trim() || null,
  country: String(payload.country ?? "").trim() || null,
  employment_status: String(payload.employment_status ?? "").trim() || null,
  occupation: String(payload.occupation ?? "").trim() || null,
  industry: String(payload.industry ?? "").trim() || null,
  product_interest: String(payload.product_interest ?? "").trim(),
  interest_reason: String(payload.interest_reason ?? "").trim() || null,
  testing_interest: String(payload.testing_interest ?? "").trim() || null,
  consent_accepted: Boolean(payload.consent_accepted),
});

const collectErrorMessages = (value) => {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(collectErrorMessages);
  if (value && typeof value === "object") return Object.values(value).flatMap(collectErrorMessages);
  return [];
};

const errorForStatus = (status) => {
  if (status === 400) return "Please check your registration details and try again.";
  if (status === 403) return "Your request was blocked. Refresh the page and try again.";
  if (status === 429) return "Too many attempts. Please wait a little before trying again.";
  if (status >= 500) return "The registration service is temporarily unavailable. Your registration has not been confirmed. Please try again shortly.";
  return `Registration could not be completed (error ${status}). Please try again.`;
};

export async function submitWaitlistRegistration(payload) {
  const normalized = normalizePayload(payload);
  const backendBaseUrl = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");
  const isLocalBackend = backendBaseUrl
    ? ["localhost", "127.0.0.1", "::1"].includes(new URL(backendBaseUrl).hostname)
    : true;
  const useDevProxy = import.meta.env.DEV && isLocalBackend;
  const url = useDevProxy || !backendBaseUrl
    ? "/api/v1/waitlist/"
    : `${backendBaseUrl}/api/v1/waitlist/`;

  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(normalized),
    });
  } catch {
    throw new Error("We couldn't reach the registration service. Please try again in a moment.");
  }

  let result;
  try {
    result = await response.json();
  } catch {
    result = null;
  }

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error("This email address is already registered for early access.");
    }

    const message =
      (typeof result?.message === "string" && result.message) ||
      (typeof result?.detail === "string" && result.detail) ||
      (typeof result?.error === "string" && result.error) ||
      collectErrorMessages(result)[0] ||
      errorForStatus(response.status);
    throw new Error(message);
  }

  if (!result || typeof result !== "object") {
    throw new Error("The registration service returned an unexpected response. Please try again.");
  }

  return result;
}
