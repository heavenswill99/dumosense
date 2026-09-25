import { cn } from "@/lib/utils";

/**
 * Non-colour-only status pill. Each classification is also labelled in text.
 * classification: observed | derived | interpretation | recommendation | action | neutral
 */
const MAP = {
  observed: { label: "Observed", dot: "var(--status-success)" },
  derived: { label: "Derived", dot: "var(--rose)" },
  interpretation: { label: "Interpretation", dot: "var(--status-warning)" },
  recommendation: { label: "Suggested", dot: "var(--rose)" },
  action: { label: "Your action", dot: "var(--primary)" },
  neutral: { label: "Status", dot: "var(--muted-foreground)" },
};

export function StatusIndicator({ classification = "neutral", label, className, testid }) {
  const cfg = MAP[classification] || MAP.neutral;
  return (
    <span
      data-testid={testid || `status-${classification}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground",
        className
      )}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: cfg.dot }} />
      {label || cfg.label}
    </span>
  );
}

export default StatusIndicator;
