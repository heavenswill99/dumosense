import { cn } from "@/lib/utils";
import { CoreMark } from "@/components/CoreMark";
import { StatusIndicator } from "@/components/StatusIndicator";
import { ArrowRight } from "lucide-react";

/**
 * InsightCard — editorial domain card. Clearly distinguishes observation from
 * interpretation via StatusIndicator; shows a calm empty state when there is
 * nothing meaningful to report yet.
 */
export function InsightCard({ domain, coreState = "insufficient", title, body, classification, action, onAction, testid }) {
  return (
    <div
      data-testid={testid || "insight-card"}
      className="group flex flex-col rounded-3xl border border-border bg-card p-6 transition-colors duration-300 hover:bg-surface-hover"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <CoreMark state={coreState} size={30} />
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{domain}</span>
        </div>
        {classification && <StatusIndicator classification={classification} />}
      </div>

      <p className="mt-5 font-display text-lg font-medium leading-snug text-foreground">{title}</p>
      {body && <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>}

      {action && (
        <button
          type="button"
          onClick={onAction}
          data-testid={`${testid || "insight-card"}-action`}
          className="mt-5 inline-flex items-center gap-1.5 self-start text-sm font-medium text-primary transition-transform duration-200 hover:gap-2.5"
        >
          {action}
          <ArrowRight className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export default InsightCard;
