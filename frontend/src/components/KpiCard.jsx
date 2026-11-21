import { TrendingUp, TrendingDown, Info } from "lucide-react";

const CURRENCY_SYMBOLS = ["$", "₹", "€", "£", "¥"];

function formatValue(kpi) {
  const v = kpi.value;
  if (kpi.aggregation === "ratio_pct") return `${v.toLocaleString()}%`;
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function tooltipFor(kpi) {
  if (kpi.label === "Total Records") return "The total number of rows in your uploaded dataset.";
  if (kpi.aggregation === "ratio_pct") return `Computed as a ratio between two related columns in your data, shown as a percentage.`;
  const verb = kpi.aggregation === "average" ? "Average" : "Sum";
  let text = `${verb} of the '${kpi.label}' column across all records.`;
  if (kpi.delta_pct != null) text += " Compared against the previous time period in your data.";
  return text;
}

export default function KpiCard({ kpi }) {
  const hasDelta = kpi.delta_pct !== null && kpi.delta_pct !== undefined;
  const isPositive = hasDelta && kpi.delta_pct >= 0;
  const isCurrencySymbol = CURRENCY_SYMBOLS.includes(kpi.unit);
  const unitPrefix = isCurrencySymbol ? kpi.unit : "";
  const unitSuffix = !isCurrencySymbol && kpi.unit
    ? (kpi.unit === "%" ? "%" : ` ${kpi.unit}`)
    : "";

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-1.5 mb-2">
        <div className="text-xs font-medium text-muted">{kpi.label}</div>
        <span className="tip-wrap text-muted">
          <Info size={12} />
          <span className="tip-bubble">{tooltipFor(kpi)}</span>
        </span>
      </div>
      <div className="flex items-baseline flex-wrap gap-x-2 gap-y-1">
        <div className="text-2xl font-bold text-text whitespace-nowrap">
          {unitPrefix}{formatValue(kpi)}
        </div>
        {unitSuffix && <div className="text-xs font-semibold text-muted">{unitSuffix.trim()}</div>}
        {hasDelta && (
          <div className={`flex items-center gap-1 text-xs font-semibold shrink-0 ${isPositive ? "text-positive" : "text-negative"}`}>
            {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {Math.abs(kpi.delta_pct)}%
          </div>
        )}
      </div>
      <div className="text-[11px] text-muted mt-1.5 capitalize">
        {kpi.aggregation.replace("_", " ")}
        {kpi.previous_value != null && ` · vs ${kpi.previous_value.toLocaleString()} last period`}
      </div>
    </div>
  );
}
