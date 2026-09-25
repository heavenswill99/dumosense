import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { CoreMark } from "@/components/CoreMark";
import { Brain, Landmark, Compass, ArrowRight } from "lucide-react";

const OPTIONS = [
  {
    key: "mindguard",
    label: "MindGuard",
    body: "Cognitive and mental wellbeing intelligence.",
    icon: Brain,
    core: "learning",
  },
  {
    key: "health_reserve",
    label: "Health Reserve",
    body: "Health-financial preparedness intelligence.",
    icon: Landmark,
    core: "intelligence",
  },
  {
    key: "explore",
    label: "Explore Dumosense",
    body: "See how the platform connects your health intelligence.",
    icon: Compass,
    core: "sensing",
  },
];

export default function ChooseStart() {
  const navigate = useNavigate();
  const choose = (key) => navigate("/create-account", { state: { starting_point: key } });

  return (
    <OnboardingLayout back="/">
      <div className="mb-8 text-center">
        <CoreMark state="sensing" size={52} className="mb-5" />
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground sm:text-4xl">
          Where would you like to start?
        </h1>
        <p className="mt-3 text-base text-muted-foreground">
          Every path opens inside the same Dumosense platform.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {OPTIONS.map(({ key, label, body, icon: Icon, core }) => (
          <button
            key={key}
            type="button"
            onClick={() => choose(key)}
            data-testid={`start-option-${key}`}
            className="group flex items-center gap-5 rounded-3xl border border-border bg-card p-6 text-left transition-all duration-200 hover:border-rose hover:bg-surface-hover"
          >
            <span className="relative inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-secondary text-primary">
              <Icon className="h-6 w-6" strokeWidth={1.8} />
              <CoreMark state={core} size={20} className="absolute -bottom-1 -right-1" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-display text-lg font-medium text-foreground">{label}</span>
              <span className="mt-1 block text-sm text-muted-foreground">{body}</span>
            </span>
            <ArrowRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
          </button>
        ))}
      </div>
    </OnboardingLayout>
  );
}
