import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { StatusIndicator } from "@/components/StatusIndicator";
import { WhyPopover } from "@/components/WhyPopover";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Check } from "lucide-react";
import { toast } from "sonner";

const money = (n) => (n == null ? "—" : `£${Number(n).toLocaleString()}`);

function Assessment({ initial, onDone }) {
  const [form, setForm] = useState({
    household_size: String(initial?.household_size || 1),
    cost_level: initial?.cost_level || "medium",
    has_coverage: initial?.has_coverage || false,
    current_reserve: String(initial?.current_reserve ?? ""),
    monthly_capacity: String(initial?.monthly_capacity ?? ""),
  });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setSaving(true);
    try {
      const { data } = await api.post("/reserve/assessment", {
        household_size: parseInt(form.household_size, 10) || 1,
        cost_level: form.cost_level,
        has_coverage: form.has_coverage,
        current_reserve: parseFloat(form.current_reserve) || 0,
        monthly_capacity: parseFloat(form.monthly_capacity) || 0,
      });
      toast.success("Preparedness assessment saved.");
      onDone(data);
    } catch {
      toast.error("Could not save your assessment.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-3xl border border-border bg-card p-6" data-testid="reserve-assessment">
      <h2 className="font-display text-lg font-medium text-foreground">Understand your preparedness</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        A few simple inputs. This is a reflection, not a prediction — and never financial advice.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-foreground">Household size</label>
          <Select value={form.household_size} onValueChange={(v) => setForm((f) => ({ ...f, household_size: v }))}>
            <SelectTrigger className="h-12 rounded-xl border-border bg-background-secondary" data-testid="reserve-household">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>{[1, 2, 3, 4, 5, 6].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-foreground">Local cost level</label>
          <Select value={form.cost_level} onValueChange={(v) => setForm((f) => ({ ...f, cost_level: v }))}>
            <SelectTrigger className="h-12 rounded-xl border-border bg-background-secondary" data-testid="reserve-cost">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Lower</SelectItem>
              <SelectItem value="medium">Typical</SelectItem>
              <SelectItem value="high">Higher</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <FormField id="current_reserve" label="Current set-aside (£)" type="number" value={form.current_reserve}
          onChange={set("current_reserve")} placeholder="0" testid="reserve-current" />
        <FormField id="monthly_capacity" label="Comfortable monthly amount (£)" type="number" value={form.monthly_capacity}
          onChange={set("monthly_capacity")} placeholder="0" testid="reserve-monthly" />
      </div>
      <div className="mt-4 flex items-center justify-between rounded-2xl border border-border bg-background-secondary p-4">
        <div>
          <p className="text-sm font-medium text-foreground">I have some health coverage</p>
          <p className="text-xs text-muted-foreground">e.g. insurance or a public scheme</p>
        </div>
        <Switch checked={form.has_coverage} onCheckedChange={(v) => setForm((f) => ({ ...f, has_coverage: v }))}
          aria-label="Has coverage" data-testid="reserve-coverage" />
      </div>
      <Button onClick={submit} disabled={saving} data-testid="reserve-submit"
        className="mt-5 h-12 w-full rounded-full bg-primary text-primary-foreground hover:opacity-90">
        {saving ? "Saving…" : "See my preparedness"}
      </Button>
    </div>
  );
}

export default function HealthReserve() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [editing, setEditing] = useState(false);

  const load = () => api.get("/reserve").then(({ data }) => setData(data));
  useEffect(() => { load(); }, []);

  if (!data) return <Skeleton className="h-72 w-full rounded-3xl" />;

  if (!data.assessed || editing) {
    return (
      <div className="space-y-6">
        <div className="rounded-3xl border border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
          Health Reserve is not a bank, insurer or investment service and does not provide financial advice.
        </div>
        <Assessment initial={data.inputs} onDone={(d) => { setData(d); setEditing(false); }} />
      </div>
    );
  }

  const onTarget = data.state === "on_target";
  const toggle = async (id) => {
    const { data: d } = await api.post(`/reserve/action/${id}/toggle`);
    setData(d);
  };
  const doneCount = data.actions.filter((a) => a.done).length;

  return (
    <div className="space-y-8">
      {/* Current state → target → gap */}
      <section className="rounded-3xl border border-border bg-card p-6" data-testid="reserve-result">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <CoreMark state={onTarget ? "intelligence" : "change"} size={40} />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Preparedness</p>
              <p className="mt-1 font-display text-lg font-medium text-foreground">{data.message}</p>
            </div>
          </div>
          <WhyPopover refKey="reserve_gap" />
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-2xl bg-secondary/60 p-4">
            <p className="font-display text-xl font-medium text-foreground">{money(data.current_reserve)}</p>
            <p className="mt-1 text-xs text-muted-foreground">Current</p>
          </div>
          <div className="rounded-2xl bg-secondary/60 p-4">
            <p className="font-display text-xl font-medium text-foreground">{money(data.target)}</p>
            <p className="mt-1 text-xs text-muted-foreground">Target</p>
          </div>
          <div className="rounded-2xl bg-secondary/60 p-4">
            <p className="font-display text-xl font-medium text-foreground">{money(data.gap)}</p>
            <p className="mt-1 text-xs text-muted-foreground">Gap</p>
          </div>
        </div>

        <div className="mt-5">
          <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
            <span>Progress to target</span><span className="font-mono">{data.progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div className="h-full rounded-full transition-[width] duration-700"
              style={{ width: `${data.progress}%`, background: "linear-gradient(90deg, var(--burgundy), var(--rose))" }} />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {!onTarget && (
            <Button onClick={() => navigate("/app/ai?context=reserve_gap")} data-testid="reserve-understand"
              className="rounded-full bg-primary text-primary-foreground hover:opacity-90">
              Understand this
            </Button>
          )}
          <Button variant="outline" onClick={() => setEditing(true)} data-testid="reserve-edit"
            className="rounded-full border-border bg-transparent hover:bg-surface-hover">
            Update inputs
          </Button>
          <StatusIndicator classification="observed" label="Your inputs" className="ml-auto self-center" />
        </div>
      </section>

      {/* Action plan */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-medium text-foreground">Your action plan</h3>
          <span className="text-xs text-muted-foreground">{doneCount}/{data.actions.length} done</span>
        </div>
        <div className="flex flex-col gap-3">
          {data.actions.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => toggle(a.id)}
              data-testid={`reserve-action-${a.id}`}
              className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:bg-surface-hover"
            >
              <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${a.done ? "border-rose bg-rose text-white" : "border-border"}`}>
                {a.done && <Check className="h-4 w-4" />}
              </span>
              <span>
                <span className={`block text-sm font-medium ${a.done ? "text-muted-foreground line-through" : "text-foreground"}`}>{a.title}</span>
                <span className="mt-0.5 block text-xs text-muted-foreground">{a.description}</span>
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
