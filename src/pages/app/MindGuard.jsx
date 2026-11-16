import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiError } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { EmptyState } from "@/components/EmptyState";
import { StatusIndicator } from "@/components/StatusIndicator";
import { Button } from "@/components/ui/button";
import { DATA_STATES } from "@/lib/domains";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const COG_ITEMS = [
  {
    key: "clarity",
    question: "How clear did your thinking feel today?",
    low: "Not clear",
    high: "Very clear",
  },
  {
    key: "memory",
    question: "How easy was it to remember everyday things today?",
    low: "Very difficult",
    high: "Very easy",
  },
  {
    key: "focus",
    question: "How easy was it to focus on what you needed to do today?",
    low: "Not easy",
    high: "Very easy",
  },
];

const WELLBEING_ITEMS = [
  {
    key: "sleep",
    question: "How well did you sleep last night?",
    low: "Not well",
    high: "Very well",
  },
  {
    key: "stress",
    question: "How stressed do you feel now?",
    low: "Not stressed",
    high: "Very stressed",
  },
  {
    key: "fatigue",
    question: "How mentally tired do you feel?",
    low: "Not tired",
    high: "Very tired",
  },
  {
    key: "focus",
    question: "How focused do you feel now?",
    low: "Not focused",
    high: "Very focused",
  },
  {
    key: "mood",
    question: "How is your mood today?",
    low: "Very low",
    high: "Very good",
  },
];

