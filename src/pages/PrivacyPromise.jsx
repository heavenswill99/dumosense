import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ShieldCheck, Eye, GitBranch, Ban, SlidersHorizontal } from "lucide-react";

const PRINCIPLES = [
  { icon: SlidersHorizontal, text: "You control your permissions." },
  { icon: Eye, text: "We explain what information is being used." },
  { icon: GitBranch, text: "We distinguish observations from interpretation." },
  { icon: Ban, text: "We do not sell personal health information to advertisers." },
  { icon: ShieldCheck, text: "You can review your data permissions at any time." },
];

export default function PrivacyPromise() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showMore, setShowMore] = useState(false);

  const cont = async () => {
    setLoading(true);
    try {
      await api.put("/onboarding", { privacy_accepted: true });
      navigate("/consent");
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingLayout step={1} totalSteps={3} back="/create-account">
      <div className="mb-8">
        <CoreMark state="intelligence" size={52} className="mb-6" />
        <h1 className="font-display text-3xl font-normal leading-tight tracking-tight text-foreground sm:text-4xl">
          Your information should work for you.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
          Dumosense is designed around your control, transparency and the responsible use of your
          personal information. Here is what that means in practice.
        </p>
      </div>

      <ul className="flex flex-col gap-3">
        {PRINCIPLES.map(({ icon: Icon, text }, i) => (
          <li
            key={i}
            data-testid={`privacy-principle-${i}`}
            className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4"
          >
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
              <Icon className="h-5 w-5" strokeWidth={1.8} />
            </span>
            <span className="text-sm leading-relaxed text-foreground">{text}</span>
          </li>
        ))}
      </ul>

      {showMore && (
        <p className="mt-5 rounded-2xl border border-border bg-background-secondary p-5 text-sm leading-relaxed text-muted-foreground" data-testid="privacy-more">
          We aim to be clear about how your data is used and to give you meaningful choices. No system
          can promise perfect privacy or absolute security, so we focus on strong, responsible
          practices and keeping you in control of your permissions.
        </p>
      )}

      <div className="mt-8 flex flex-col gap-3 sm:flex-row-reverse">
        <Button onClick={cont} disabled={loading} data-testid="privacy-continue"
          className="h-12 rounded-full bg-primary px-8 text-primary-foreground hover:opacity-90 sm:flex-1">
          {loading ? "…" : "Continue"}
        </Button>
        <Button variant="ghost" onClick={() => setShowMore((s) => !s)} data-testid="privacy-read-more"
          className="h-12 rounded-full text-foreground hover:bg-surface-hover">
          Read more about privacy
        </Button>
      </div>
    </OnboardingLayout>
  );
}
