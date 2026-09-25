import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * FormField — labelled input with accessible error messaging (non-colour-only).
 */
export function FormField({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  error,
  helper,
  autoComplete,
  required,
  testid,
  children,
}) {
  const describedBy = error ? `${id}-error` : helper ? `${id}-helper` : undefined;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <Label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
          {required && <span className="ml-0.5 text-muted-foreground">*</span>}
        </Label>
      )}
      {children || (
        <Input
          id={id}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          data-testid={testid}
          className={cn(
            "h-12 rounded-xl border-border bg-background-secondary text-base focus-visible:ring-2 focus-visible:ring-ring/50",
            error && "border-error focus-visible:ring-error/40"
          )}
        />
      )}
      {helper && !error && (
        <p id={`${id}-helper`} className="text-xs text-muted-foreground">
          {helper}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="flex items-center gap-1 text-xs font-medium text-error">
          <span aria-hidden>▲</span>
          {error}
        </p>
      )}
    </div>
  );
}

export default FormField;
