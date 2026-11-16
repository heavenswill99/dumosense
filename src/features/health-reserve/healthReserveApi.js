import { api, ensureCsrf } from "@/lib/api";

const BASE = "/health-reserve";

export const healthReserveApi = {
  getConsents: () => api.get("/consents/"),
  createConsent: async (payload) => {
    await ensureCsrf();
    return api.post("/consents/", payload);
  },
  grantConsent: async (consentId, payload) => {
    await ensureCsrf();
    return api.post(`/consents/${consentId}/grant/`, payload);
  },
  withdrawConsent: async (consentId, payload) => {
    await ensureCsrf();
    return api.post(`/consents/${consentId}/withdraw/`, payload);
  },
  getAssessments: () => api.get(`${BASE}/assessments/`),
  createAssessment: async (payload) => {
    await ensureCsrf();
    return api.post(`${BASE}/assessments/create/`, payload);
  },
  getProgress: () => api.get(`${BASE}/progress/`),
  getFinancialProfiles: () => api.get(`${BASE}/financial-profile/`),
};
