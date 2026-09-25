import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Wordmark } from "@/components/Wordmark";
import { CoreMark } from "@/components/CoreMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import {
  ArrowRight, Check, Menu, X, Brain, Target, Puzzle, Sparkles, Activity,
  GitCompare, ShieldCheck, Compass, TrendingUp, Award, Flag, Moon, Waves, Footprints,
} from "lucide-react";

const IMG = {
  questions: "https://images.unsplash.com/photo-1545386673-7723f55e5490?crop=entropy&cs=srgb&fm=jpg&q=85&w=1100",
  mindguard: "https://images.unsplash.com/photo-1518610935804-eeec86691db6?crop=entropy&cs=srgb&fm=jpg&q=85&w=1100",
  reserve: "https://images.unsplash.com/photo-1738441390600-d4002681f40d?crop=entropy&cs=srgb&fm=jpg&q=85&w=1100",
  ai: "https://images.unsplash.com/photo-1505762924203-b085ebd0c5ee?crop=entropy&cs=srgb&fm=jpg&q=85&w=1100",
  ring: "https://images.unsplash.com/photo-1518610935804-eeec86691db6?crop=entropy&cs=srgb&fm=jpg&q=85&w=1100",
};

const NAV = [
  { label: "How It Works", id: "how" },
  { label: "MindGuard", id: "mindguard" },
  { label: "Health Reserve", id: "reserve" },
  { label: "Dumosense AI", id: "ai" },
  { label: "Membership", id: "membership" },
];

const QUESTIONS = [
  "Am I okay?",
  "Has something changed?",
  "What should I pay attention to?",
  "Could my sleep, stress or wellbeing be affecting how I feel?",
  "If something happened to my health, would I be prepared?",
  "What can I do next?",
];

const MINDGUARD_AREAS = [
  { icon: Brain, title: "Memory", body: "Explore your memory patterns over time." },
  { icon: Target, title: "Focus", body: "Understand your attention and concentration patterns." },
  { icon: Puzzle, title: "Thinking", body: "Explore processing, flexible thinking and problem-solving." },
  { icon: Waves, title: "Wellbeing", body: "Explore mood, stress, sleep and other aspects of mental wellbeing." },
  { icon: Activity, title: "Patterns", body: "See how your observations develop over time." },
  { icon: GitCompare, title: "Changes", body: "Understand when recent observations look different from your established pattern." },
];

const RESERVE_STEPS = [
  { tag: "Current position", body: "Understand your likely healthcare exposure today." },
  { tag: "Gap", body: "See where your preparedness might fall short." },
  { tag: "Target", body: "Set a sensible planning target for your circumstances." },
  { tag: "Action", body: "Take practical steps you can actually follow." },
  { tag: "Progress", body: "Watch your preparedness build over time." },
];

const AI_ASKS = [
  "What have I learned?",
  "What has changed?",
  "What might matter?",
  "What don't we know yet?",
  "What could I do next?",
];

const LOOP = ["Sense", "Know", "Discover", "Understand", "Act", "Progress", "Benefit", "Return", "Learn"];

const DISCOVER_ITEMS = [
  "Explore your focus.",
  "Complete a 7-Day Sleep Check.",
  "Build your first health baseline.",
  "Explore your wellbeing.",
  "Understand your preparedness gap.",
  "Review what has changed.",
  "Take your next step.",
];

const DISCOVER_KINDS = [
  { icon: Compass, title: "Discoveries", body: "Small, curious things to learn about yourself." },
  { icon: Flag, title: "Missions", body: "Gentle guided steps that build a fuller picture." },
  { icon: Award, title: "Milestones", body: "Moments that mark real understanding, not scores." },
  { icon: TrendingUp, title: "Progress", body: "A calm sense of continuity as you keep exploring." },
];

const PLANS = [
  {
    key: "free", label: "Free", price: "£0", per: "", note: "No payment required.",
    tagline: "Start exploring Dumosense without paying.",
    features: [
      "Basic Dumosense profile", "Starter MindGuard", "Starter Health Reserve",
      "Basic Dumosense AI", "Discoveries, Missions & Progress", "Limited historical comparison",
    ],
    cta: "Start for Free", recommended: false,
  },
  {
    key: "personal", label: "Personal", price: "£12.99", per: "/month", note: "or £129/year",
    tagline: "For people who want a deeper, continuous understanding of their health.",
    features: [
      "Full MindGuard", "Full Health Reserve", "Full Dumosense AI",
      "Longitudinal intelligence & historical comparisons", "Full discoveries, missions & progress",
      "Dumosense Ring integration", "Expanded member benefits",
    ],
    cta: "Start with Personal", recommended: true,
  },
  {
    key: "family", label: "Family", price: "£24.99", per: "/month", note: "or £249/year",
    tagline: "For people who want to extend Dumosense across their family.",
    features: [
      "Everything in Personal", "Multiple people", "Family & caregiver sharing",
      "Family-oriented progress", "Expanded member benefits",
    ],
    cta: "Start with Family", recommended: false,
  },
];

