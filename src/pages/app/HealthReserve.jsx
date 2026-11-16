import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  CircleAlert,
  FileText,
  HeartPulse,
  LockKeyhole,
  ShieldCheck,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { healthReserveApi } from "@/features/health-reserve/healthReserveApi";

const CONSENT_TYPE = "health_reserve_data";
const CONSENT_PURPOSE =
  "Use your Health Reserve assessment details to calculate and store preparedness estimates.";
const CONSENT_VERSION = "1.00";
const PRIVATE_VIEWS = new Set([
  "assessment",
  "results",
  "dashboard",
  "progress",
  "history",
  "financial-profile",
  "dependents",
  "privacy",
]);
const VALID_VIEWS = new Set([...PRIVATE_VIEWS, "overview", "consent", "results"]);
const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: HeartPulse },
  { id: "assessment", label: "Assessment", icon: FileText },
  { id: "dashboard", label: "Dashboard", icon: Wallet },
  { id: "progress", label: "Progress", icon: TrendingUp },
  { id: "history", label: "History", icon: FileText },
  { id: "financial-profile", label: "Financial profile", icon: ShieldCheck },
  { id: "dependents", label: "Dependents", icon: Users },
  { id: "privacy", label: "Privacy", icon: LockKeyhole },
];

function listFromResponse(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  throw new Error("The server returned an unexpected list response.");
}

function errorMessage(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const firstValue = Object.values(data).find((value) => value !== undefined);
    if (typeof firstValue === "string") return firstValue;
    if (Array.isArray(firstValue) && typeof firstValue[0] === "string") {
      return firstValue[0];
    }
  }
  return error?.message || "Something went wrong. Please try again.";
}

function formatMoney(value, currency) {
  if (value === null || value === undefined || value === "") return "Not provided";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  if (currency) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: String(currency).toUpperCase(),
        maximumFractionDigits: 2,
      }).format(amount);
    } catch (error) {
      if (!(error instanceof RangeError)) throw error;
    }
  }
  return amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatDate(value) {
  if (!value) return "Date not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date not available"
    : date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
}

function Panel({ children, className = "" }) {
  return (
    <section className={`rounded-3xl border border-border bg-card p-5 shadow-sm sm:p-7 ${className}`}>
      {children}
    </section>
  );
}

function PageTitle({ eyebrow = "HEALTH RESERVE", title, description, children }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-2 font-display text-2xl font-medium text-foreground sm:text-3xl">{title}</h2>
        {description && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {children}
    </div>
  );
}

function Notice({ tone = "info", title, children, action }) {
  const tones = {
    info: "border-primary/20 bg-primary/5 text-foreground",
    error: "border-destructive/30 bg-destructive/5 text-foreground",
    success: "border-emerald-500/25 bg-emerald-500/5 text-foreground",
    warning: "border-amber-500/30 bg-amber-500/5 text-foreground",
  };
  return (
    <div className={`rounded-2xl border p-4 ${tones[tone] || tones.info}`} role={tone === "error" ? "alert" : "status"}>
      <div className="flex items-start gap-3">
        <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          {title && <p className="font-medium">{title}</p>}
          <div className="mt-1 text-sm leading-relaxed text-muted-foreground">{children}</div>
          {action && <div className="mt-3">{action}</div>}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ title, children, action }) {
  return (
    <Panel className="text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <HeartPulse className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="mt-4 font-display text-lg font-medium text-foreground">{title}</h3>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">{children}</p>
      {action && <div className="mt-5">{action}</div>}
    </Panel>
  );
}

