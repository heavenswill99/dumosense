import { useState } from "react";
import { api } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Moon, HeartPulse, Activity, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

const SIGNALS = [
  { key: "sleep_hours", label: "Sleep", icon: Moon, suffix: "h" },
  { key: "resting_rhythm", label: "Resting rhythm", icon: HeartPulse, suffix: " bpm" },
  { key: "activity_minutes", label: "Activity", icon: Activity, suffix: " min" },
];

function SampleBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--rose)" }} />
      Sample data
    </span>
  );
}

/**
 * Dumosense Ring — a sensing layer (not a domain). In Alpha it streams clearly
 * labelled SAMPLE signals into the Health Graph.
 */
export function RingCard({ ring, onChanged, className }) {
  const [busy, setBusy] = useState(false);
  const connected = ring?.connected;
  const signals = ring?.signals;

  const act = async (fn, msg) => {
    setBusy(true);
    try {
      await fn();
      toast.success(msg);
      onChanged?.();
    } catch {
      toast.error("Could not reach the Ring. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="ring-card" className={cn("rounded-3xl border border-border bg-card p-6", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <CoreMark state={connected ? "sensing" : "insufficient"} size={34} />
          <div>
            <p className="font-display text-base font-medium text-foreground">Dumosense Ring</p>
            <p className="text-xs text-muted-foreground">
              {connected ? "Sensing your pattern continuously" : "A continuous sensing layer"}
            </p>
          </div>
        </div>
        {connected && <SampleBadge />}
      </div>

      {connected && signals ? (
        <>
          <div className="mt-5 grid grid-cols-3 gap-3">
            {SIGNALS.map(({ key, label, icon: Icon, suffix }) => (
              <div key={key} data-testid={`ring-signal-${key}`} className="rounded-2xl bg-secondary/60 p-3 text-center">
                <Icon className="mx-auto h-4 w-4 text-primary" strokeWidth={1.8} />
                <p className="mt-2 font-display text-lg font-medium text-foreground">
                  {signals[key] ? `${signals[key].value}${suffix}` : "—"}
                </p>
                <p className="text-[11px] text-muted-foreground">{label}</p>
              </div>
            ))}
          </div>
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => act(() => api.post("/ring/sync"), "Ring synced.")}
            data-testid="ring-sync"
            className="mt-4 h-10 rounded-full text-sm text-primary hover:bg-surface-hover"
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", busy && "animate-spin")} /> Sync latest
          </Button>
        </>
      ) : (
        <div className="mt-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Connect your Ring to add continuous sensing to your Health Graph. In this preview it
            streams realistic sample signals so you can see how it works.
          </p>
          <Button
            disabled={busy}
            onClick={() => act(() => api.post("/ring/connect"), "Dumosense Ring connected.")}
            data-testid="ring-connect"
            className="mt-4 h-11 rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90"
          >
            Connect Ring
          </Button>
        </div>
      )}
    </div>
  );
}

export default RingCard;
