import { useTheme } from "@/context/ThemeContext";
import { Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggleTheme}
      data-testid="theme-toggle-button"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={cn(
        "inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-background-secondary text-foreground transition-colors hover:bg-surface-hover",
        className
      )}
    >
      {isDark ? <Sun className="h-4.5 w-4.5" size={18} /> : <Moon className="h-4.5 w-4.5" size={18} />}
    </button>
  );
}

export default ThemeToggle;
