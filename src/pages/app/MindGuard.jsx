import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { EmptyState } from "@/components/EmptyState";
import { StatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import { DATA_STATES } from "@/lib/domains";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendChart } from "@/components/TrendChart";

const MOODS = [
  { value: "bright", label: "Bright" },
  { value: "rested", label: "Rested" },
  { value: "steady", label: "Steady" },
  { value: "tired", label: "Tired" },
  { value: "low", label: "Low" },
];

const COG_ITEMS = [
  { key: "clarity", label: "Mental clarity" },
  { key: "memory", label: "Everyday memory" },
  { key: "focus", label: "Focus" },
];
const BASELINE_LABEL = {
  STARTING: "Starting", LEARNING: "Learning", EMERGING: "Emerging", ESTABLISHED: "Established",
};

export default function MindGuard() {
  const [data, setData] = useState(null);
  const [trend, setTrend] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [cog, setCog] = useState({ clarity: 0, memory: 0, focus: 0 });
  const [saving, setSaving] = useState(false);

  const load = () => {
    api.get("/home").then(({ data }) => setData(data.insights.mindguard));
    api.get("/mindguard/trend").then(({ data }) => setTrend(data));
    api.get("/mindguard/baseline").then(({ data }) => setBaseline(data));
  };
  useEffect(() => { load(); }, []);

  const checkIn = async (mood) => {
    setSaving(true);
    try {
      await api.post("/observations", { domain: "mindguard", type: "wellbeing_checkin", value: mood });
      toast.success("Wellbeing check-in recorded.");
      load();
    } catch {
      toast.error("Could not record your check-in.");
    } finally {
      setSaving(false);
    }
  };

  const submitCognitive = async () => {
    const vals = COG_ITEMS.map((i) => cog[i.key]).filter(Boolean);
    if (vals.length < COG_ITEMS.length) {
      toast.error("Please rate each reflection.");
      return;
    }
    setSaving(true);
    try {
      const avg = Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
      await api.post("/observations", { domain: "mindguard", type: "cognitive_checkin", value: avg, note: JSON.stringify(cog) });
      toast.success("Cognitive reflection recorded.");
      setCog({ clarity: 0, memory: 0, focus: 0 });
      load();
    } catch {
      toast.error("Could not record your reflection.");
    } finally {
      setSaving(false);
    }
  };

  if (!data) return <Skeleton className="h-64 w-full rounded-3xl" />;

  const state = DATA_STATES[data.state] || DATA_STATES.no_data;

  return (
    <div className="space-y-8">
      <section className="flex items-start gap-4 rounded-3xl border border-border bg-card p-6">
        <CoreMark state={state.core} size={56} />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Cognitive & wellbeing</p>
          <p className="mt-2 font-display text-lg font-medium text-foreground">{state.title}</p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{state.body}</p>
          {data.count > 0 && (
            <div className="mt-3 flex items-center gap-2">
              <StatusIndicator classification="observed" />
              <span className="text-xs text-muted-foreground">{data.count} observations recorded</span>
            </div>
          )}
          {baseline && (
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-border bg-background-secondary px-3 py-1.5" data-testid="mindguard-baseline">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Baseline</span>
              <span className="text-xs font-medium text-primary">{BASELINE_LABEL[baseline.state]}</span>
              <span className="text-xs text-muted-foreground">· {baseline.total} observations</span>
            </div>
          )}
        </div>
      </section>

      {/* Cognitive reflection — a personal container, NOT a clinical test */}
      <section className="rounded-3xl border border-border bg-card p-6" data-testid="mindguard-cognitive">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-medium text-foreground">Cognitive check-in</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              A quick personal reflection on how your thinking felt today. This is not a clinical test
              or a score — just an observation for your pattern.
            </p>
          </div>
          <StatusIndicator classification="observed" label="Observed" />
        </div>
        <div className="mt-5 space-y-4">
          {COG_ITEMS.map((item) => (
            <div key={item.key}>
              <p className="mb-2 text-sm font-medium text-foreground">{item.label}</p>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setCog((c) => ({ ...c, [item.key]: n }))}
                    data-testid={`cog-${item.key}-${n}`}
                    aria-label={`${item.label} ${n} of 5`}
                    className={`h-10 flex-1 rounded-xl border text-sm transition-colors ${
                      cog[item.key] === n
                        ? "border-rose bg-rose text-white"
                        : "border-border bg-background-secondary text-foreground hover:border-rose"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">1 = low · 5 = high</span>
          <Button onClick={submitCognitive} disabled={saving} data-testid="cog-submit"
            className="rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90">
            Record reflection
          </Button>
        </div>
      </section>

      {/* Longitudinal wellbeing trend (observed) */}
      {trend?.ready && (
        <section data-testid="mindguard-trend" className="rounded-3xl border border-border bg-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-medium text-foreground">Your wellbeing over time</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {trend.stats
                  ? `Typically around "${trend.stats.average_mood}" across ${trend.stats.count} check-ins.`
                  : "Your recent wellbeing check-ins."}
              </p>
            </div>
            <StatusIndicator classification="observed" label="Observed" />
          </div>
          <div className="mt-5">
            <TrendChart data={trend.wellbeing} />
          </div>
        </section>
      )}

      {/* Daily wellbeing check-in (observed data) */}
      <section className="rounded-3xl border border-border bg-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg font-medium text-foreground">Wellbeing check-in</h2>
            <p className="mt-1 text-sm text-muted-foreground">How are you feeling today? This adds an observation to your pattern.</p>
          </div>
          <StatusIndicator classification="observed" label="Observed" />
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {MOODS.map((m) => (
            <Button
              key={m.value}
              variant="outline"
              disabled={saving}
              onClick={() => checkIn(m.value)}
              data-testid={`mindguard-mood-${m.value}`}
              className="rounded-full border-border bg-background-secondary hover:border-rose hover:bg-surface-hover"
            >
              {m.label}
            </Button>
          ))}
        </div>
      </section>

      {data.count === 0 && (
        <EmptyState
          testid="mindguard-empty"
          state="no_data"
          title="No interpretations yet."
          body="Once you've recorded a few check-ins, MindGuard will begin to reflect your wellbeing pattern here — always distinguishing what was observed from what it interprets."
        />
      )}
    </div>
  );
}
