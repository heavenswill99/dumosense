import { createContext, useContext, useEffect, useState, useCallback } from "react";

const ThemeContext = createContext(null);

const DEFAULTS = {
  theme: "light",
  reducedMotion: false,
  highContrast: false,
  textSize: "default",
};

function load() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem("ds-prefs") || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

export function ThemeProvider({ children }) {
  const [prefs, setPrefs] = useState(load);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", prefs.theme === "dark");
    root.setAttribute("data-reduced-motion", String(prefs.reducedMotion));
    root.setAttribute("data-high-contrast", String(prefs.highContrast));
    root.setAttribute("data-text-size", prefs.textSize);
    localStorage.setItem("ds-prefs", JSON.stringify(prefs));
  }, [prefs]);

  const update = useCallback((patch) => setPrefs((p) => ({ ...p, ...patch })), []);
  const toggleTheme = useCallback(
    () => setPrefs((p) => ({ ...p, theme: p.theme === "dark" ? "light" : "dark" })),
    []
  );

  return (
    <ThemeContext.Provider value={{ ...prefs, update, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
