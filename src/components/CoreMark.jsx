import { cn } from "@/lib/utils";

/**
 * Dumosense Core Mark — the signature circular "O" from the DUMOSENSE logo,
 * rendered as a luminous eclipse ring with a bright corona flare.
 * Represents continuity, sensing, personal patterns and the intelligence cycle.
 * States: static | sensing | learning | intelligence | insufficient | change
 * Animations are subtle and calm — never flashing or alarming.
 */
export function CoreMark({ state = "static", size = 48, className, strokeWidth, ...rest }) {
  const s = size;
  const sw = strokeWidth ?? Math.max(1.4, s * 0.05);
  const r = (s - sw * 2) / 2;
  const c = s / 2;
  const uid = `cm-${Math.random().toString(36).slice(2, 8)}`;

  const dashed = state === "insufficient";
  // Corona flare sits on the ring's upper-left, matching the supplied logo.
  const flareAngle = (-125 * Math.PI) / 180;
  const fx = c + r * Math.cos(flareAngle);
  const fy = c + r * Math.sin(flareAngle);

  const glowClass =
    state === "intelligence" ? "ds-anim-breathe" : state === "sensing" ? "ds-anim-sense" : "";

  return (
    <span
      role="img"
      aria-label={`Dumosense core mark, state: ${state}`}
      data-testid="core-mark"
      data-state={state}
      className={cn("relative inline-flex items-center justify-center align-middle", className)}
      style={{ width: s, height: s }}
      {...rest}
    >
      {/* Ambient bloom behind the ring */}
      <span
        className={cn("pointer-events-none absolute rounded-full", glowClass)}
        style={{
          inset: "-14%",
          background: "radial-gradient(circle at 38% 34%, var(--core-glow), transparent 68%)",
          filter: `blur(${Math.max(2, s * 0.06)}px)`,
        }}
      />

      <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`} fill="none" className="relative">
        <defs>
          <linearGradient id={`${uid}-ring`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--core-hi)" />
            <stop offset="45%" stopColor="var(--core-stroke)" />
            <stop offset="100%" stopColor="var(--core-stroke)" stopOpacity="0.7" />
          </linearGradient>
          <radialGradient id={`${uid}-flare`}>
            <stop offset="0%" stopColor="var(--core-hi)" stopOpacity="1" />
            <stop offset="60%" stopColor="var(--core-stroke)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--core-stroke)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* meaningful change: expanding ripple ring (calm, single) */}
        {state === "change" && (
          <circle className="ds-anim-ripple" cx={c} cy={c} r={r} stroke="var(--core-stroke)"
            strokeWidth={sw} opacity="0.5" />
        )}

        {/* soft outer bloom ring */}
        <circle cx={c} cy={c} r={r} stroke="var(--core-stroke)" strokeWidth={sw * 2.4}
          opacity="0.12" />

        {/* base eclipse ring — the O */}
        <circle
          cx={c}
          cy={c}
          r={r}
          stroke={`url(#${uid}-ring)`}
          strokeWidth={sw}
          strokeLinecap="round"
          opacity={dashed ? 0.55 : 1}
          strokeDasharray={dashed ? `${sw * 1.8} ${sw * 2.6}` : undefined}
        />

        {/* learning: revolving luminous arc */}
        {state === "learning" && (
          <g className="ds-anim-learn">
            <circle cx={c} cy={c} r={r} stroke="var(--core-hi)" strokeWidth={sw * 1.1}
              strokeLinecap="round" strokeDasharray={`${r * 0.7} ${r * 6}`} opacity="0.95" />
          </g>
        )}

        {/* corona flare highlight (the logo's signature glow) */}
        {!dashed && (
          <circle cx={fx} cy={fy} r={sw * 2.6} fill={`url(#${uid}-flare)`} />
        )}
        {!dashed && <circle cx={fx} cy={fy} r={Math.max(1, sw * 0.7)} fill="var(--core-hi)" />}

        {/* central sensing core */}
        <circle cx={c} cy={c} r={Math.max(1.2, s * 0.045)} fill="var(--core-stroke)" opacity="0.6" />
      </svg>
    </span>
  );
}

export default CoreMark;
