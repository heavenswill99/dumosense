import { useEffect, useRef, useState } from "react";
import { api, apiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Bot, Send, X } from "lucide-react";

const WELCOME_MESSAGE = {
  role: "assistant",
  content: "Hi! I can help with Dumosense features and general wellbeing questions. I don't access your personal health records.",
};

export default function SiteChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, open]);

  const send = async (event) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setInput("");
    setMessages((current) => [...current, { role: "user", content: message }]);
    setSending(true);

    try {
      const { data } = await api.post("/ai/chat", { message });
      setMessages((current) => [...current, data]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: apiError(error) || "I couldn't respond just now. Please try again.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed bottom-24 right-4 z-[60]" data-testid="site-chatbot">
      {open && (
        <section
          id="site-chatbot-panel"
          role="dialog"
          aria-label="Dumosense chatbot"
          className="absolute bottom-16 right-0 flex h-[min(34rem,calc(100vh-11rem))] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-3xl border border-border bg-background shadow-2xl"
        >
          <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
            <div>
              <h2 className="font-display text-base font-medium text-foreground">Dumosense Assistant</h2>
              <p className="text-xs text-muted-foreground">General site and wellbeing guidance</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chatbot"
              data-testid="site-chatbot-close"
              className="rounded-full p-2 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              return (
                <div
                  key={`${message.role}-${index}`}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <p
                    className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                      isUser
                        ? "rounded-br-md bg-primary text-primary-foreground"
                        : "rounded-bl-md border border-border bg-card text-foreground"
                    }`}
                  >
                    {message.content}
                  </p>
                </div>
              );
            })}
            {sending && (
              <p className="text-xs text-muted-foreground" data-testid="site-chatbot-thinking">
                Thinking…
              </p>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={send} className="border-t border-border bg-card p-3">
            <div className="flex items-end gap-2">
              <Textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Ask a question…"
                rows={1}
                maxLength={2000}
                aria-label="Message Dumosense Assistant"
                data-testid="site-chatbot-input"
                className="max-h-24 min-h-10 resize-none border-0 bg-background focus-visible:ring-0"
              />
              <Button
                type="submit"
                disabled={sending || !input.trim()}
                aria-label="Send message"
                data-testid="site-chatbot-send"
                className="h-10 w-10 shrink-0 rounded-full bg-primary p-0 text-primary-foreground"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
              Don’t share sensitive details. This assistant doesn’t diagnose or access personal records.
            </p>
          </form>
        </section>
      )}

      <Button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="site-chatbot-panel"
        aria-label={open ? "Close Dumosense chatbot" : "Chat with Dumosense"}
        data-testid="site-chatbot-toggle"
        className="h-14 w-14 rounded-full bg-primary p-0 text-primary-foreground shadow-lg hover:opacity-90"
      >
        {open ? (
          <X className="h-5 w-5" />
        ) : (
          <Bot className="h-6 w-6" />
        )}
      </Button>
    </div>
  );
}