function RatingQuestions({ items, values, onChange, testPrefix }) {
  return (
    <div className="mt-5 space-y-5">
      {items.map((item) => (
        <div key={item.key}>
          <p className="mb-2 text-sm font-medium text-foreground">{item.question}</p>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => onChange(item.key, value)}
                data-testid={`${testPrefix}-${item.key}-${value}`}
                aria-label={`${item.question} ${value} of 5`}
                aria-pressed={values[item.key] === value}
                className={`h-10 flex-1 rounded-xl border text-sm transition-colors ${
                  values[item.key] === value
                    ? "border-rose bg-rose text-white"
                    : "border-border bg-background-secondary text-foreground hover:border-rose"
                }`}
              >
                {value}
              </button>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>1 · {item.low}</span>
            <span>5 · {item.high}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MindGuard({ previewMode = false }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [pageError, setPageError] = useState("");
  const [hasDataConsent, setHasDataConsent] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentError, setConsentError] = useState("");
  const [wellbeing, setWellbeing] = useState({
    sleep: 0,
    stress: 0,
    fatigue: 0,
    focus: 0,
    mood: 0,
  });
  const [cog, setCog] = useState({ clarity: 0, memory: 0, focus: 0 });
  const [saving, setSaving] = useState(false);
  const [wellbeingSavedOpen, setWellbeingSavedOpen] = useState(false);

  const load = () => {
    api.get("/home")
      .then(({ data: response }) => {
        setData(response.insights.mindguard);
        setPageError("");
      })
      .catch((error) => {
        setPageError(apiError(error) || "Could not load your MindGuard data.");
        setData({ state: "no_data", count: 0 });
      });
    api.get("/mindguard/consent/")
      .then(({ data: response }) => {
        setHasDataConsent(response.granted);
        setConsentError("");
      })
      .catch((error) => {
        setConsentError(apiError(error) || "Could not check your data consent.");
      });
  };
  useEffect(() => {
    if (previewMode) {
      setData({ state: "no_data", count: 0 });
      setHasDataConsent(false);
      return;
    }
    load();
  }, [previewMode]);

  const ensureConsent = async () => {
    if (hasDataConsent) return true;
    if (!consentChecked) {
      setConsentError("Please agree before saving these reflections.");
      return false;
    }

    try {
      await api.post("/mindguard/consent/", { accepted: true });
      setHasDataConsent(true);
      setConsentChecked(false);
      setConsentError("");
      return true;
    } catch (error) {
      setConsentError(apiError(error) || "Could not save your consent.");
      return false;
    }
  };

  const saveReflection = async (type, items, values, onSaved) => {
    if (items.some((item) => !values[item.key])) {
      toast.error("Please answer every question.");
      return;
    }
    if (previewMode || pageError || consentError) {
      toast("Frontend preview only — your reflection was not saved.");
      return;
    }

    setSaving(true);
    try {
      if (!(await ensureConsent())) return;

      const answers = items.map((item) => ({
        question: item.question,
        value: values[item.key],
      }));
      await api.post(`/mindguard/reflections/${type}/`, {
        answers,
        question_set_version: "v1",
        timestamp: new Date().toISOString(),
      });
      if (type === "wellbeing_checkin") {
        setWellbeingSavedOpen(true);
      } else {
        toast.success("Your reflection was saved to your account.");
      }
      onSaved();
      load();
    } catch (error) {
      toast.error(apiError(error) || "Could not save your reflection.");
    } finally {
      setSaving(false);
    }
  };

  if (!data && !pageError) return <Skeleton className="h-64 w-full rounded-3xl" />;
  const state = DATA_STATES[data.state] || DATA_STATES.no_data;
  const isPreviewOnly = previewMode || Boolean(pageError || consentError);

  return (
    <div className="space-y-8">
      {isPreviewOnly && (
        <div role="status" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm leading-relaxed text-muted-foreground">
          <p className="font-medium text-foreground">Frontend preview</p>
          <p className="mt-1">
            {previewMode
              ? "MindGuard is open in preview mode. Your answers are not sent or saved."
              : `MindGuard is showing its frontend because the service is unavailable. ${pageError || consentError} Your answers will not be sent.`}
          </p>
        </div>
      )}
      <section className="flex items-start gap-4 rounded-3xl border border-border bg-card p-6">
        <CoreMark state={state.core} size={56} />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Cognitive & wellbeing</p>
          <p className="mt-2 font-display text-lg font-medium text-foreground">{state.title}</p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{state.body}</p>
          {data.count > 0 && (
            <div className="mt-3 flex items-center gap-2">
              <StatusIndicator classification="observed" />
              <span className="text-xs text-muted-foreground">{data.count} reflections saved to your account</span>
            </div>
          )}
        </div>
      </section>

      {!hasDataConsent && !isPreviewOnly && (
        <section className="rounded-2xl border border-border bg-card p-5" data-testid="mindguard-consent">
          <label className="flex cursor-pointer items-start gap-3 text-sm leading-relaxed text-muted-foreground">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(event) => {
                setConsentChecked(event.target.checked);
                setConsentError("");
              }}
              className="mt-1"
              data-testid="mindguard-consent-checkbox"
            />
            <span>
              I agree to send my MindGuard self-reported answers securely to the backend for processing.
              Individual answers will not be displayed here, and these reflections are not a clinical assessment.
            </span>
          </label>
          {consentError && <p role="alert" className="mt-2 text-sm text-error">{consentError}</p>}
        </section>
      )}

      <section id="mindguard-cognitive" className="rounded-3xl border border-border bg-card p-6" data-testid="mindguard-cognitive">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-medium text-foreground">Cognitive reflection</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Think about how these everyday moments felt for you today. There are no right or wrong answers.
            </p>
          </div>
          <StatusIndicator classification="observed" label="Observed" />
        </div>
        <RatingQuestions
          items={COG_ITEMS}
          values={cog}
          onChange={(key, value) => setCog((current) => ({ ...current, [key]: value }))}
          testPrefix="cog"
        />
        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => saveReflection(
              "cognitive_checkin",
              COG_ITEMS,
              cog,
              () => setCog({ clarity: 0, memory: 0, focus: 0 }),
            )}
            disabled={saving}
            data-testid="cog-submit"
            className="rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90"
          >
            Record reflection
          </Button>
        </div>
      </section>

      <section className="rounded-3xl border border-border bg-card p-6" data-testid="mindguard-wellbeing">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-medium text-foreground">Wellbeing check-in</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Take a moment to reflect on how things feel today. Choose a number from 1 to 5 for each question.
            </p>
          </div>
          <StatusIndicator classification="observed" label="Observed" />
        </div>
        <RatingQuestions
          items={WELLBEING_ITEMS}
          values={wellbeing}
          onChange={(key, value) => setWellbeing((current) => ({ ...current, [key]: value }))}
          testPrefix="wellbeing"
        />
        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => saveReflection(
              "wellbeing_checkin",
              WELLBEING_ITEMS,
              wellbeing,
              () => setWellbeing({
                sleep: 0,
                stress: 0,
                fatigue: 0,
                focus: 0,
                mood: 0,
              }),
            )}
            disabled={saving}
            data-testid="wellbeing-submit"
            className="rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90"
          >
            Save wellbeing check-in
          </Button>
        </div>
      </section>

      {data.count === 0 && (
        <EmptyState
          testid="mindguard-empty"
          state="no_data"
          title="No reflections saved yet."
          body={isPreviewOnly
            ? "This frontend preview contains no saved reflections. Individual answers are not sent or stored in preview mode."
            : "Your check-ins are sent securely to the backend for processing. Individual answers are not displayed here."}
        />
      )}

      <Dialog open={wellbeingSavedOpen} onOpenChange={setWellbeingSavedOpen}>
        <DialogContent data-testid="wellbeing-saved-dialog" className="rounded-3xl border-border bg-card">
          <DialogHeader>
            <DialogTitle className="font-display text-xl font-medium text-foreground">
              Wellbeing check-in saved
            </DialogTitle>
            <DialogDescription>
              Your check-in was received. Continue with a cognitive reflection or return to your dashboard.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-end">
            <Button
              type="button"
              variant="outline"
              data-testid="wellbeing-back-home"
              className="rounded-full border-border bg-transparent"
              onClick={() => {
                setWellbeingSavedOpen(false);
                navigate("/app");
              }}
            >
              Back Home
            </Button>
            <Button
              type="button"
              data-testid="wellbeing-take-assessment"
              className="rounded-full bg-primary text-primary-foreground"
              onClick={() => {
                setWellbeingSavedOpen(false);
                document.getElementById("mindguard-cognitive")?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                });
              }}
            >
              Take Assessment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
