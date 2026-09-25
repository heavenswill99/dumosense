import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { NAV_ITEMS } from "@/lib/domains";
import { Wordmark } from "@/components/Wordmark";
import { CoreMark } from "@/components/CoreMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/utils";
import { Bell } from "lucide-react";

function NavList({ orientation }) {
  const mobile = orientation === "mobile";
  return (
    <nav
      className={cn(mobile ? "flex w-full items-stretch justify-around" : "flex flex-col gap-1")}
      aria-label="Primary"
    >
      {NAV_ITEMS.map(({ key, label, to, icon: Icon, testid }) => (
        <NavLink
          key={key}
          to={to}
          end={to === "/app"}
          data-testid={testid}
          className={({ isActive }) =>
            cn(
              "group relative flex items-center transition-colors duration-200",
              mobile
                ? "flex-1 flex-col gap-1 py-2 text-[11px]"
                : "gap-3 rounded-xl px-3.5 py-3 text-sm font-medium",
              isActive
                ? mobile
                  ? "text-primary"
                  : "bg-secondary text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )
          }
        >
          {({ isActive }) => (
            <>
              {!mobile && isActive && (
                <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-rose" />
              )}
              <Icon className={cn(mobile ? "h-5 w-5" : "h-[18px] w-[18px]")} strokeWidth={isActive ? 2.2 : 1.7} />
              <span className={cn(mobile && "leading-none")}>{label}</span>
              {mobile && isActive && <span className="mt-0.5 h-1 w-1 rounded-full bg-rose" />}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

const TITLES = {
  "/app": { title: "Your Health Intelligence", desc: "One place to understand what is changing, what matters and what you can do next." },
  "/app/mindguard": { title: "MindGuard", desc: "Cognitive and mental wellbeing intelligence." },
  "/app/health-reserve": { title: "Health Reserve", desc: "Health-financial preparedness intelligence." },
  "/app/ai": { title: "Dumosense AI", desc: "Intelligence that connects your health picture." },
  "/app/profile": { title: "Profile", desc: "Your details, preferences and permissions." },
  "/app/membership": { title: "Membership", desc: "Choose the plan that fits — prototype pricing, no payment taken." },
  "/app/privacy": { title: "Privacy Center", desc: "Your data, connected sources, permissions and history." },
};

export function AppShell({ children }) {
  const location = useLocation();
  const meta = TITLES[location.pathname] || TITLES["/app"];
  const [demoMode, setDemoMode] = useState(null);

  useEffect(() => {
    api.get("/demo/status").then(({ data }) => setDemoMode(data.demo_mode)).catch(() => {});
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop left rail */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[264px] flex-col border-r border-border bg-background-secondary px-4 py-6 lg:flex">
        <div className="px-2">
          <Wordmark size="md" state="sensing" />
          <p className="mt-2 pl-0.5 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Health Security Intelligence
          </p>
        </div>
        <div className="mt-10 flex-1">
          <NavList orientation="desktop" />
        </div>
        <div className="flex items-center justify-between border-t border-border pt-4">
          <span className="text-xs text-muted-foreground">Appearance</span>
          <ThemeToggle />
        </div>
      </aside>

      {/* Main column */}
      <div className="lg:pl-[264px]">
        {/* Top bar */}
        <header className="sticky top-0 z-20 border-b border-border backdrop-blur-xl" style={{ background: "var(--header-bg)" }}>
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="lg:hidden">
                <Wordmark size="sm" state="static" />
              </div>
              <div className="hidden min-w-0 sm:block">
                <h1 className="truncate font-display text-lg font-medium text-foreground">{meta.title}</h1>
                <p className="truncate text-xs text-muted-foreground">{meta.desc}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="notifications-button"
                aria-label="Notifications"
                className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-background-secondary text-foreground transition-colors hover:bg-surface-hover"
              >
                <Bell className="h-[18px] w-[18px]" strokeWidth={1.7} />
              </button>
              <div className="lg:hidden">
                <ThemeToggle />
              </div>
            </div>
          </div>
        </header>

        {/* Mobile title block */}
        <div className="px-4 pt-6 sm:hidden">
          <h1 className="font-display text-2xl font-medium text-foreground">{meta.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{meta.desc}</p>
        </div>

        {demoMode && (
          <div data-testid="demo-banner" className="mx-auto mt-4 max-w-5xl px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-2 rounded-xl border border-rose/40 bg-rose/10 px-4 py-2 text-xs font-medium text-foreground">
              <span className="rounded-full bg-rose px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">Demo data</span>
              Showing the “{demoMode.replace(/_/g, " ")}” scenario — this is synthetic sample data, not your own.
            </div>
          </div>
        )}

        <main className="mx-auto max-w-5xl px-4 pb-28 pt-6 sm:px-6 lg:px-8 lg:pb-16">{children}</main>
      </div>

      {/* Mobile bottom nav */}
      <div
        className="fixed inset-x-0 bottom-0 z-30 border-t border-border backdrop-blur-xl lg:hidden"
        style={{ background: "var(--header-bg)" }}
      >
        <div className="mx-auto max-w-lg px-2 pb-[env(safe-area-inset-bottom)]">
          <NavList orientation="mobile" />
        </div>
      </div>
    </div>
  );
}

export default AppShell;
