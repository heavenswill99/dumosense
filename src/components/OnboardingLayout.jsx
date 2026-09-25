import { Wordmark } from "@/components/Wordmark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

/**
 * OnboardingLayout — calm, single-column funnel frame with optional step progress.
 */
export function OnboardingLayout({ children, step, totalSteps, className, back }) {
  const navigate = useNavigate();
  return (
    <div className="relative min-h-screen bg-background">
      <div className="ds-ambient pointer-events-none absolute inset-x-0 top-0 h-72" />
      <header className="relative z-10 mx-auto flex max-w-2xl items-center justify-between px-5 py-6">
        <button
          type="button"
          onClick={() => (back ? navigate(back) : navigate(-1))}
          className="flex items-center"
          aria-label="Dumosense home"
          data-testid="onboarding-logo"
        >
          <Wordmark size="sm" state="static" />
        </button>
        <ThemeToggle />
      </header>

      {typeof step === "number" && (
        <div className="relative z-10 mx-auto max-w-2xl px-5">
          <div className="flex gap-1.5" aria-label={`Step ${step} of ${totalSteps}`}>
            {Array.from({ length: totalSteps }).map((_, i) => (
              <span
                key={i}
                className={cn("h-1 flex-1 rounded-full transition-colors", i < step ? "bg-rose" : "bg-secondary")}
              />
            ))}
          </div>
        </div>
      )}

      <main className={cn("relative z-10 mx-auto w-full max-w-2xl px-5 pb-24 pt-8", className)}>{children}</main>
    </div>
  );
}

export default OnboardingLayout;
