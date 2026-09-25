import { CoreMark } from "@/components/CoreMark";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { key: "what_we_observed", label: "What we observed", cls: "observed" },
  { key: "what_changed", label: "What changed", cls: "observed" },
  { key: "what_it_may_mean", label: "What it may mean", cls: "interp" },
  { key: "what_we_dont_know", label: "What we don't know", cls: "unknown" },
  { key: "what_you_can_do_next", label: "What you can do next", cls: "action" },
];

const EPISTEMIC = {
  KNOWN: { label: "Known", tone: "var(--status-success)" },
  INFERRED: { label: "Inferred", tone: "var(--rose)" },
  POSSIBLE: { label: "Possible", tone: "var(--status-warning)" },
  UNKNOWN: { label: "Unknown", tone: "var(--muted-foreground)" },
};

/**
 * Dumosense AI structured explanation — the five-part intelligence response.
 * Distinguishes observation from interpretation and never hides uncertainty.
 */
export function StructuredExplanation({ data }) {
  if (!data?.sections) return null;
  const ep = EPISTEMIC[data.epistemic] || EPISTEMIC.UNKNOWN;

  return (
    <div data-testid="ai-structured-explanation" className="rounded-3xl border border-border bg-card p-6">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CoreMark state="intelligence" size={30} />
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Dumosense AI · Intelligence
          </span>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: ep.tone }} />
          {ep.label}
        </span>
      </div>

      <div className="space-y-4">
        {SECTIONS.map(({ key, label, cls }) =>
          data.sections[key] ? (
            <div key={key} className={cn("border-l-2 pl-4", cls === "unknown" ? "border-muted" : "border-rose")}>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm leading-relaxed text-foreground">{data.sections[key]}</p>
            </div>
          ) : null
        )}
      </div>

      {data.provenance && (
        <p className="mt-5 rounded-2xl bg-secondary/50 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Why am I seeing this? </span>
          {data.provenance}
        </p>
      )}
    </div>
  );
}

export default StructuredExplanation;
