import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { StatusIndicator } from "@/components/StatusIndicator";
import { ConsentSection } from "@/components/ConsentSection";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Database, Radio, CheckCircle2, Circle } from "lucide-react";

function fmt(ts) {
  try {
    return new Date(ts).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return "";
  }
}

const CLASS_LABEL = {
  observed: "observed", derived: "derived", interpretation: "interpretation",
  recommendation: "recommendation", user_action: "action",
};

export default function PrivacyCenter() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState(null);
  const [states, setStates] = useState({});

  const load = () => {
    api.get("/privacy/summary").then(({ data }) => {
      setSummary(data);
      const s = {};
      data.categories.forEach((c) => (s[c.key] = c.granted));
      setStates(s);
    });
    api.get("/data-history").then(({ data }) => setHistory(data.entries));
  };
  useEffect(() => { load(); }, []);

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

  if (!summary) return <Skeleton className="h-96 w-full rounded-3xl" />;

  return (
    <div className="space-y-8">
      <div className="rounded-3xl border border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
        Your information should work for you. We explain what is used, keep observations separate from
        interpretation, and never sell personal health information to advertisers.
      </div>

      {/* Your data */}
      <section data-testid="privacy-your-data">
        <h2 className="mb-3 font-display text-lg font-medium text-foreground">Your data</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { k: "total", label: "Total records" },
            { k: "mindguard", label: "MindGuard" },
            { k: "ring", label: "Ring signals" },
            { k: "health_reserve", label: "Health Reserve" },
          ].map((c) => (
            <div key={c.k} className="rounded-2xl border border-border bg-card p-4 text-center">
              <Database className="mx-auto h-4 w-4 text-primary" strokeWidth={1.8} />
              <p className="mt-2 font-display text-xl font-medium text-foreground">{summary.counts[c.k]}</p>
              <p className="text-[11px] text-muted-foreground">{c.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Connected sources */}
      <section data-testid="privacy-sources">
        <h2 className="mb-3 font-display text-lg font-medium text-foreground">Connected sources</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {summary.sources.map((s) => (
            <div key={s.key} className="flex items-center gap-3 rounded-2xl border border-border bg-card p-4">
              <Radio className={cn("h-5 w-5", s.active ? "text-rose" : "text-muted-foreground")} strokeWidth={1.8} />
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.note}</p>
              </div>
              {s.active
                ? <CheckCircle2 className="h-5 w-5 text-success" />
                : <Circle className="h-5 w-5 text-muted-foreground" />}
            </div>
          ))}
        </div>
      </section>

      {/* Permissions (AI use + Research distinct) */}
      <section data-testid="privacy-permissions">
        <h2 className="mb-3 font-display text-lg font-medium text-foreground">Your permissions</h2>
        <div className="flex flex-col gap-3">
          {summary.categories.map((cat) => (
            <ConsentSection key={cat.key} category={cat} granted={!!states[cat.key]} onToggle={toggle} />
          ))}
        </div>
      </section>

      {/* Data history timeline */}
      <section data-testid="privacy-history">
        <h2 className="mb-3 font-display text-lg font-medium text-foreground">Data history</h2>
        {!history ? (
          <Skeleton className="h-40 rounded-3xl" />
        ) : history.length === 0 ? (
          <p className="rounded-3xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Nothing recorded yet. Your history will appear here as you use Dumosense.
          </p>
        ) : (
          <ol className="relative ml-3 border-l border-border">
            {history.map((e, i) => (
              <li key={i} data-testid="history-entry" className="mb-5 ml-5">
                <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full border-2 border-background bg-rose" />
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{e.label}</span>
                  {e.detail && <span className="text-sm text-muted-foreground">· {e.detail}</span>}
                  <StatusIndicator classification={CLASS_LABEL[e.classification] || "neutral"} />
                  {e.sample && (
                    <span className="rounded-full bg-rose/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-rose">Sample</span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{e.domain} · {fmt(e.date)}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
