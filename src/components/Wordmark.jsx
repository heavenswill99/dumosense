import { cn } from "@/lib/utils";
import { CoreMark } from "@/components/CoreMark";

/**
 * DUMOSENSE wordmark. The "O" is rendered as the Core Mark (brand source of truth).
 * size: "sm" | "md" | "lg"
 */
export function Wordmark({ size = "md", state = "static", className, showTagline = false }) {
  const cfg = {
    sm: { text: "text-base", mark: 16, gap: "gap-[1px]" },
    md: { text: "text-xl", mark: 20, gap: "gap-[2px]" },
    lg: { text: "text-3xl sm:text-4xl", mark: 36, gap: "gap-[3px]" },
  }[size];

  return (
    <div className={cn("inline-flex flex-col", className)} data-testid="dumosense-wordmark">
      <span className={cn("ds-wordmark inline-flex items-center text-foreground", cfg.text, cfg.gap)}>
        <span>DUM</span>
        <CoreMark state={state} size={cfg.mark} className="mx-[0.03em]" />
        <span>SENSE</span>
      </span>
      {showTagline && (
        <span className="ds-wordmark-tagline mt-1.5 text-[11px] text-rose">For a Life Lived in Full</span>
      )}
    </div>
  );
}

export default Wordmark;
