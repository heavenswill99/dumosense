import { cn } from "@/lib/utils";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";

/**
 * Reusable, reassuring empty / data state.
 * Never framed as a medical problem or poor health.
 */
export function EmptyState({ state = "insufficient", title, body, ctaLabel, onCta, className, testid }) {
  const coreState =
    { no_data: "insufficient", insufficient: "insufficient", developing: "learning", established: "intelligence", meaningful_change: "change", no_change: "static" }[state] ||
    state;

  return (
    <div
      data-testid={testid || "empty-state"}
      className={cn(
        "flex flex-col items-center justify-center rounded-3xl border border-border bg-background-secondary px-6 py-12 text-center",
        className
      )}
    >
      <CoreMark state={coreState} size={64} className="mb-6" />
      <p className="max-w-md font-display text-lg font-medium text-foreground">{title}</p>
      {body && <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">{body}</p>}
      {ctaLabel && (
        <Button
          onClick={onCta}
          data-testid={`${testid || "empty-state"}-cta`}
          className="mt-6 rounded-full bg-primary px-7 text-primary-foreground hover:opacity-90"
        >
          {ctaLabel}
        </Button>
      )}
    </div>
  );
}

export default EmptyState;
