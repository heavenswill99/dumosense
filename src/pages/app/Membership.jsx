import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function Membership() {
  const { user, setUser, checkAuth } = useAuth();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("");

  useEffect(() => { api.get("/membership").then(({ data }) => setData(data)); }, []);

  const choose = async (tier) => {
    if (tier === data.tier) return;
    setBusy(tier);
    try {
      await api.post("/membership", { tier });
      const { data: d } = await api.get("/membership");
      setData(d);
      await checkAuth();
      toast.success(`Switched to ${tier} (prototype — no payment taken).`);
    } catch {
      toast.error("Could not change your plan.");
    } finally {
      setBusy("");
    }
  };

  if (!data) return <Skeleton className="h-96 w-full rounded-3xl" />;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
        Prototype pricing for product testing — <span className="font-medium text-foreground">no payment is taken</span> and
        plans switch instantly so you can explore the value of each tier.
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {data.tiers.map((t) => {
          const current = t.key === data.tier;
          return (
            <div
              key={t.key}
              data-testid={`plan-${t.key}`}
              className={cn(
                "flex flex-col rounded-3xl border bg-card p-6 transition-colors",
                current ? "border-rose ring-1 ring-rose/40" : "border-border"
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CoreMark state={t.recommended ? "intelligence" : "static"} size={24} />
                  <h3 className="font-display text-lg font-medium text-foreground">{t.label}</h3>
                </div>
                {t.recommended && (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">Popular</span>
                )}
              </div>
              <p className="mt-3 font-display text-3xl font-light text-foreground">
                {t.price_month === 0 ? "Free" : `£${t.price_month}`}
                {t.price_month !== 0 && <span className="text-sm text-muted-foreground">/mo</span>}
              </p>
              {t.price_year !== 0 && <p className="text-xs text-muted-foreground">or £{t.price_year}/year</p>}
              <p className="mt-2 text-sm text-muted-foreground">{t.tagline}</p>

              <ul className="mt-5 flex-1 space-y-2.5">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-foreground">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-rose" />
                    {f}
                  </li>
                ))}
              </ul>

              <Button
                onClick={() => choose(t.key)}
                disabled={current || busy === t.key}
                data-testid={`plan-select-${t.key}`}
                variant={current ? "outline" : "default"}
                className={cn("mt-6 h-11 rounded-full",
                  current ? "border-border bg-transparent text-muted-foreground" : "bg-primary text-primary-foreground hover:opacity-90")}
              >
                {current ? "Current plan" : busy === t.key ? "Switching…" : `Choose ${t.label}`}
              </Button>
            </div>
          );
        })}
      </div>

      <div className="rounded-3xl border border-border bg-card p-6">
        <h3 className="font-display text-base font-medium text-foreground">Dumosense Ring</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          The Ring is a sensing layer that adds continuous signals to your Health Graph.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          <span className="rounded-full border border-border px-3 py-1 text-foreground">Ring · £{data.ring_pricing.ring}</span>
          <span className="rounded-full border border-border px-3 py-1 text-foreground">Ring + 12 months Personal · £{data.ring_pricing.ring_bundle}</span>
        </div>
      </div>
    </div>
  );
}