const COMPARE = [
  { feature: "MindGuard intelligence", free: "Starter", personal: "Full", family: "Full" },
  { feature: "Health Reserve", free: "Starter", personal: "Full", family: "Full" },
  { feature: "Dumosense AI", free: "Basic", personal: "Full", family: "Full" },
  { feature: "Longitudinal intelligence", free: "Limited", personal: "Full", family: "Full" },
  { feature: "Historical comparison", free: "Limited", personal: "Full", family: "Full" },
  { feature: "Discoveries, missions & progress", free: true, personal: true, family: true },
  { feature: "Dumosense Ring integration", free: false, personal: true, family: true },
  { feature: "Multiple people", free: false, personal: false, family: true },
  { feature: "Family & caregiver sharing", free: false, personal: false, family: true },
];

function SectionHeading({ eyebrow, title, coreState = "learning", children }) {
  return (
    <div className="max-w-2xl">
      <div className="mb-4 flex items-center gap-3">
        <CoreMark state={coreState} size={28} />
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{eyebrow}</span>
      </div>
      <h2 className="font-display text-2xl font-normal leading-snug tracking-tight text-foreground sm:text-3xl">{title}</h2>
      {children && <p className="mt-4 text-base leading-relaxed text-muted-foreground">{children}</p>}
    </div>
  );
}

function Cell({ value }) {
  if (value === true) return <Check className="mx-auto h-4 w-4 text-rose" />;
  if (value === false) return <span className="text-muted-foreground/40">—</span>;
  return <span className="text-sm text-foreground">{value}</span>;
}

