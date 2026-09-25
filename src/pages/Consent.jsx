import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { ConsentSection } from "@/components/ConsentSection";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function Consent() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [states, setStates] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/consent").then(({ data }) => {
      setCategories(data.categories);
      const init = {};
      data.categories.forEach((c) => (init[c.key] = c.granted));
      setStates(init);
    });
  }, []);

  const toggle = (key, val) => setStates((s) => ({ ...s, [key]: val }));

  const submit = async () => {
    setLoading(true);
    try {
      await api.put("/consent", { states });
      await api.put("/onboarding", { consent_complete: true });
      navigate("/profile-setup");
    } catch {
      toast.error("Could not save your choices. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingLayout step={2} totalSteps={3} back="/privacy-promise">
      <div className="mb-7">
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground sm:text-4xl">
          Choose what you share
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-muted-foreground">
          Each choice is separate and in plain language. You can change these permissions later in
          your profile.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {categories.map((cat) => (
          <ConsentSection key={cat.key} category={cat} granted={!!states[cat.key]} onToggle={toggle} />
        ))}
      </div>

      <Button onClick={submit} disabled={loading || categories.length === 0} data-testid="consent-continue"
        className="mt-8 h-12 w-full rounded-full bg-primary text-primary-foreground hover:opacity-90">
        {loading ? "Saving…" : "I understand"}
      </Button>
    </OnboardingLayout>
  );
}
