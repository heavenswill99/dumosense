import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BrainCircuit,
  Check,
  HeartPulse,
  LoaderCircle,
  Mail,
  PartyPopper,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Wordmark } from "@/components/Wordmark";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { submitWaitlistRegistration } from "@/lib/waitlist";

const PRODUCT_OPTIONS = [
  {
    key: "mindguard",
    label: "MindGuard",
    description: "Intelligent insights for understanding and supporting mental wellbeing.",
    icon: BrainCircuit,
  },
  {
    key: "health_reserve",
    label: "Health Reserve",
    description: "A clearer way to understand and plan for future health needs.",
    icon: HeartPulse,
  },
  {
    key: "both",
    label: "Both products",
    description: "Explore the full DumoSense wellbeing experience.",
    icon: Sparkles,
  },
];

const EMPLOYMENT_OPTIONS = [
  "Employed",
  "Self-employed",
  "Business Owner",
  "Student",
  "Retired",
  "Unemployed",
  "Other",
];

const TESTING_OPTIONS = [
  { value: "Yes, I'm interested", label: "Yes, I'm interested" },
  { value: "Maybe, I'd like more information", label: "Maybe, I'd like more information" },
  { value: "No, just keep me updated", label: "No, just keep me updated" },
];

const INITIAL_FORM = {
  full_name: "",
  email: "",
  phone_number: "",
  city: "",
  country: "",
  employment_status: "",
  occupation: "",
  industry: "",
  product_interest: "",
  interest_reason: "",
  testing_interest: "",
  consent_accepted: false,
};

const PRIVACY_POLICY_URL = import.meta.env.VITE_PRIVACY_POLICY_URL?.trim();

function ChoiceCard({ active, children, onClick, ...props }) {
  const { className, ...buttonProps } = props;
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={`rounded-2xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active
          ? "border-primary bg-secondary shadow-sm"
          : "border-border bg-background-secondary hover:border-rose hover:bg-surface-hover"
      } ${className || ""}`}
      {...buttonProps}
    >
      {children}
    </button>
  );
}

