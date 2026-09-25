import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, apiError } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { StatusIndicator } from "@/components/StatusIndicator";
import { StructuredExplanation } from "@/components/StructuredExplanation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Send, Sparkles, History as HistoryIcon, X } from "lucide-react";

const SUGGESTIONS = [
  "What is my wellbeing pattern telling you so far?",
  "Has anything changed recently that I should notice?",
  "How do my Ring signals relate to my check-ins?",
  "What is a good next step for me on Dumosense?",
];

function Bubble({ role, content, grounded_on }) {
  const isUser = role === "user";
  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")} data-testid={`ai-message-${role}`}>
      {!isUser && (
        <div className="mt-1 shrink-0">
          <CoreMark state="intelligence" size={28} />
        </div>
      )}
      <div className={cn("max-w-[82%]", isUser && "items-end")}>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-3xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-md bg-primary text-primary-foreground"
              : "rounded-tl-md border border-border bg-card text-foreground"
          )}
        >
          {content}
        </div>
        {!isUser && grounded_on?.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusIndicator classification="interpretation" label="Interpretation" />
            <span className="text-[11px] text-muted-foreground">Grounded on: {grounded_on.join(" · ")}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DumosenseAI() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [messages, setMessages] = useState([]);
  const [explanation, setExplanation] = useState(null);
  const [consentNeeded, setConsentNeeded] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const endRef = useRef(null);
  const ctxHandled = useRef(false);

  useEffect(() => {
    api.get("/ai/messages").then(({ data }) => {
      setMessages(data.messages || []);
      setLoaded(true);
    });
  }, []);

  // Contextual entry point — inherit context and show a structured explanation.
  useEffect(() => {
    const context = searchParams.get("context");
    if (!context || ctxHandled.current) return;
    ctxHandled.current = true;
    api.post("/ai/explain", { ref: context })
      .then(({ data }) => { if (data.sections) setExplanation(data); else if (data.consent_required) setConsentNeeded(true); })
      .catch(() => {});
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking, explanation]);

  const send = async (text, context) => {
    const msg = (text ?? input).trim();
    if (!msg || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setThinking(true);
    try {
      const { data } = await api.post("/ai/chat", { message: msg, context });
      setMessages((m) => [...m, data]);
    } catch (err) {
      toast.error(apiError(err.response?.data?.detail) || "Dumosense AI is unavailable right now.");
      setMessages((m) => [...m, {
        role: "assistant",
        content: "I couldn't respond just now. Please try again shortly.",
        grounded_on: [],
      }]);
    } finally {
      setThinking(false);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const openHistory = async () => {
    setShowHistory(true);
    try {
      const { data } = await api.get("/ai/history");
      setHistory(data.items || []);
    } catch {
      setHistory([]);
    }
  };

  const reopenExplanation = async (ref) => {
    setShowHistory(false);
    try {
      const { data } = await api.post("/ai/explain", { ref });
      if (data.sections) setExplanation(data);
    } catch {
      /* ignore */
    }
  };

  const empty = loaded && messages.length === 0 && !explanation;

  return (
    <div className="flex min-h-[70vh] flex-col">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex-1 rounded-3xl border border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
          Dumosense AI reflects only <span className="font-medium text-foreground">your</span> recorded
          information and clearly separates what was observed from any interpretation. It does not
          diagnose or give medical advice.
        </div>
        <button
          type="button"
          onClick={openHistory}
          data-testid="ai-history-open"
          className="inline-flex h-11 shrink-0 items-center gap-2 rounded-full border border-border bg-background-secondary px-4 text-sm text-foreground transition-colors hover:bg-surface-hover"
        >
          <HistoryIcon className="h-4 w-4" /> History
        </button>
      </div>

      {showHistory && (
        <div data-testid="ai-history" className="mb-4 rounded-3xl border border-border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="font-display text-base font-medium text-foreground">Past intelligence</p>
            <button onClick={() => setShowHistory(false)} aria-label="Close history" data-testid="ai-history-close"
              className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
          </div>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">No past questions or explanations yet.</p>
          ) : (
            <ul className="space-y-2">
              {history.map((h, i) => (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => h.type === "explanation" ? reopenExplanation(h.context) : setShowHistory(false)}
                    data-testid="ai-history-item"
                    className="w-full rounded-2xl border border-border bg-background-secondary p-3 text-left transition-colors hover:bg-surface-hover"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">{h.title}</span>
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {h.created_at ? new Date(h.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : ""}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{h.preview}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex-1 space-y-5" data-testid="ai-messages">
        {consentNeeded && (
          <div data-testid="ai-consent-needed" className="rounded-3xl border border-rose/40 bg-rose/5 p-5 text-sm text-foreground">
            To let Dumosense AI interpret your data, please enable <span className="font-medium">AI use</span> in
            Profile → Your data permissions.
          </div>
        )}
        {explanation && <StructuredExplanation data={explanation} />}
        {empty && (
          <div className="flex flex-col items-center py-8 text-center">
            <CoreMark state="learning" size={72} className="mb-5" />
            <p className="font-display text-xl font-medium text-foreground">Ask about your health picture.</p>
            <p className="mt-2 max-w-sm text-sm text-muted-foreground">
              I connect your MindGuard wellbeing and Health Reserve preparedness into one plain-language
              view.
            </p>
            <div className="mt-6 grid w-full max-w-xl gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  data-testid="ai-suggestion"
                  className="flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground transition-colors hover:bg-surface-hover"
                >
                  <Sparkles className="h-4 w-4 shrink-0 text-primary" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} content={m.content} grounded_on={m.grounded_on} />
        ))}

        {thinking && (
          <div className="flex items-center gap-3" data-testid="ai-thinking">
            <CoreMark state="learning" size={28} />
            <span className="text-sm text-muted-foreground">Reading your pattern…</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-20 mt-6 lg:bottom-4">
        <div className="flex items-end gap-2 rounded-3xl border border-border bg-card p-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask Dumosense AI about your pattern…"
            rows={1}
            data-testid="ai-input"
            className="max-h-32 min-h-[44px] resize-none border-0 bg-transparent text-base focus-visible:ring-0"
          />
          <Button
            onClick={() => send()}
            disabled={thinking || !input.trim()}
            data-testid="ai-send"
            className="h-11 w-11 shrink-0 rounded-full bg-primary p-0 text-primary-foreground hover:opacity-90"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
