import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";

export default function ProfileComplete() {
  const navigate = useNavigate();
  return (
    <OnboardingLayout>
      <div className="flex flex-col items-center pt-10 text-center">
        <CoreMark state="intelligence" size={92} className="mb-8" />
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground sm:text-4xl">
          Your foundation is ready.
        </h1>
        <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
          Dumosense will learn your personal pattern over time. You do not need to provide everything
          today.
        </p>
        <Button
          onClick={() => navigate("/app")}
          data-testid="profile-complete-continue"
          className="mt-10 h-13 rounded-full bg-primary px-8 py-6 text-base text-primary-foreground hover:opacity-90"
        >
          Go to my health intelligence
        </Button>
      </div>
    </OnboardingLayout>
  );
}
