import { Home, Brain, Landmark, Sparkles, User } from "lucide-react";

// Platform navigation — Dumosense is ONE platform; these are domains within it.
export const NAV_ITEMS = [
  { key: "home", label: "Home", to: "/app", icon: Home, testid: "nav-home" },
  { key: "mindguard", label: "MindGuard", to: "/app/mindguard", icon: Brain, testid: "nav-mindguard" },
  { key: "health-reserve", label: "Health Reserve", to: "/app/health-reserve", icon: Landmark, testid: "nav-health-reserve" },
  { key: "ai", label: "AI", to: "/app/ai", icon: Sparkles, testid: "nav-ai" },
  { key: "profile", label: "Profile", to: "/app/profile", icon: User, testid: "nav-profile" },
];

export const DOMAIN_META = {
  mindguard: {
    label: "MindGuard",
    tagline: "Cognitive and mental wellbeing intelligence.",
  },
  health_reserve: {
    label: "Health Reserve",
    tagline: "Health-financial preparedness intelligence.",
  },
};

// Reusable data-state system (never framed as a medical problem).
export const DATA_STATES = {
  no_data: {
    core: "insufficient",
    title: "Let's start learning your pattern.",
    body: "Add your first observations so Dumosense can begin to understand you.",
  },
  insufficient: {
    core: "insufficient",
    title: "We're still learning your pattern.",
    body: "Continue adding observations to build a clearer picture over time.",
  },
  developing: {
    core: "learning",
    title: "Your personal pattern is becoming clearer.",
    body: "Keep going — each observation adds definition to your picture.",
  },
  established: {
    core: "intelligence",
    title: "Your usual pattern is becoming established.",
    body: "Dumosense can now recognise what is typical for you.",
  },
  no_change: {
    core: "static",
    title: "We haven't identified a meaningful change in your recent observations.",
    body: "Everything looks consistent with your usual pattern.",
  },
  meaningful_change: {
    core: "change",
    title: "Something looks different.",
    body: "A recent observation stands apart from your usual pattern. Here is what we noticed.",
  },
};
