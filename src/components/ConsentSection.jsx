import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

/**
 * ConsentSection / PermissionRow — plain-language, per-category consent.
 * Consent is never bundled into one vague checkbox.
 */
export function ConsentSection({ category, granted, onToggle }) {
  const required = category.required;
  return (
    <div
      data-testid={`consent-row-${category.key}`}
      className="rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-display text-base font-medium text-foreground">{category.label}</h3>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                required
                  ? "bg-primary/10 text-primary"
                  : "bg-secondary text-secondary-foreground"
              )}
            >
              {required ? "Required" : "Optional"}
            </span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-foreground/80">
            <span className="font-medium text-foreground">What: </span>
            {category.what}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">Why: </span>
            {category.why}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-center gap-1 pt-1">
          <Switch
            checked={granted}
            disabled={required}
            onCheckedChange={(v) => onToggle(category.key, v)}
            aria-label={`Allow ${category.label}`}
            data-testid={`consent-toggle-${category.key}`}
          />
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {granted ? "Allowed" : "Off"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default ConsentSection;
