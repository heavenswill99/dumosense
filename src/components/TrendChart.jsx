import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const MOOD = { 1: "Low", 2: "Tired", 3: "Steady", 4: "Rested", 5: "Bright" };

function fmtDay(ts) {
  try {
    return new Date(ts).toLocaleDateString(undefined, { weekday: "short", day: "numeric" });
  } catch {
    return "";
  }
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-xl border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-medium text-foreground">{fmtDay(p.timestamp)}</p>
      <p className="text-muted-foreground">Wellbeing: {MOOD[p.value] || p.value}</p>
    </div>
  );
}

/**
 * Calm longitudinal wellbeing trend. Observed data only — no interpretation drawn here.
 */
export function TrendChart({ data }) {
  const rows = (data || []).map((d) => ({ timestamp: d.timestamp, value: d.value }));
  return (
    <div className="h-56 w-full" data-testid="mindguard-trend-chart">
      <ResponsiveContainer width="100%" height="100%" minHeight={200}>
        <AreaChart data={rows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="wbFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#B56C82" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#B56C82" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 6" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={fmtDay} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            axisLine={false} tickLine={false} minTickGap={16} />
          <YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} tickFormatter={(v) => MOOD[v]}
            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--rose)", strokeOpacity: 0.3 }} />
          <Area type="monotone" dataKey="value" stroke="#B56C82" strokeWidth={2.4}
            fill="url(#wbFill)" dot={{ r: 3, fill: "#B56C82", strokeWidth: 0 }}
            activeDot={{ r: 5 }} isAnimationActive />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