export default function Landing() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const startFree = () => navigate("/start");
  const signIn = () => navigate("/login");
  const scrollTo = (id) => {
    setMenuOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="ds-ambient pointer-events-none absolute inset-x-0 top-0 h-[70vh]" />

      {/* ---------------- Public navigation ---------------- */}
      <header className="sticky top-0 z-30 border-b border-border/70 bg-[var(--header-bg)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <button onClick={() => scrollTo("top")} data-testid="nav-logo" className="shrink-0">
            <Wordmark size="md" state="sensing" />
          </button>

          <nav className="hidden items-center gap-1 lg:flex">
            {NAV.map((n) => (
              <button
                key={n.id}
                onClick={() => scrollTo(n.id)}
                data-testid={`nav-${n.id}`}
                className="rounded-full px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-hover hover:text-foreground"
              >
                {n.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button
              variant="ghost" data-testid="nav-sign-in" onClick={signIn}
              className="hidden rounded-full text-foreground hover:bg-surface-hover sm:inline-flex"
            >
              Sign in
            </Button>
            <Button
              data-testid="nav-start-free" onClick={startFree}
              className="rounded-full bg-primary px-5 text-primary-foreground hover:opacity-90"
            >
              Start for free
            </Button>
            <button
              onClick={() => setMenuOpen((v) => !v)} data-testid="nav-menu-toggle"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-foreground hover:bg-surface-hover lg:hidden"
              aria-label="Menu"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="border-t border-border/70 px-5 py-3 lg:hidden" data-testid="nav-mobile-menu">
            {NAV.map((n) => (
              <button
                key={n.id} onClick={() => scrollTo(n.id)} data-testid={`nav-mobile-${n.id}`}
                className="block w-full rounded-xl px-3 py-3 text-left text-sm text-foreground hover:bg-surface-hover"
              >
                {n.label}
              </button>
            ))}
            <button onClick={() => { setMenuOpen(false); signIn(); }} data-testid="nav-mobile-sign-in"
              className="block w-full rounded-xl px-3 py-3 text-left text-sm text-foreground hover:bg-surface-hover">
              Sign in
            </button>
          </div>
        )}
      </header>

      <span id="top" />

      {/* ---------------- Hero ---------------- */}
      <section className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-5 pb-24 pt-14 sm:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:pt-20">
        <div className="ds-fade-up">
          <p className="ds-wordmark text-xs text-muted-foreground">DUMOSENSE · HEALTH SECURITY INTELLIGENCE</p>
          <h1 className="mt-6 font-display text-4xl font-light leading-[1.06] tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            What if you understood what was changing in your health —
            <span className="text-primary"> before it became a bigger problem?</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Dumosense helps you make sense of your health over time, understand meaningful
            changes, prepare for what matters and know what you can do next.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg" data-testid="hero-start-free" onClick={startFree}
              className="group h-13 rounded-full bg-primary px-8 py-6 text-base text-primary-foreground hover:opacity-90"
            >
              Start for free
              <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button
              size="lg" variant="outline" data-testid="hero-how-it-works" onClick={() => scrollTo("questions")}
              className="h-13 rounded-full border-border bg-transparent px-8 py-6 text-base text-foreground hover:bg-surface-hover"
            >
              See how it works
            </Button>
          </div>
          <p className="mt-5 text-sm text-muted-foreground">No payment required. Explore Dumosense first.</p>
        </div>

        <div className="relative flex items-center justify-center py-8">
          <div className="absolute h-72 w-72 rounded-full border border-border sm:h-80 sm:w-80" />
          <div className="absolute h-48 w-48 rounded-full border border-border sm:h-56 sm:w-56" />
          <CoreMark state="sensing" size={220} className="drop-shadow-sm" />
        </div>
      </section>

      {/* ---------------- Questions people already ask ---------------- */}
      <section id="questions" className="relative z-10 scroll-mt-24 border-t border-border bg-background-secondary/60 py-20 sm:py-24">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="overflow-hidden rounded-[2rem] border border-border">
            <img src={IMG.questions} alt="A quiet, reflective morning" loading="lazy"
              className="h-full max-h-[460px] w-full object-cover" />
          </div>
          <div>
            <SectionHeading eyebrow="The questions people ask" coreState="sensing"
              title="Your health doesn't happen one appointment at a time.">
              It changes gradually — yet what you know about it is scattered across appointments,
              assessments, devices, memories and your own circumstances. So the everyday questions
              go unanswered.
            </SectionHeading>
            <ul className="mt-8 grid gap-3 sm:grid-cols-2">
              {QUESTIONS.map((q, i) => (
                <li key={i} data-testid={`question-${i}`}
                  className="rounded-2xl border border-border bg-card px-4 py-3.5 text-sm leading-relaxed text-foreground">
                  “{q}”
                </li>
              ))}
            </ul>
            <p className="mt-8 max-w-xl text-base leading-relaxed text-muted-foreground">
              Dumosense is being built to help you answer those questions — calmly, over time,
              in language that makes sense.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------- Discover your patterns (MindGuard) ---------------- */}
      <section id="mindguard" className="relative z-10 scroll-mt-24 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <SectionHeading eyebrow="MindGuard" coreState="learning" title="Discover more about yourself.">
            Build a clearer picture of your cognitive and mental wellbeing over time.
          </SectionHeading>

          <div className="mt-12 grid gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
            <div className="grid gap-5 sm:grid-cols-2">
              {MINDGUARD_AREAS.map(({ icon: Icon, title, body }) => (
                <div key={title} data-testid={`mindguard-${title.toLowerCase()}`}
                  className="rounded-3xl border border-border bg-card p-6 transition-colors hover:bg-surface-hover">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-primary">
                    <Icon className="h-5 w-5" strokeWidth={1.8} />
                  </span>
                  <h3 className="mt-5 font-display text-lg font-medium text-foreground">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
                </div>
              ))}
            </div>
            <div className="overflow-hidden rounded-[2rem] border border-border">
              <img src={IMG.mindguard} alt="A calm moment of reflection" loading="lazy"
                className="h-full max-h-[520px] w-full object-cover" />
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- We're still learning your pattern ---------------- */}
      <section className="relative z-10 py-6 sm:py-10">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <div className="rounded-[2rem] border border-border bg-secondary/40 p-8 text-center sm:p-12">
            <CoreMark state="insufficient" size={44} className="mx-auto mb-5" />
            <p className="font-display text-2xl font-light leading-snug tracking-tight text-foreground sm:text-3xl">
              Sometimes the most useful answer is:
              <br />
              <span className="text-primary">“We're still learning your pattern.”</span>
            </p>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Dumosense is designed around understanding you over time — not forcing a conclusion
              from a single observation. When there isn't enough to say something meaningful yet,
              we'll tell you honestly.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------- Health Reserve ---------------- */}
      <section id="reserve" className="relative z-10 scroll-mt-24 border-t border-border bg-background-secondary/60 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div className="order-2 overflow-hidden rounded-[2rem] border border-border lg:order-1">
              <img src={IMG.reserve} alt="Walking a path together" loading="lazy"
                className="h-full max-h-[480px] w-full object-cover" />
            </div>
            <div className="order-1 lg:order-2">
              <SectionHeading eyebrow="Health Reserve" coreState="intelligence"
                title="What if your health changed tomorrow?">
                Would you know what healthcare costs you might face? Do you understand what your
                current cover means? Where might your gaps be — and what could you prepare for now?
              </SectionHeading>
              <p className="mt-6 text-base leading-relaxed text-foreground">
                <span className="font-medium">Health-Financial Preparedness Intelligence.</span> Health
                Reserve helps you understand your healthcare exposure, identify preparedness gaps,
                set a planning target and take practical action.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-2">
                {RESERVE_STEPS.map(({ tag }, i) => (
                  <span key={tag} className="flex items-center gap-2" data-testid={`reserve-step-${i}`}>
                    <span className="rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-medium uppercase tracking-wide text-foreground">
                      {tag}
                    </span>
                    {i < RESERVE_STEPS.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />}
                  </span>
                ))}
              </div>
              <p className="mt-6 text-sm text-muted-foreground">
                Health Reserve is a preparedness tool — not banking, insurance, investment
                management or financial advice.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Dumosense AI ---------------- */}
      <section id="ai" className="relative z-10 scroll-mt-24 py-20 sm:py-24">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <SectionHeading eyebrow="Dumosense AI" coreState="intelligence"
              title="You don't have to figure it all out yourself.">
              Your shared health intelligence experience — it interprets, explains, connects and
              prioritises using only your authorised Dumosense intelligence.
            </SectionHeading>
            <ul className="mt-8 space-y-3">
              {AI_ASKS.map((q, i) => (
                <li key={i} data-testid={`ai-ask-${i}`}
                  className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5 text-sm text-foreground">
                  <Sparkles className="h-4 w-4 shrink-0 text-rose" />
                  “{q}”
                </li>
              ))}
            </ul>
          </div>
          <div className="overflow-hidden rounded-[2rem] border border-border">
            <img src={IMG.ai} alt="Looking ahead" loading="lazy"
              className="h-full max-h-[480px] w-full object-cover" />
          </div>
        </div>
      </section>

      {/* ---------------- The bigger picture — Value Loop ---------------- */}
      <section id="how" className="relative z-10 scroll-mt-24 border-t border-border bg-background-secondary/60 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 text-center sm:px-8">
          <div className="mx-auto max-w-2xl">
            <div className="mb-4 flex items-center justify-center gap-3">
              <CoreMark state="learning" size={28} />
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">The bigger picture</span>
            </div>
            <h2 className="font-display text-2xl font-normal leading-snug tracking-tight text-foreground sm:text-3xl">
              Dumosense becomes more useful as your understanding develops.
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              A continuous value loop built for meaningful continuity — not compulsive engagement.
            </p>
          </div>

          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-2 gap-y-3">
            {LOOP.map((step, i) => (
              <span key={step} className="flex items-center gap-2" data-testid={`loop-${step.toLowerCase()}`}>
                <span className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground">
                  {step}
                </span>
                {i < LOOP.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- There is always something to discover ---------------- */}
      <section id="discover" className="relative z-10 scroll-mt-24 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <SectionHeading eyebrow="Progress & discovery" coreState="sensing"
            title="There is always something to discover.">
            Your progress isn't about being “healthy enough.” It's about understanding yourself better.
          </SectionHeading>

          <div className="mt-10 grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="flex flex-wrap gap-3">
              {DISCOVER_ITEMS.map((d, i) => (
                <span key={i} data-testid={`discover-item-${i}`}
                  className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2.5 text-sm text-foreground">
                  <Footprints className="h-4 w-4 text-rose" />
                  {d}
                </span>
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {DISCOVER_KINDS.map(({ icon: Icon, title, body }) => (
                <div key={title} data-testid={`discover-kind-${title.toLowerCase()}`}
                  className="rounded-3xl border border-border bg-card p-6">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-primary">
                    <Icon className="h-5 w-5" strokeWidth={1.8} />
                  </span>
                  <h3 className="mt-5 font-display text-base font-medium text-foreground">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Dumosense Ring ---------------- */}
      <section id="ring" className="relative z-10 scroll-mt-24 border-t border-border bg-background-secondary/60 py-20 sm:py-24">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-2">
          <div className="overflow-hidden rounded-[2rem] border border-border">
            <img src={IMG.ring} alt="Dumosense Ring" loading="lazy"
              className="h-full max-h-[460px] w-full object-cover" />
          </div>
          <div>
            <SectionHeading eyebrow="Dumosense Ring" coreState="sensing"
              title="Your health doesn't stop when you close the app.">
              The Dumosense Ring is a sensing layer that can contribute continuous, everyday signals
              to your evolving health picture.
            </SectionHeading>
            <p className="mt-6 flex items-start gap-3 text-base leading-relaxed text-foreground">
              <Moon className="mt-1 h-5 w-5 shrink-0 text-rose" />
              Less of your health story has to depend on remembering to enter it yourself.
            </p>
            <p className="mt-6 rounded-2xl border border-border bg-card px-4 py-3.5 text-sm text-muted-foreground">
              The Ring is an optional capability — you don't need to buy anything to begin using
              Dumosense.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------- Membership ---------------- */}
      <section id="membership" className="relative z-10 scroll-mt-24 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <div className="mb-4 flex items-center justify-center gap-3">
              <CoreMark state="intelligence" size={28} />
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Membership</span>
            </div>
            <h2 className="font-display text-3xl font-light leading-tight tracking-tight text-foreground sm:text-4xl">
              How much of Dumosense would you like to explore?
            </h2>
          </div>

          <div className="mt-12 grid gap-5 lg:grid-cols-3">
            {PLANS.map((p) => (
              <div key={p.key} data-testid={`plan-${p.key}`}
                className={`flex flex-col rounded-3xl border bg-card p-7 transition-colors ${
                  p.recommended ? "border-rose ring-1 ring-rose/40" : "border-border"}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CoreMark state={p.recommended ? "intelligence" : "static"} size={24} />
                    <h3 className="font-display text-lg font-medium text-foreground">{p.label}</h3>
                  </div>
                  {p.recommended && (
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">Recommended</span>
                  )}
                </div>
                <p className="mt-4 font-display text-3xl font-light text-foreground">
                  {p.price}<span className="text-sm text-muted-foreground">{p.per}</span>
                </p>
                {p.note && <p className="text-xs text-muted-foreground">{p.note}</p>}
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{p.tagline}</p>

                <ul className="mt-6 flex-1 space-y-2.5">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-foreground">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-rose" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Button onClick={startFree} data-testid={`plan-cta-${p.key}`}
                  variant={p.recommended ? "default" : "outline"}
                  className={`mt-7 h-11 rounded-full ${p.recommended
                    ? "bg-primary text-primary-foreground hover:opacity-90"
                    : "border-border bg-transparent text-foreground hover:bg-surface-hover"}`}>
                  {p.cta}
                </Button>
              </div>
            ))}
          </div>

          {/* Comparison */}
          <div className="mt-12 overflow-hidden rounded-3xl border border-border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left" data-testid="plan-comparison">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-5 py-4 text-sm font-medium text-muted-foreground">Compare plans</th>
                    <th className="px-4 py-4 text-center text-sm font-medium text-foreground">Free</th>
                    <th className="px-4 py-4 text-center text-sm font-medium text-primary">Personal</th>
                    <th className="px-4 py-4 text-center text-sm font-medium text-foreground">Family</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARE.map((row, i) => (
                    <tr key={row.feature} className={i % 2 ? "bg-secondary/30" : ""}>
                      <td className="px-5 py-3.5 text-sm text-foreground">{row.feature}</td>
                      <td className="px-4 py-3.5 text-center"><Cell value={row.free} /></td>
                      <td className="px-4 py-3.5 text-center"><Cell value={row.personal} /></td>
                      <td className="px-4 py-3.5 text-center"><Cell value={row.family} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Final free CTA ---------------- */}
      <section className="relative z-10 border-t border-border bg-background-secondary/60 py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
          <CoreMark state="sensing" size={52} className="mx-auto mb-6" />
          <h2 className="font-display text-3xl font-light tracking-tight text-foreground sm:text-4xl">
            Not sure yet? <span className="text-primary">Start free.</span>
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
            No payment required. Explore Dumosense first and decide when you're ready.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button size="lg" data-testid="final-start-free" onClick={startFree}
              className="group h-13 rounded-full bg-primary px-8 py-6 text-base text-primary-foreground hover:opacity-90">
              Start for free
              <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button size="lg" variant="outline" data-testid="final-sign-in" onClick={signIn}
              className="h-13 rounded-full border-border bg-transparent px-8 py-6 text-base text-foreground hover:bg-surface-hover">
              Sign in
            </Button>
          </div>
        </div>
      </section>

      <footer className="relative z-10 border-t border-border py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 text-center sm:flex-row sm:px-8 sm:text-left">
          <Wordmark size="sm" state="static" />
          <p className="max-w-md text-xs leading-relaxed text-muted-foreground">
            Dumosense helps you understand change over time. It does not diagnose disease or predict
            any condition, and Health Reserve is not financial advice.
          </p>
        </div>
      </footer>
    </div>
  );
}
