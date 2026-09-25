import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { InsightCard } from "@/components/InsightCard";
import { ProgressCard } from "@/components/ProgressCard";
import { Button } from "@/components/ui/button";
import { DATA_STATES } from "@/lib/domains";
import { Skeleton } from "@/components/ui/skeleton";
import { RingCard } from "@/components/RingCard";
import { WhyPopover } from "@/components/WhyPopover";
import { toast } from "sonner";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function Home() {
  const navigate = useNavigate();
  const [home, setHome] = useState(null);

  const load = () => api.get("/home").then(({ data }) => setHome(data));
  useEffect(() => { load(); }, []);

  const runNext = async (target) => {
    if (target === "/app/mindguard") {
      try {
        await api.post("/observations", { domain: "mindguard", type: "wellbeing_checkin", value: "steady" });
        toast.success("First check-in recorded.");
        load();
      } catch {
        toast.error("Could not record that. Please try again.");
      }
    } else {
      navigate(target);
    }
  };

  if (!home) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-3xl" />
        <Skeleton className="h-40 w-full rounded-3xl" />
        <div className="grid gap-6 sm:grid-cols-2">
          <Skeleton className="h-44 rounded-3xl" />
          <Skeleton className="h-44 rounded-3xl" />
        </div>
      </div>
    );
  }

  const patternState = DATA_STATES[home.pattern_state] || DATA_STATES.insufficient;
  const mg = home.insights.mindguard;
  const hr = home.insights.health_reserve;

  return (
    <div className="space-y-10 pb-4">
      {/* 1. WHAT'S HAPPENING */}
      <section className="ds-fade-up" data-testid="home-happening">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">What's happening</p>
        <h2 className="mt-2 font-display text-2xl font-normal text-foreground sm:text-3xl">
          {greeting()}, {home.first_name}.
        </h2>
        <p className="mt-1 text-base text-muted-foreground">
          Let's see what your health intelligence is telling us.
        </p>

        <div data-testid="home-pattern" className="mt-6 flex flex-col items-center gap-6 rounded-3xl border border-border bg-card p-8 text-center sm:flex-row sm:text-left">
          <CoreMark state={patternState.core} size={84} className="shrink-0" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Your pattern</p>
            <p className="mt-2 font-display text-lg font-medium text-foreground">{patternState.title}</p>
            <p className="mt-1 max-w-md text-sm leading-relaxed text-muted-foreground">{patternState.body}</p>
            <Button onClick={() => navigate("/app/mindguard")} data-testid="home-pattern-continue"
              variant="outline" className="mt-4 rounded-full border-border bg-transparent hover:bg-surface-hover">
              Continue
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <ProgressCard label="Understanding" value={home.progress.understanding}
            caption="How clearly Dumosense understands your pattern." />
          <ProgressCard label="Preparedness" value={home.progress.preparedness}
            caption="How ready you are to prepare ahead." />
          <ProgressCard label="Action" value={home.progress.action}
            caption="Practical steps you have taken so far." />
        </div>
      </section>

      {/* 2. WHAT CHANGED */}
      <section data-testid="home-changed">
        <h3 className="mb-4 font-display text-lg font-medium text-foreground">What changed</h3>
        {home.change?.state === "meaningful_change" ? (
          <div data-testid="home-change" className="flex items-start gap-4 rounded-3xl border border-rose/40 bg-card p-6">
            <CoreMark state="change" size={48} className="shrink-0" />
            <div className="flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Worth noticing</p>
              <p className="mt-2 font-display text-lg font-medium text-foreground">{home.change.title}</p>
              <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted-foreground">{home.change.body}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button onClick={() => navigate("/app/mindguard")} data-testid="home-change-mindguard"
                  variant="outline" className="rounded-full border-border bg-transparent hover:bg-surface-hover">
                  See in MindGuard
                </Button>
                <Button onClick={() => navigate("/app/ai?context=mindguard_change")} data-testid="home-change-ai"
                  className="rounded-full bg-primary text-primary-foreground hover:opacity-90">
                  Understand this
                </Button>
                <WhyPopover refKey="mindguard_change" />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 rounded-3xl border border-border bg-card p-6">
            <CoreMark state="static" size={40} />
            <p className="text-sm leading-relaxed text-muted-foreground">
              We haven't identified a meaningful change in your recent observations. Everything looks
              consistent with your usual pattern.
            </p>
          </div>
        )}
      </section>

      {/* 3. WHAT MATTERS */}
      <section data-testid="home-matters">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-medium text-foreground">What matters</h3>
          <WhyPopover refKey="pattern" />
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          <InsightCard
            testid="home-insight-mindguard"
            domain="MindGuard"
            coreState={DATA_STATES[mg.state]?.core || "insufficient"}
            title={DATA_STATES[mg.state]?.title}
            body={DATA_STATES[mg.state]?.body}
            classification={mg.count > 0 ? "observed" : undefined}
            action="Open MindGuard"
            onAction={() => navigate("/app/mindguard")}
          />
          <InsightCard
            testid="home-insight-health-reserve"
            domain="Health Reserve"
            coreState={hr.assessed ? (hr.state === "meaningful_change" ? "change" : "intelligence") : "insufficient"}
            title={hr.assessed ? hr.message : DATA_STATES[hr.state]?.title}
            body={hr.assessed
              ? (hr.gap > 0 ? `You're £${Number(hr.gap).toLocaleString()} from your target · ${hr.progress}% there.` : "Your preparedness target is met.")
              : DATA_STATES[hr.state]?.body}
            classification={hr.assessed ? "derived" : undefined}
            action="Open Health Reserve"
            onAction={() => navigate("/app/health-reserve")}
          />
        </div>
      </section>

      {/* 4. WHAT YOU CAN DO */}
      <section data-testid="home-can-do">
        <h3 className="mb-4 font-display text-lg font-medium text-foreground">What you can do</h3>
        <div data-testid="home-what-next"
          className="flex flex-col items-start gap-4 rounded-3xl border border-rose/40 bg-secondary/50 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <CoreMark state="sensing" size={40} />
            <p className="font-display text-base font-medium text-foreground">{home.next_action.title}</p>
          </div>
          <Button onClick={() => runNext(home.next_action.target)} data-testid="home-next-action"
            className="rounded-full bg-primary px-7 text-primary-foreground hover:opacity-90">
            {home.next_action.cta}
          </Button>
        </div>
      </section>

      {/* 5. WHAT YOU'RE PREPARING FOR */}
      <section data-testid="home-preparing">
        <h3 className="mb-4 font-display text-lg font-medium text-foreground">What you're preparing for</h3>
        <div className="rounded-3xl border border-border bg-card p-6">
          {hr.assessed ? (
            <>
              <div className="flex items-center justify-between">
                <p className="font-display text-base font-medium text-foreground">{hr.message}</p>
                <span className="font-mono text-xs text-muted-foreground">{hr.progress}%</span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full transition-[width] duration-700"
                  style={{ width: `${hr.progress}%`, background: "linear-gradient(90deg, var(--burgundy), var(--rose))" }} />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {hr.gap > 0 ? `£${Number(hr.gap).toLocaleString()} from your preparedness target of £${Number(hr.target).toLocaleString()}.` : "You've reached your preparedness target."}
              </p>
              <Button onClick={() => navigate("/app/health-reserve")} variant="outline"
                data-testid="home-preparing-open" className="mt-4 rounded-full border-border bg-transparent hover:bg-surface-hover">
                Open Health Reserve
              </Button>
            </>
          ) : (
            <div className="flex items-center gap-4">
              <CoreMark state="insufficient" size={40} />
              <div className="flex-1">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Understand how prepared you are for what may come. This is a reflection, never a prediction.
                </p>
                <Button onClick={() => navigate("/app/health-reserve")} data-testid="home-preparing-start"
                  className="mt-3 rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90">
                  Check preparedness
                </Button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 6. WHAT WE'RE STILL LEARNING */}
      <section data-testid="home-learning">
        <h3 className="mb-4 font-display text-lg font-medium text-foreground">What we're still learning</h3>
        <RingCard ring={home.ring} onChanged={load} />
        {(mg.count < 5 || !hr.assessed) && (
          <p className="mt-3 rounded-2xl bg-secondary/50 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
            {mg.count < 5 && "We're still learning your wellbeing pattern. "}
            {!hr.assessed && "Your preparedness picture will take shape once you complete a Health Reserve assessment. "}
            Insufficient data never means poor health — just that there's more to learn.
          </p>
        )}
      </section>
    </div>
  );
}
