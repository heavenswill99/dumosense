import { useState } from "react";
import { api } from "@/lib/api";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CoreMark } from "@/components/CoreMark";
import { HelpCircle } from "lucide-react";

/**
 * "Why am I seeing this?" — surfaces plain-language provenance for an
 * intelligence item, honouring the Dumosense provenance principle.
 */
export function WhyPopover({ refKey = "pattern", label = "Why am I seeing this?" }) {
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async (open) => {
    if (open && text == null && !loading) {
      setLoading(true);
      try {
        const { data } = await api.get(`/ai/why?ref=${encodeURIComponent(refKey)}`);
        setText(data.explanation);
      } catch {
        setText("This is based only on information you have recorded or authorised within Dumosense.");
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <Popover onOpenChange={load}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={`why-${refKey}`}
          className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          {label}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 rounded-2xl border-border bg-popover p-4" data-testid="why-content">
        <div className="mb-2 flex items-center gap-2">
          <CoreMark state="static" size={20} />
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Provenance</span>
        </div>
        <p className="text-sm leading-relaxed text-foreground">
          {loading ? "Explaining…" : text}
        </p>
      </PopoverContent>
    </Popover>
  );
}

export default WhyPopover;