export default function WaitlistModal({ open, onOpenChange }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [emailStatus, setEmailStatus] = useState("processing");
  const successButtonRef = useRef(null);

  useEffect(() => {
    if (submitted && open) {
      successButtonRef.current?.focus();
    }
  }, [submitted, open]);

  const updateField = (field) => (event) => {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
    setSubmitError("");
  };

  const chooseField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
    setSubmitError("");
  };

  const validate = () => {
    const nextErrors = {};

    if (!form.full_name.trim()) {
      nextErrors.full_name = "Please enter your full name.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!form.product_interest) {
      nextErrors.product_interest = "Please choose a product interest.";
    }
    if (!form.consent_accepted) {
      nextErrors.consent_accepted = "You must agree before joining the waitlist.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError("");
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const result = await submitWaitlistRegistration(form);
      setSubmittedEmail(form.email.trim().toLowerCase());
      setEmailStatus(
        result.confirmation_email_status === "sent"
          ? "sent"
          : result.confirmation_email_status === "failed"
            ? "failed"
            : "processing"
      );
      setSubmitted(true);
    } catch (error) {
      setSubmitError(
        error?.message ||
          "We couldn't confirm the registration result. Please try again, or contact DumoSense if the problem continues."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (nextOpen) => {
    if (isSubmitting && !nextOpen) return;

    if (!nextOpen && submitted) {
      setForm(INITIAL_FORM);
      setErrors({});
      setSubmitError("");
      setSubmitted(false);
      setSubmittedEmail("");
      setEmailStatus("processing");
    }

    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="waitlist-dialog-content max-h-[92dvh] w-[calc(100%-1rem)] max-w-3xl overflow-hidden border-border bg-background p-0 shadow-2xl sm:rounded-3xl"
        overlayClassName="bg-black/45 backdrop-blur-[2px]"
        onEscapeKeyDown={(event) => {
          if (isSubmitting) event.preventDefault();
        }}
        onInteractOutside={(event) => {
          if (isSubmitting) event.preventDefault();
        }}
      >
        <div className="max-h-[92dvh] overflow-y-auto overscroll-contain">
          {submitted ? (
            <section className="relative overflow-hidden px-6 py-10 text-center sm:px-12 sm:py-14" aria-live="polite">
              <span className="waitlist-confetti waitlist-confetti-one" aria-hidden="true" />
              <span className="waitlist-confetti waitlist-confetti-two" aria-hidden="true" />
              <span className="waitlist-confetti waitlist-confetti-three" aria-hidden="true" />
              <Wordmark size="md" state="sensing" className="mb-8" />
              <div className="waitlist-success-mark mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-success/10 text-success">
                <Check className="h-10 w-10" strokeWidth={2.2} />
              </div>
              <div className="mt-6 flex items-center justify-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                <PartyPopper className="h-4 w-4" />
                Early access community
              </div>
              <DialogTitle className="mt-3 font-display text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
                Congratulations!
              </DialogTitle>
              <p className="mt-3 font-display text-xl font-medium text-primary">
                You&apos;re officially on the DumoSense Waitlist!
              </p>
              <DialogDescription className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground sm:text-base">
                Welcome to the DumoSense Early Access Community. Your registration has been received successfully!
                We&apos;re excited to have you join us on this journey toward smarter health and wellbeing.
              </DialogDescription>

              <div className="mx-auto mt-7 max-w-md rounded-2xl border border-border bg-background-secondary p-4 text-left">
                <div className="flex items-start gap-3">
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
                    <Mail className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium text-foreground">
                      {emailStatus === "sent"
                        ? "Confirmation Email Sent!"
                        : emailStatus === "failed"
                          ? "Your registration is saved, but the confirmation email could not be sent yet."
                          : "Your confirmation email is being processed."}
                    </p>
                    <p className="mt-1 break-all text-sm text-muted-foreground">
                      {emailStatus === "sent"
                        ? <>We&apos;ve sent a confirmation email to <strong className="font-semibold text-foreground">{submittedEmail}</strong>. Please check your inbox and spam folder.</>
                        : emailStatus === "failed"
                          ? <>We&apos;ve received your registration for <strong className="font-semibold text-foreground">{submittedEmail}</strong>. Please contact DumoSense if you need help confirming your registration.</>
                          : <>We&apos;ve received your registration for <strong className="font-semibold text-foreground">{submittedEmail}</strong>. Please check your inbox later for a welcome message.</>}
                    </p>
                  </div>
                </div>
              </div>

              <p className="mt-8 font-display text-sm text-muted-foreground">
                DumoSense — Your Wellbeing Deserves a Smarter Future.
              </p>
              <Button
                ref={successButtonRef}
                type="button"
                onClick={() => handleOpenChange(false)}
                className="mt-6 h-12 rounded-full bg-primary px-8 text-base text-primary-foreground hover:opacity-90"
              >
                Back to Website
              </Button>
            </section>
          ) : (
            <div className="p-5 sm:p-8">
              <div className="mb-7 border-b border-border pb-6 pr-8">
                <Wordmark size="md" state="sensing" />
                <div className="mt-5 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  DumoSense Early Access
                </div>
                <DialogTitle className="mt-3 max-w-2xl font-display text-3xl font-light leading-tight tracking-tight text-foreground sm:text-4xl">
                  Your Wellbeing Deserves a Smarter Future.
                </DialogTitle>
                <DialogDescription className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
                  Join the early access community and be among the first to explore MindGuard for mental wellbeing and Health Reserve for future health planning.
                </DialogDescription>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {PRODUCT_OPTIONS.slice(0, 2).map(({ key, label, description, icon: Icon }) => (
                    <div key={key} className="flex items-start gap-3 rounded-xl border border-border bg-background-secondary p-3">
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <p className="text-xs leading-relaxed text-muted-foreground">
                        <strong className="font-semibold text-foreground">{label}:</strong> {description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-7" noValidate>
                <section aria-labelledby="waitlist-personal-heading">
                  <h3 id="waitlist-personal-heading" className="mb-4 font-display text-lg font-medium text-foreground">
                    Personal information
                  </h3>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-full-name">Full name <span aria-hidden="true">*</span></Label>
                      <Input id="waitlist-full-name" autoComplete="name" required value={form.full_name} onChange={updateField("full_name")} placeholder="Your full name" aria-invalid={!!errors.full_name} aria-describedby={errors.full_name ? "waitlist-full-name-error" : undefined} />
                      {errors.full_name && <p id="waitlist-full-name-error" role="alert" className="text-xs font-medium text-error">{errors.full_name}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-email">Email address <span aria-hidden="true">*</span></Label>
                      <Input id="waitlist-email" type="email" autoComplete="email" required value={form.email} onChange={updateField("email")} placeholder="name@example.com" aria-invalid={!!errors.email} aria-describedby={errors.email ? "waitlist-email-error" : undefined} />
                      {errors.email && <p id="waitlist-email-error" role="alert" className="text-xs font-medium text-error">{errors.email}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-phone">Phone number</Label>
                      <Input id="waitlist-phone" type="tel" autoComplete="tel" value={form.phone_number} onChange={updateField("phone_number")} placeholder="Optional" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-city">City</Label>
                      <Input id="waitlist-city" autoComplete="address-level2" value={form.city} onChange={updateField("city")} placeholder="Optional" />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="waitlist-country">Country</Label>
                      <Input id="waitlist-country" autoComplete="country-name" value={form.country} onChange={updateField("country")} placeholder="Optional" />
                    </div>
                  </div>
                </section>

                <section aria-labelledby="waitlist-professional-heading">
                  <h3 id="waitlist-professional-heading" className="mb-4 font-display text-lg font-medium text-foreground">
                    Professional background <span className="text-xs font-normal text-muted-foreground">(optional)</span>
                  </h3>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-employment">Employment status</Label>
                      <select id="waitlist-employment" value={form.employment_status} onChange={updateField("employment_status")} className="flex h-10 w-full rounded-md border border-input bg-background-secondary px-3 py-2 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50">
                        <option value="">Select an option</option>
                        {EMPLOYMENT_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="waitlist-occupation">Occupation or job title</Label>
                      <Input id="waitlist-occupation" autoComplete="organization-title" value={form.occupation} onChange={updateField("occupation")} placeholder="Optional" />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="waitlist-industry">Industry or professional field</Label>
                      <Input id="waitlist-industry" value={form.industry} onChange={updateField("industry")} placeholder="Optional" />
                    </div>
                  </div>
                </section>

                <section aria-labelledby="waitlist-product-heading">
                  <h3 id="waitlist-product-heading" className="mb-3 font-display text-lg font-medium text-foreground">
                    Product interest <span aria-hidden="true">*</span>
                  </h3>
                  <div role="radiogroup" aria-labelledby="waitlist-product-heading" aria-describedby={errors.product_interest ? "waitlist-product-error" : undefined} className="grid gap-3 sm:grid-cols-3">
                    {PRODUCT_OPTIONS.map(({ key, label, description, icon: Icon }) => (
                      <ChoiceCard key={key} active={form.product_interest === key} onClick={() => chooseField("product_interest", key)}>
                        <span className="flex items-center gap-2 font-display font-medium text-foreground">
                          <Icon className="h-4 w-4 text-primary" />
                          {label}
                        </span>
                        <span className="mt-2 block text-xs leading-relaxed text-muted-foreground">{description}</span>
                      </ChoiceCard>
                    ))}
                  </div>
                  {errors.product_interest && <p id="waitlist-product-error" role="alert" className="mt-2 text-xs font-medium text-error">{errors.product_interest}</p>}
                </section>

                <section className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="waitlist-interest">What interests you most about DumoSense?</Label>
                    <Textarea id="waitlist-interest" value={form.interest_reason} onChange={updateField("interest_reason")} placeholder="Optional — share what excites you most." rows={3} />
                  </div>
                  <fieldset>
                    <legend className="mb-3 text-sm font-medium text-foreground">
                      Would you like to participate in initial product testing?
                    </legend>
                    <div role="radiogroup" aria-label="Initial product testing preference" className="grid gap-2 sm:grid-cols-3">
                      {TESTING_OPTIONS.map(({ value, label }) => (
                        <ChoiceCard key={value} active={form.testing_interest === value} onClick={() => chooseField("testing_interest", value)} className="px-3 py-3 text-sm">
                          {label}
                        </ChoiceCard>
                      ))}
                    </div>
                  </fieldset>
                </section>

                <section>
                  <label className="flex items-start gap-3 rounded-2xl border border-border bg-background-secondary p-4">
                    <input type="checkbox" required checked={form.consent_accepted} onChange={updateField("consent_accepted")} aria-invalid={!!errors.consent_accepted} aria-describedby={errors.consent_accepted ? "waitlist-consent-error" : undefined} className="mt-1 h-4 w-4 shrink-0 rounded border-border text-primary focus:ring-primary" />
                    <span className="text-sm leading-relaxed text-foreground">
                      I agree to DumoSense collecting and processing my information to manage my waitlist registration and send early-access communications, as described in the{" "}
                      {PRIVACY_POLICY_URL ? (
                        <a href={PRIVACY_POLICY_URL} target="_blank" rel="noreferrer" className="font-medium text-primary underline">
                          Privacy Policy
                        </a>
                      ) : (
                        <>
                          <span className="font-medium">Privacy Policy</span>.
                          <span className="ml-1 text-muted-foreground">The policy must be published before launch.</span>
                        </>
                      )}
                    </span>
                  </label>
                  {errors.consent_accepted && <p id="waitlist-consent-error" role="alert" className="mt-2 text-xs font-medium text-error">{errors.consent_accepted}</p>}
                </section>

                {submitError && (
                  <p role="alert" className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                    {submitError}
                  </p>
                )}

                <Button type="submit" disabled={isSubmitting} className="h-12 w-full rounded-full bg-primary px-8 text-base text-primary-foreground hover:opacity-90 disabled:cursor-wait disabled:opacity-70 sm:w-auto">
                  {isSubmitting ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Submitting registration...
                    </>
                  ) : (
                    <>
                      Join the DumoSense Waitlist
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground">Your information is used only to manage your waitlist registration and related updates.</p>
              </form>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
