import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { CoreMark } from "@/components/CoreMark";
import { ConsentSection } from "@/components/ConsentSection";
import { RingCard } from "@/components/RingCard";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { LogOut } from "lucide-react";

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-3 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value || "—"}</span>
    </div>
  );
}

export default function Profile() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const theme = useTheme();
  const [profile, setProfile] = useState(null);
  const [categories, setCategories] = useState([]);
  const [states, setStates] = useState({});
  const [ring, setRing] = useState(null);
  const [demoEligible, setDemoEligible] = useState(false);

  const loadRing = () => api.get("/home").then(({ data }) => setRing(data.ring));

  useEffect(() => {
    api.get("/profile").then(({ data }) => setProfile(data));
    api.get("/demo/status").then(({ data }) => setDemoEligible(!!data.demo_eligible)).catch(() => {});
    loadRing();
    api.get("/consent").then(({ data }) => {
      setCategories(data.categories);
      const init = {};
      data.categories.forEach((c) => (init[c.key] = c.granted));
      setStates(init);
    });
  }, []);

  const toggle = async (key, val) => {
    const next = { ...states, [key]: val };
    setStates(next);
    try {
      await api.put("/consent", { states: next });
      toast.success("Permission updated.");
    } catch {
      toast.error("Could not update permission.");
    }
  };

  const doLogout = async () => {
    await logout();
    navigate("/");
  };

  if (!profile) return <Skeleton className="h-96 w-full rounded-3xl" />;

  return (
    <div className="space-y-8">
      <section className="flex items-center gap-5 rounded-3xl border border-border bg-card p-6">
        <div className="relative">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary font-display text-xl font-medium text-primary">
            {(user?.first_name?.[0] || "D").toUpperCase()}
          </div>
          <CoreMark state="static" size={22} className="absolute -bottom-1 -right-1" />
        </div>
        <div>
          <p className="font-display text-lg font-medium text-foreground">{user?.name || user?.first_name}</p>
          <p className="text-sm text-muted-foreground">{user?.email}</p>
        </div>
      </section>

      <section className="rounded-3xl border border-border bg-card p-6">
        <h2 className="font-display text-lg font-medium text-foreground">Personal details</h2>
        <div className="mt-3">
          <Row label="First name" value={profile.first_name} />
          <Row label="Date of birth" value={profile.date_of_birth} />
          <Row label="Country" value={profile.country} />
          <Row label="Preferred language" value={profile.preferred_language} />
          <Row label="Caregiver context" value={profile.caregiver_context} />
        </div>
      </section>

      <section className="rounded-3xl border border-border bg-card p-6">
        <h2 className="font-display text-lg font-medium text-foreground">Appearance & accessibility</h2>
        <div className="mt-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-foreground">Theme</span>
            <Select value={theme.theme} onValueChange={(v) => v !== theme.theme && theme.toggleTheme()}>
              <SelectTrigger className="h-10 w-32 rounded-xl border-border bg-background-secondary" data-testid="profile-theme">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-foreground">Text size</span>
            <Select value={theme.textSize} onValueChange={(v) => theme.update({ textSize: v })}>
              <SelectTrigger className="h-10 w-32 rounded-xl border-border bg-background-secondary" data-testid="profile-text-size">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Default</SelectItem>
                <SelectItem value="large">Large</SelectItem>
                <SelectItem value="xlarge">Extra large</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-foreground">Reduced motion</span>
            <Switch checked={theme.reducedMotion} onCheckedChange={(v) => theme.update({ reducedMotion: v })}
              aria-label="Reduced motion" data-testid="profile-reduced-motion" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-foreground">High contrast</span>
            <Switch checked={theme.highContrast} onCheckedChange={(v) => theme.update({ highContrast: v })}
              aria-label="High contrast" data-testid="profile-high-contrast" />
          </div>
        </div>
      </section>

      <section
        data-testid="profile-membership"
        className="flex items-center justify-between gap-4 rounded-3xl border border-border bg-card p-6"
      >
        <div className="flex items-center gap-3">
          <CoreMark state="intelligence" size={30} />
          <div>
            <p className="font-display text-base font-medium text-foreground">Membership</p>
            <p className="text-sm capitalize text-muted-foreground">{user?.membership?.tier || "free"} plan</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => navigate("/app/membership")} data-testid="profile-membership-manage"
          className="rounded-full border-border bg-transparent hover:bg-surface-hover">
          Manage
        </Button>
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg font-medium text-foreground">Connected devices</h2>
        <RingCard ring={ring} onChanged={loadRing} />
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-lg font-medium text-foreground">Your data permissions</h2>
          <Button variant="ghost" onClick={() => navigate("/app/privacy")} data-testid="profile-privacy-center"
            className="rounded-full text-sm text-primary hover:bg-surface-hover">
            Privacy Center
          </Button>
        </div>
        <div className="flex flex-col gap-3">
          {categories.map((cat) => (
            <ConsentSection key={cat.key} category={cat} granted={!!states[cat.key]} onToggle={toggle} />
          ))}
        </div>
      </section>

      {demoEligible && (
      <section data-testid="profile-demo" className="rounded-3xl border border-border bg-card p-6">
        <h2 className="font-display text-lg font-medium text-foreground">Demo mode</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Load a labelled synthetic scenario for demonstrations. This replaces your current demo data
          and is clearly marked as sample data — never mixed silently with real information.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { key: "new_member", label: "New member", to: "/app" },
            { key: "established", label: "Established", to: "/app" },
            { key: "meaningful_change", label: "Meaningful change", to: "/app" },
            { key: "reserve_gap", label: "Reserve gap", to: "/app/health-reserve" },
          ].map((s) => (
            <Button
              key={s.key}
              variant="outline"
              data-testid={`demo-${s.key}`}
              onClick={async () => {
                try {
                  await api.post("/demo/apply", { scenario: s.key });
                  toast.success(`Loaded "${s.label}" demo scenario.`);
                  navigate(s.to);
                } catch {
                  toast.error("Could not load that scenario.");
                }
              }}
              className="h-auto whitespace-normal rounded-2xl border-border bg-background-secondary py-3 text-xs hover:border-rose hover:bg-surface-hover"
            >
              {s.label}
            </Button>
          ))}
        </div>
      </section>
      )}

      <Button variant="outline" onClick={doLogout} data-testid="profile-logout"
        className="h-12 w-full rounded-full border-border bg-transparent text-foreground hover:bg-surface-hover">
        <LogOut className="mr-2 h-4 w-4" /> Sign out
      </Button>
    </div>
  );
}