function Metric({ label, value, detail }) {
  return (
    <div className="rounded-2xl border border-border bg-background/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 break-words font-display text-xl font-medium text-foreground">{value}</p>
      {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}

function ErrorState({ title = "We couldn't load this information", message, onRetry }) {
  return (
    <Notice
      tone="error"
      title={title}
      action={onRetry ? (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    >
      {message}
    </Notice>
  );
}

function LoadingState() {
  return (
    <div className="space-y-5" aria-label="Loading Health Reserve">
      <Skeleton className="h-28 w-full rounded-3xl" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-32 rounded-3xl" />
        <Skeleton className="h-32 rounded-3xl" />
        <Skeleton className="h-32 rounded-3xl" />
      </div>
    </div>
  );
}

function ConsentView({ consent, saving, error, previewMode, onGrant, onBack }) {
  const [accepted, setAccepted] = useState(false);
  const isGranted = consent?.status === "granted";

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageTitle
        eyebrow="PRIVACY & PERMISSION"
        title="Your Health Reserve data"
        description="Review how your information is used before opening or submitting a Health Reserve assessment."
      />
      {isGranted ? (
        <Notice tone="success" title="Health Reserve consent is active">
          You can review or withdraw this permission at any time from Privacy settings.
        </Notice>
      ) : (
        <Panel>
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="font-display text-lg font-medium text-foreground">Consent is required</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Health Reserve information is private. We need your permission before loading or storing this section's assessment data.
              </p>
            </div>
          </div>
          <div className="mt-5 rounded-2xl bg-background/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Purpose</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground">{CONSENT_PURPOSE}</p>
            <p className="mt-3 text-xs text-muted-foreground">Consent version {CONSENT_VERSION}</p>
          </div>
          {previewMode && (
            <div className="mt-4">
              <Notice title="Preview only">Consent can’t be recorded in frontend preview mode.</Notice>
            </div>
          )}
          <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-relaxed text-foreground">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
              className="mt-1 h-4 w-4 rounded border-border accent-primary"
            />
            <span>I understand and agree to the Health Reserve data use described above.</span>
          </label>
          {error && <div className="mt-4"><ErrorState title="Consent was not saved" message={error} /></div>}
          <div className="mt-5 flex flex-wrap gap-3">
            <Button type="button" onClick={onGrant} disabled={!accepted || saving || previewMode} className="rounded-full">
              {previewMode ? "Preview only" : saving ? "Saving..." : "Agree and continue"}
              {!saving && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
            </Button>
            <Button type="button" variant="outline" onClick={onBack} disabled={saving} className="rounded-full">
              Back to overview
            </Button>
          </div>
        </Panel>
      )}
      {isGranted && (
        <Panel>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Your permission is recorded for Health Reserve only. You can continue to your assessment, or return to the overview.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button type="button" onClick={onGrant} disabled={saving} className="rounded-full">
              Continue to Health Reserve <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" onClick={onBack} className="rounded-full">Back to overview</Button>
          </div>
        </Panel>
      )}
    </div>
  );
}

const FORM_STEPS = [
  { title: "Coverage & health costs", fields: ["healthcare_coverage_status", "estimated_healthcare_exposure", "emergency_health_resources"] },
  { title: "Commitments", fields: ["monthly_financial_obligations", "number_of_dependants"] },
  { title: "Your reserve target", fields: ["current_preparedness_amount", "preparedness_target"] },
];

const FIELD_CONFIG = {
  healthcare_coverage_status: {
    label: "Healthcare coverage status",
    hint: "For example: insured, partially covered, uninsured, or not sure.",
    type: "text",
  },
  estimated_healthcare_exposure: {
    label: "Estimated healthcare costs you may need to cover",
    hint: "Enter a non-negative amount in your local currency.",
    type: "number",
    min: "0",
    step: "0.01",
  },
  emergency_health_resources: {
    label: "Emergency health resources available",
    hint: "Funds or resources you could use for an unexpected health cost.",
    type: "number",
    min: "0",
    step: "0.01",
  },
  monthly_financial_obligations: {
    label: "Monthly financial obligations",
    hint: "Your regular monthly commitments, in your local currency.",
    type: "number",
    min: "0",
    step: "0.01",
  },
  number_of_dependants: {
    label: "Number of dependants",
    hint: "Enter a whole number, including 0 if you have none.",
    type: "number",
    min: "0",
    step: "1",
  },
  current_preparedness_amount: {
    label: "Amount currently set aside",
    hint: "Your current Health Reserve amount, in your local currency.",
    type: "number",
    min: "0",
    step: "0.01",
  },
  preparedness_target: {
    label: "Your preparedness target",
    hint: "Choose a target greater than zero. Automatic recommendations are not available.",
    type: "number",
    min: "0.01",
    step: "0.01",
  },
};

function AssessmentForm({ saving, error, previewMode, onSubmit, onCancel }) {
  const [step, setStep] = useState(0);
  const [values, setValues] = useState({
    healthcare_coverage_status: "",
    estimated_healthcare_exposure: "",
    emergency_health_resources: "",
    monthly_financial_obligations: "",
    number_of_dependants: "",
    current_preparedness_amount: "",
    preparedness_target: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const isReview = step === FORM_STEPS.length;

  const updateValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  };

  const validateStep = () => {
    const currentErrors = {};
    FORM_STEPS[step].fields.forEach((name) => {
      const value = values[name].trim();
      if (!value) {
        currentErrors[name] = "This field is required.";
      } else if (name === "number_of_dependants") {
        if (!/^\d+$/.test(value)) currentErrors[name] = "Enter a whole number of 0 or more.";
      } else if (name !== "healthcare_coverage_status") {
        const amount = Number(value);
        if (!Number.isFinite(amount) || amount < 0 || (name === "preparedness_target" && amount === 0)) {
          currentErrors[name] = name === "preparedness_target"
            ? "Enter a target greater than zero."
            : "Enter a valid amount of 0 or more.";
        }
      }
    });
    setFieldErrors(currentErrors);
    return Object.keys(currentErrors).length === 0;
  };

  const submit = () => {
    onSubmit({
      target_mode: "manual",
      healthcare_coverage_status: values.healthcare_coverage_status.trim(),
      estimated_healthcare_exposure: values.estimated_healthcare_exposure,
      emergency_health_resources: values.emergency_health_resources,
      monthly_financial_obligations: values.monthly_financial_obligations,
      number_of_dependants: Number(values.number_of_dependants),
      current_preparedness_amount: values.current_preparedness_amount,
      preparedness_target: values.preparedness_target,
    });
  };

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle
        title="Health Reserve assessment"
        description="Answer a few questions to record your current preparedness. You can review everything before sending it."
      />
      <Panel>
        <div className="mb-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium text-foreground">
              {isReview ? "Review your answers" : `Step ${step + 1} of ${FORM_STEPS.length}`}
            </p>
            <p className="text-xs text-muted-foreground">{isReview ? "Final check" : FORM_STEPS[step].title}</p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${((step + 1) / (FORM_STEPS.length + 1)) * 100}%` }}
            />
          </div>
        </div>
        {previewMode && (
          <div className="mb-5">
            <Notice title="Frontend preview">You can review the assessment flow, but submissions are disabled and no answers are saved.</Notice>
          </div>
        )}

        {!isReview ? (
          <div className="space-y-5">
            {FORM_STEPS[step].fields.map((name) => {
              const config = FIELD_CONFIG[name];
              return (
                <div key={name}>
                  <label htmlFor={`health-reserve-${name}`} className="text-sm font-medium text-foreground">
                    {config.label}
                  </label>
                  <input
                    id={`health-reserve-${name}`}
                    type={config.type}
                    min={config.min}
                    step={config.step}
                    value={values[name]}
                    onChange={(event) => updateValue(name, event.target.value)}
                    aria-invalid={Boolean(fieldErrors[name])}
                    aria-describedby={`health-reserve-${name}-hint${fieldErrors[name] ? ` health-reserve-${name}-error` : ""}`}
                    className="mt-2 h-11 w-full rounded-xl border border-input bg-background px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <p id={`health-reserve-${name}-hint`} className="mt-1.5 text-xs text-muted-foreground">{config.hint}</p>
                  {fieldErrors[name] && (
                    <p id={`health-reserve-${name}-error`} className="mt-1 text-xs text-destructive">{fieldErrors[name]}</p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {Object.entries(FIELD_CONFIG).map(([name, config]) => (
              <div key={name} className="flex flex-col gap-1 py-3 sm:flex-row sm:justify-between sm:gap-6">
                <span className="text-sm text-muted-foreground">{config.label}</span>
                <span className="break-all text-sm font-medium text-foreground">{values[name]}</span>
              </div>
            ))}
          </div>
        )}

        {error && <div className="mt-5"><ErrorState title="Assessment was not saved" message={error} /></div>}
        <div className="mt-6 flex flex-wrap justify-between gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => (step === 0 ? onCancel() : setStep((current) => current - 1))}
            disabled={saving}
            className="rounded-full"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {step === 0 ? "Cancel" : "Back"}
          </Button>
          {isReview ? (
            <Button type="button" onClick={submit} disabled={saving || previewMode} className="rounded-full">
              {previewMode ? "Preview only" : saving ? "Saving..." : "Submit assessment"}
              {!saving && !previewMode && <Check className="h-4 w-4" aria-hidden="true" />}
            </Button>
          ) : (
            <Button type="button" onClick={() => validateStep() && setStep((current) => current + 1)} className="rounded-full">
              Continue <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </Panel>
      <p className="mt-4 text-center text-xs leading-relaxed text-muted-foreground">
        {previewMode
          ? "This preview does not send or save assessment answers."
          : "Your assessment is sent securely to the Health Reserve service. Results shown here are returned by the service."}
      </p>
    </div>
  );
}

function AssessmentSummary({ assessment, currency }) {
  const ratio = Number(assessment?.preparedness_ratio);
  const percentage = Number.isFinite(ratio) ? Math.round(ratio * 100) : null;
  const targetMet = assessment?.reserve_status === "target_met";
  return (
    <Panel>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Assessment result</p>
          <h3 className="mt-2 font-display text-xl font-medium text-foreground">
            {targetMet ? "Your target is met" : "Your reserve is below target"}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">Assessed {formatDate(assessment.assessed_at)}</p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-xs font-medium ${targetMet ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "bg-amber-500/10 text-amber-700 dark:text-amber-300"}`}>
          {targetMet ? "Target met" : "In progress"}
        </span>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Current reserve" value={formatMoney(assessment.current_preparedness_amount, currency)} />
        <Metric label="Preparedness target" value={formatMoney(assessment.preparedness_target, currency)} />
        <Metric label="Remaining gap" value={formatMoney(assessment.preparedness_gap, currency)} />
      </div>
      {percentage !== null && (
        <div className="mt-5">
          <div className="flex justify-between gap-3 text-sm">
            <span className="text-muted-foreground">Progress toward target</span>
            <span className="font-medium text-foreground">{percentage}%</span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Preparedness progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.max(0, Math.min(100, percentage))}
          >
            <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function OverviewView({ assessments, progress, currency, errors, onRetry, onNavigate }) {
  const latest = assessments[0];
  return (
    <div className="space-y-6">
      <PageTitle
        title="Prepare for health costs"
        description="Health Reserve helps you record the resources you have set aside and track your progress toward a target."
      >
        <Button type="button" onClick={() => onNavigate("assessment")} className="w-fit rounded-full">
          Start assessment <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </PageTitle>
      {errors.assessments ? (
        <ErrorState message={errors.assessments} onRetry={onRetry} />
      ) : latest ? (
        <>
          <AssessmentSummary assessment={latest} currency={currency} />
          <div className="grid gap-4 sm:grid-cols-3">
            <Metric label="Assessments recorded" value={progress?.assessment_count ?? assessments.length} />
            <Metric label="Current reserve" value={formatMoney(latest.current_preparedness_amount, currency)} />
            <Metric label="Current gap" value={formatMoney(latest.preparedness_gap, currency)} />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" variant="outline" onClick={() => onNavigate("dashboard")} className="rounded-full">
              Open dashboard <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" onClick={() => onNavigate("history")} className="rounded-full">
              View assessment history
            </Button>
          </div>
        </>
      ) : (
        <EmptyState
          title="Your Health Reserve starts here"
          action={<Button type="button" onClick={() => onNavigate("assessment")} className="rounded-full">Start an assessment</Button>}
        >
          No assessment has been recorded yet. Start one when you are ready; your results will appear here after the service saves them.
        </EmptyState>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel>
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
            <h3 className="font-medium text-foreground">Your information stays yours</h3>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Health Reserve data is only loaded after you grant consent. You can withdraw that consent in Privacy settings.
          </p>
        </Panel>
        <Panel>
          <div className="flex items-center gap-3">
            <TrendingUp className="h-5 w-5 text-primary" aria-hidden="true" />
            <h3 className="font-medium text-foreground">Progress uses your assessments</h3>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Charts and summaries are based on assessment records returned by the Health Reserve service.
          </p>
        </Panel>
      </div>
    </div>
  );
}

function DashboardView({ assessments, progress, currency, errors, onRetry, onNavigate }) {
  const latest = assessments[0];
  return (
    <div className="space-y-6">
      <PageTitle title="Your Health Reserve dashboard" description="A snapshot of your latest saved assessment and progress." />
      {errors.assessments ? (
        <ErrorState message={errors.assessments} onRetry={onRetry} />
      ) : !latest ? (
        <EmptyState title="No dashboard data yet" action={<Button type="button" onClick={() => onNavigate("assessment")} className="rounded-full">Create an assessment</Button>}>
          Your dashboard will show your reserve, target, and progress after your first assessment is saved.
        </EmptyState>
      ) : (
        <>
          <AssessmentSummary assessment={latest} currency={currency} />
          {errors.progress ? (
            <Notice tone="warning" title="Progress summary unavailable">
              {errors.progress}
            </Notice>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Assessments" value={progress?.assessment_count ?? assessments.length} />
              <Metric label="First recorded" value={formatDate(progress?.first_assessment_date)} />
              <Metric label="Reserve change" value={progress ? formatMoney(progress.amount_change, currency) : "Not available"} />
              <Metric label="Target change" value={progress ? formatMoney(progress.target_change, currency) : "Not available"} />
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <Button type="button" variant="outline" onClick={() => onNavigate("progress")} className="rounded-full">View progress</Button>
            <Button type="button" variant="outline" onClick={() => onNavigate("history")} className="rounded-full">View history</Button>
          </div>
        </>
      )}
    </div>
  );
}

function ProgressChart({ assessments, currency }) {
  if (!assessments.length) {
    return <EmptyState title="Not enough data for a progress chart">A chart will appear after at least one saved assessment.</EmptyState>;
  }
  const amounts = assessments.map((item) => Number(item.current_preparedness_amount)).filter(Number.isFinite);
  if (!amounts.length) return <Notice tone="warning" title="Progress chart unavailable">The saved assessments do not contain usable reserve amounts.</Notice>;

  const minimum = Math.min(...amounts);
  const maximum = Math.max(...amounts);
  const range = maximum - minimum || 1;
  const points = assessments
    .map((item, index) => {
      const amount = Number(item.current_preparedness_amount);
      if (!Number.isFinite(amount)) return null;
      const x = assessments.length === 1 ? 50 : 8 + (index / (assessments.length - 1)) * 84;
      const y = 90 - ((amount - minimum) / range) * 76;
      return `${x},${y}`;
    })
    .filter(Boolean)
    .join(" ");

  return (
    <Panel>
      <h3 className="font-display text-lg font-medium text-foreground">Reserve amount over time</h3>
      <p className="mt-1 text-sm text-muted-foreground">Each point represents an assessment saved by you.</p>
      <div className="mt-5">
        <svg viewBox="0 0 100 100" className="h-52 w-full overflow-visible" role="img" aria-label="Chart of saved reserve amounts over time">
          <line x1="5" y1="90" x2="95" y2="90" stroke="currentColor" className="text-border" strokeWidth="0.7" />
          {points && <polyline points={points} fill="none" stroke="currentColor" className="text-primary" strokeWidth="2" vectorEffect="non-scaling-stroke" />}
          {assessments.map((item, index) => {
            const amount = Number(item.current_preparedness_amount);
            if (!Number.isFinite(amount)) return null;
            const x = assessments.length === 1 ? 50 : 8 + (index / (assessments.length - 1)) * 84;
            const y = 90 - ((amount - minimum) / range) * 76;
            return <circle key={item.reserve_assessment_id || `${item.assessed_at}-${index}`} cx={x} cy={y} r="1.8" fill="currentColor" className="text-primary" />;
          })}
        </svg>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{formatMoney(minimum, currency)}</span>
          <span>{formatMoney(maximum, currency)}</span>
        </div>
      </div>
    </Panel>
  );
}

function ProgressView({ assessments, progress, currency, errors, onRetry }) {
  return (
    <div className="space-y-6">
      <PageTitle title="Your progress" description="Track changes between real assessment records. No values are estimated for this chart." />
      {errors.progress ? (
        <ErrorState message={errors.progress} onRetry={onRetry} />
      ) : progress ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Assessments" value={progress.assessment_count ?? 0} />
          <Metric label="Reserve change" value={formatMoney(progress.amount_change, currency)} />
          <Metric label="Target change" value={formatMoney(progress.target_change, currency)} />
          <Metric label="Current gap" value={formatMoney(progress.current_gap, currency)} />
        </div>
      ) : null}
      {errors.assessments ? (
        <ErrorState message={errors.assessments} onRetry={onRetry} />
      ) : <ProgressChart assessments={[...assessments].reverse()} currency={currency} />}
      {progress?.message && <p className="text-sm text-muted-foreground">{progress.message}</p>}
    </div>
  );
}

function HistoryView({ assessments, currency, error, onRetry, onNavigate }) {
  return (
    <div className="space-y-6">
      <PageTitle title="Assessment history" description="Review your saved Health Reserve assessments." />
      {error ? <ErrorState message={error} onRetry={onRetry} /> : assessments.length === 0 ? (
        <EmptyState title="No assessments to show" action={<Button type="button" onClick={() => onNavigate("assessment")} className="rounded-full">Start an assessment</Button>}>
          Saved assessments will appear here.
        </EmptyState>
      ) : (
        <Panel className="overflow-hidden p-0">
          <div className="divide-y divide-border">
            {assessments.map((assessment) => (
              <div key={assessment.reserve_assessment_id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-foreground">{formatDate(assessment.assessed_at)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {assessment.reserve_assessment_id || "Assessment"} · {assessment.reserve_status === "target_met" ? "Target met" : "Below target"}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm sm:min-w-72">
                  <div><p className="text-xs text-muted-foreground">Current reserve</p><p className="mt-1 font-medium">{formatMoney(assessment.current_preparedness_amount, currency)}</p></div>
                  <div><p className="text-xs text-muted-foreground">Remaining gap</p><p className="mt-1 font-medium">{formatMoney(assessment.preparedness_gap, currency)}</p></div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

const PROFILE_FIELDS = [
  ["income_type", "Income type"],
  ["employment_status", "Employment status"],
  ["monthly_income", "Monthly income", true],
  ["essential_monthly_expenses", "Essential monthly expenses", true],
  ["debt_repayments", "Debt repayments", true],
  ["other_monthly_obligations", "Other monthly obligations", true],
  ["existing_liquid_savings", "Existing liquid savings", true],
  ["income_stability_index", "Income stability index"],
  ["currency_code", "Currency"],
  ["country_code", "Country"],
  ["region_code", "Region"],
  ["data_source", "Data source"],
  ["effective_from", "Effective from", false, true],
  ["effective_to", "Effective to", false, true],
  ["recorded_at", "Recorded at", false, true],
];

function FinancialProfileView({ profiles, error, onRetry }) {
  const profile = profiles[0];
  return (
    <div className="space-y-6">
      <PageTitle title="Financial profile" description="This is a read-only view of financial profile data returned by the service." />
      {error ? <ErrorState message={error} onRetry={onRetry} /> : !profile ? (
        <EmptyState title="No financial profile available">The service has not returned a financial profile for your account.</EmptyState>
      ) : (
        <>
          <Notice title="Read-only information">Profile values are displayed as received. Editing and saving a financial profile are not supported here.</Notice>
          <Panel>
            <div className="grid gap-x-8 sm:grid-cols-2">
              {PROFILE_FIELDS.map(([key, label, isMoney, isDate]) => {
                const value = profile[key];
                if (value === null || value === undefined || value === "") return null;
                const formatted = isMoney
                  ? formatMoney(value, profile.currency_code)
                  : isDate ? formatDate(value) : String(value);
                return (
                  <div key={key} className="border-b border-border py-3">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="mt-1 break-words text-sm font-medium text-foreground">{formatted}</p>
                  </div>
                );
              })}
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}

function DependentsView() {
  return (
    <div className="space-y-6">
      <PageTitle title="Dependants" description="Information about dependants is not available in the connected service yet." />
      <Notice tone="warning" title="Dependants data is unavailable">
        The backend currently provides a dependants count as part of an assessment, but no separate endpoint for listing or managing dependants. This page does not create, display, or assume any dependant records.
      </Notice>
    </div>
  );
}

function PrivacyView({ consent, saving, error, onWithdraw, onNavigate }) {
  const isGranted = consent?.status === "granted";
  return (
    <div className="space-y-6">
      <PageTitle title="Privacy & consent" description="Manage permission for the Health Reserve feature." />
      <Panel>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Health Reserve data</p>
            <h3 className="mt-2 font-display text-lg font-medium text-foreground">{isGranted ? "Consent is active" : "Consent is not active"}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {consent?.consent_id ? `Record ${consent.consent_id} · ${consent.status}` : "No consent record was returned for this feature."}
            </p>
          </div>
          <ShieldCheck className={`h-6 w-6 shrink-0 ${isGranted ? "text-emerald-600" : "text-muted-foreground"}`} aria-hidden="true" />
        </div>
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{CONSENT_PURPOSE}</p>
        {error && <div className="mt-4"><ErrorState title="Consent could not be updated" message={error} /></div>}
        <div className="mt-5 flex flex-wrap gap-3">
          {isGranted ? (
            <Button type="button" variant="destructive" onClick={onWithdraw} disabled={saving} className="rounded-full">
              {saving ? "Withdrawing..." : "Withdraw consent"}
            </Button>
          ) : (
            <Button type="button" onClick={() => onNavigate("consent")} className="rounded-full">Review consent</Button>
          )}
          <Button type="button" variant="outline" onClick={() => onNavigate("overview")} className="rounded-full">Back to overview</Button>
        </div>
      </Panel>
      {isGranted && (
        <Notice tone="warning" title="Withdrawing consent">
          Health Reserve data will no longer be loaded in this session after withdrawal. You can grant consent again later.
        </Notice>
      )}
    </div>
  );
}

export default function HealthReserve({ previewMode = false }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedView = searchParams.get("view") || "overview";
  const view = VALID_VIEWS.has(requestedView)
    ? requestedView
    : "overview";
  const [consent, setConsent] = useState(null);
  const [consentLoading, setConsentLoading] = useState(!previewMode);
  const [consentLoadError, setConsentLoadError] = useState("");
  const [consentError, setConsentError] = useState("");
  const [consentSaving, setConsentSaving] = useState(false);
  const [assessmentSaving, setAssessmentSaving] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [assessments, setAssessments] = useState([]);
  const [progress, setProgress] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [dataErrors, setDataErrors] = useState({});
  const [dataLoading, setDataLoading] = useState(false);
  const [submittedAssessment, setSubmittedAssessment] = useState(null);
  const servicePreview = !previewMode && Boolean(consentLoadError && !consent);
  const isPreview = previewMode || servicePreview;
  const consentGranted = isPreview || consent?.status === "granted";
  const currency = profiles[0]?.currency_code;

  const navigateView = useCallback((nextView) => {
    const nextParams = new URLSearchParams(searchParams);
    if (nextView === "overview") nextParams.delete("view");
    else nextParams.set("view", nextView);
    setSearchParams(nextParams);
  }, [searchParams, setSearchParams]);

  const loadPrivateData = useCallback(async () => {
    if (previewMode) return;
    setDataLoading(true);
    const [assessmentResult, progressResult, profileResult] = await Promise.allSettled([
      healthReserveApi.getAssessments(),
      healthReserveApi.getProgress(),
      healthReserveApi.getFinancialProfiles(),
    ]);
    const errors = {};

    if (assessmentResult.status === "fulfilled") {
      try {
        setAssessments(listFromResponse(assessmentResult.value.data));
      } catch (error) {
        setAssessments([]);
        errors.assessments = errorMessage(error);
      }
    } else {
      setAssessments([]);
      errors.assessments = errorMessage(assessmentResult.reason);
    }

    if (progressResult.status === "fulfilled") {
      setProgress(progressResult.value.data);
    } else {
      setProgress(null);
      errors.progress = errorMessage(progressResult.reason);
    }

    if (profileResult.status === "fulfilled") {
      try {
        setProfiles(listFromResponse(profileResult.value.data));
      } catch (error) {
        setProfiles([]);
        errors.profiles = errorMessage(error);
      }
    } else {
      setProfiles([]);
      errors.profiles = errorMessage(profileResult.reason);
    }

    setDataErrors(errors);
    setDataLoading(false);
  }, [previewMode]);

  const loadConsent = useCallback(async () => {
    setConsentLoading(true);
    setConsentLoadError("");
    try {
      const response = await healthReserveApi.getConsents();
      const consents = listFromResponse(response.data);
      const healthReserveConsent = consents.find((item) => item.consent_type === CONSENT_TYPE) || null;
      setConsent(healthReserveConsent);
      if (healthReserveConsent?.status === "granted") {
        await loadPrivateData();
      } else {
        setAssessments([]);
        setProgress(null);
        setProfiles([]);
        setDataErrors({});
        setSubmittedAssessment(null);
      }
    } catch (error) {
      setConsent(null);
      setConsentLoadError(errorMessage(error));
    } finally {
      setConsentLoading(false);
    }
  }, [loadPrivateData]);

  useEffect(() => {
    if (previewMode) {
      setConsentLoading(false);
      return;
    }
    loadConsent();
  }, [loadConsent, previewMode]);

  const handleGrantConsent = async () => {
    if (isPreview) return;
    if (consent?.status === "granted") {
      navigateView("assessment");
      return;
    }
    setConsentSaving(true);
    setConsentError("");
    try {
      const response = consent?.consent_id
        ? await healthReserveApi.grantConsent(consent.consent_id, { reason: "Granted from Health Reserve." })
        : await healthReserveApi.createConsent({
            consent_type: CONSENT_TYPE,
            purpose: CONSENT_PURPOSE,
            consent_version: CONSENT_VERSION,
            reason: "Granted from Health Reserve.",
          });
      setConsent(response.data);
      await loadPrivateData();
      navigateView("assessment");
    } catch (error) {
      setConsentError(errorMessage(error));
    } finally {
      setConsentSaving(false);
    }
  };

  const handleAssessmentSubmit = async (payload) => {
    if (isPreview) return;
    setAssessmentSaving(true);
    setAssessmentError("");
    try {
      const response = await healthReserveApi.createAssessment(payload);
      setSubmittedAssessment(response.data);
      await loadPrivateData();
      navigateView("results");
    } catch (error) {
      setAssessmentError(errorMessage(error));
    } finally {
      setAssessmentSaving(false);
    }
  };

  const handleWithdrawConsent = async () => {
    if (isPreview) return;
    if (!consent?.consent_id) return;
    const confirmed = window.confirm("Withdraw Health Reserve consent? This will stop Health Reserve data from loading until you grant consent again.");
    if (!confirmed) return;
    setConsentSaving(true);
    setConsentError("");
    try {
      const response = await healthReserveApi.withdrawConsent(consent.consent_id, { reason: "Withdrawn from Health Reserve privacy settings." });
      setConsent(response.data);
      setAssessments([]);
      setProgress(null);
      setProfiles([]);
      setDataErrors({});
      setSubmittedAssessment(null);
      navigateView("overview");
    } catch (error) {
      setConsentError(errorMessage(error));
    } finally {
      setConsentSaving(false);
    }
  };

  const assessmentForResults = submittedAssessment || assessments[0];
  const isPrivateView = PRIVATE_VIEWS.has(view);
  const page = useMemo(() => {
    if (view === "overview") {
      return (
        <OverviewView
          assessments={assessments}
          progress={progress}
          currency={currency}
          errors={dataErrors}
          onRetry={loadPrivateData}
          onNavigate={navigateView}
        />
      );
    }
    if (view === "consent") {
      return (
        <ConsentView
          consent={consent}
          saving={consentSaving}
          error={consentError}
          previewMode={isPreview}
          onGrant={handleGrantConsent}
          onBack={() => navigateView("overview")}
        />
      );
    }
    if (view === "assessment") {
      return (
        <AssessmentForm
          saving={assessmentSaving}
          error={assessmentError}
          previewMode={isPreview}
          onSubmit={handleAssessmentSubmit}
          onCancel={() => navigateView("overview")}
        />
      );
    }
    if (view === "results") {
      return assessmentForResults ? (
        <div className="space-y-6">
          <PageTitle title="Assessment results" description="These results were returned by the Health Reserve service." />
          <AssessmentSummary assessment={assessmentForResults} currency={currency} />
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => navigateView("dashboard")} className="rounded-full">Go to dashboard</Button>
            <Button type="button" variant="outline" onClick={() => navigateView("overview")} className="rounded-full">Back to overview</Button>
          </div>
        </div>
      ) : dataErrors.assessments ? (
        <ErrorState title="Assessment results could not be loaded" message={dataErrors.assessments} onRetry={loadPrivateData} />
      ) : (
        <EmptyState title="No assessment result to show" action={<Button type="button" onClick={() => navigateView("assessment")} className="rounded-full">Start an assessment</Button>}>
          Submit an assessment to see the service's result here.
        </EmptyState>
      );
    }
    if (view === "dashboard") {
      return <DashboardView assessments={assessments} progress={progress} currency={currency} errors={dataErrors} onRetry={loadPrivateData} onNavigate={navigateView} />;
    }
    if (view === "progress") {
      return <ProgressView assessments={assessments} progress={progress} currency={currency} errors={dataErrors} onRetry={loadPrivateData} />;
    }
    if (view === "history") {
      return <HistoryView assessments={assessments} currency={currency} error={dataErrors.assessments} onRetry={loadPrivateData} onNavigate={navigateView} />;
    }
    if (view === "financial-profile") {
      return <FinancialProfileView profiles={profiles} error={dataErrors.profiles} onRetry={loadPrivateData} />;
    }
    if (view === "dependents") return <DependentsView />;
    if (view === "privacy") {
      return <PrivacyView consent={consent} saving={consentSaving} error={consentError} onWithdraw={handleWithdrawConsent} onNavigate={navigateView} />;
    }
    return null;
  }, [
    view,
    assessments,
    progress,
    currency,
    dataErrors,
    loadPrivateData,
    navigateView,
    consent,
    consentSaving,
    consentError,
    handleGrantConsent,
    assessmentSaving,
    assessmentError,
    handleAssessmentSubmit,
    assessmentForResults,
    profiles,
    handleWithdrawConsent,
    isPreview,
  ]);

  if (consentLoading) return <LoadingState />;

  return (
    <div className="space-y-6 pb-8">
      <div className="rounded-3xl border border-border bg-card p-5 sm:p-7">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">DUMOSENSE · HEALTH RESERVE</p>
            <h1 className="mt-2 font-display text-2xl font-medium text-foreground">Build your financial readiness</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Keep a clear view of your saved health reserve assessments, targets, and progress.
            </p>
          </div>
          <span className={`w-fit rounded-full px-3 py-1.5 text-xs font-medium ${isPreview ? "bg-amber-500/10 text-amber-700 dark:text-amber-300" : consentGranted ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "bg-muted text-muted-foreground"}`}>
            {isPreview ? "Frontend preview" : consentGranted ? "Consent active" : "Consent required"}
          </span>
        </div>
      </div>

      {isPreview && (
        <Notice
          tone={servicePreview ? "warning" : "info"}
          title={servicePreview ? "Health Reserve service unavailable" : "Frontend preview"}
          action={servicePreview ? (
            <Button type="button" variant="outline" size="sm" onClick={loadConsent}>
              Retry service
            </Button>
          ) : null}
        >
          {servicePreview
            ? `${consentLoadError} The Health Reserve interface is available in preview mode; no assessment or consent changes will be saved.`
            : "This preview needs no login or backend connection. It contains no personal data, and assessments, consent changes, and profile updates are not saved."}
        </Notice>
      )}

      <nav className="overflow-x-auto rounded-2xl border border-border bg-card p-2" aria-label="Health Reserve navigation">
        <div className="flex min-w-max gap-1">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => navigateView(id)}
              aria-current={view === id ? "page" : undefined}
              className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors ${
                view === id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      </nav>

      {dataLoading && consentGranted && (isPrivateView && view !== "privacy" || view === "overview") && <LoadingState />}
      {!(dataLoading && consentGranted && (isPrivateView && view !== "privacy" || view === "overview")) && (
        isPrivateView && !consentGranted
          ? <Notice title="Consent is required">
              Grant Health Reserve consent before accessing private assessments or profile information.
              <div className="mt-3">
                <Button type="button" onClick={() => navigateView("consent")} className="rounded-full">
                  Review consent <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </Notice>
          : page
      )}
    </div>
  );
}
