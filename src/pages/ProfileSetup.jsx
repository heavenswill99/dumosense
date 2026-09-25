import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

const COUNTRIES = ["United Kingdom", "United States", "Canada", "Australia", "India", "Germany", "France", "Other"];
const LANGUAGES = ["English", "Spanish", "French", "German", "Hindi", "Portuguese", "Other"];

function A11yRow({ label, description, children, testid }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-card p-4" data-testid={testid}>
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export default function ProfileSetup() {
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const theme = useTheme();

  const [form, setForm] = useState({
    first_name: user?.first_name || "",
    date_of_birth: "",
    country: "",
    preferred_language: "English",
    caregiver_context: "",
  });
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const finish = async (skip = false) => {
    setLoading(true);
    try {
      const payload = skip
        ? { first_name: form.first_name }
        : { ...form };
      payload.accessibility = {
        text_size: theme.textSize,
        reduced_motion: theme.reducedMotion,
        high_contrast: theme.highContrast,
      };
      await api.put("/profile", payload);
      const { data } = await api.put("/onboarding", { profile_complete: true });
      setUser(data);
      navigate("/profile-complete");
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingLayout step={3} totalSteps={3} back="/consent">
      <div className="mb-7">
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground sm:text-4xl">
          A little about you
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-muted-foreground">
          Only the essentials for now. You can skip anything that isn't required and add more later.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <FormField id="first_name" label="First name" value={form.first_name} onChange={set("first_name")}
          required testid="profile-first-name" />
        <FormField id="date_of_birth" label="Date of birth" type="date" value={form.date_of_birth}
          onChange={set("date_of_birth")} helper="Used to understand age-related context." testid="profile-dob" />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-foreground">Country</label>
            <Select value={form.country} onValueChange={(v) => setForm((f) => ({ ...f, country: v }))}>
              <SelectTrigger className="h-12 rounded-xl border-border bg-background-secondary" data-testid="profile-country">
                <SelectValue placeholder="Select country" />
              </SelectTrigger>
              <SelectContent>
                {COUNTRIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-foreground">Preferred language</label>
            <Select value={form.preferred_language} onValueChange={(v) => setForm((f) => ({ ...f, preferred_language: v }))}>
              <SelectTrigger className="h-12 rounded-xl border-border bg-background-secondary" data-testid="profile-language">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((l) => (<SelectItem key={l} value={l}>{l}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <FormField id="caregiver_context" label="Caregiver or family context (optional)"
          value={form.caregiver_context} onChange={set("caregiver_context")}
          placeholder="e.g. Supporting a parent" testid="profile-caregiver" />
      </div>

      <div className="mt-9">
        <h2 className="font-display text-lg font-medium text-foreground">Accessibility preferences</h2>
        <p className="mt-1 text-sm text-muted-foreground">These apply immediately and are saved with your profile.</p>
        <div className="mt-4 flex flex-col gap-3">
          <A11yRow label="Larger text" description="Increase text size across the app" testid="a11y-text">
            <Select value={theme.textSize} onValueChange={(v) => theme.update({ textSize: v })}>
              <SelectTrigger className="h-10 w-32 rounded-xl border-border bg-background-secondary" data-testid="a11y-text-size">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Default</SelectItem>
                <SelectItem value="large">Large</SelectItem>
                <SelectItem value="xlarge">Extra large</SelectItem>
              </SelectContent>
            </Select>
          </A11yRow>
          <A11yRow label="Reduced motion" description="Minimise animation" testid="a11y-motion">
            <Switch checked={theme.reducedMotion} onCheckedChange={(v) => theme.update({ reducedMotion: v })}
              aria-label="Reduced motion" data-testid="a11y-reduced-motion" />
          </A11yRow>
          <A11yRow label="High contrast" description="Stronger borders and text" testid="a11y-contrast">
            <Switch checked={theme.highContrast} onCheckedChange={(v) => theme.update({ highContrast: v })}
              aria-label="High contrast" data-testid="a11y-high-contrast" />
          </A11yRow>
        </div>
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row-reverse">
        <Button onClick={() => finish(false)} disabled={loading} data-testid="profile-continue"
          className="h-12 rounded-full bg-primary px-8 text-primary-foreground hover:opacity-90 sm:flex-1">
          {loading ? "Saving…" : "Continue"}
        </Button>
        <Button variant="ghost" onClick={() => finish(true)} disabled={loading} data-testid="profile-skip"
          className="h-12 rounded-full text-foreground hover:bg-surface-hover">
          Skip for now
        </Button>
      </div>
    </OnboardingLayout>
  );
}
