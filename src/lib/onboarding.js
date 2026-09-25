export function nextOnboardingRoute(user) {
  const o = user?.onboarding || {};
  if (!o.privacy_accepted) return "/privacy-promise";
  if (!o.consent_complete) return "/consent";
  if (!o.profile_complete) return "/profile-setup";
  return "/app";
}
