import { cn } from "@/lib/utils";

/**
 * ProgressCard — reflects a qualitative journey (Understanding / Preparedness /
 * Action). Intentionally NOT a health score or gamified points system.
 */
export function ProgressCard({ label, value = 0, caption, className, testid }) {
  const pct = Math.max(0, Math.min(100, value));
  const stage = pct === 0 ? "Not started" : pct < 34 ? "Beginning" : pct < 67 ? "Developing" : "Established";

  return (
    <div
      data-testid={testid || `progress-${label?.toLowerCase()}`}
      className={cn("rounded-3xl border border-border bg-card p-5", className)}
    >
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="font-mono text-xs text-muted-foreground">{stage}</span>
      </div>
      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%`, background: "linear-gradient(90deg, var(--burgundy), var(--rose))" }}
        />
      </div>
      {caption && <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{caption}</p>}
    </div>
  );
}

export default ProgressCard;
