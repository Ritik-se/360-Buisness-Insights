import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { getRootCause } from "../api/client";

export default function RootCausePanel({ datasetId }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleOpen() {
    setOpen(true);
    if (data || loading) return;
    setLoading(true);
    try {
      setData(await getRootCause(datasetId));
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not break down this change.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button onClick={handleOpen} className="flex items-center gap-1.5 text-xs text-primary font-medium hover:underline mb-4">
        <HelpCircle size={13} /> Why did this change?
      </button>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 mb-6">
      <div className="text-sm font-semibold text-text mb-1">
        {loading ? "Analyzing…" : data ? `Why ${data.metric} changed ${data.overall_change_pct >= 0 ? "+" : ""}${data.overall_change_pct}%` : "Root cause"}
      </div>
      {error && <p className="text-sm text-negative">{error}</p>}
      {data && (
        <>
          <p className="text-xs text-muted mb-4">
            {data.previous_period} ({data.previous_total.toLocaleString()}) → {data.current_period} ({data.current_total.toLocaleString()})
          </p>
          <div className="space-y-4">
            {data.contributions.map((c) => (
              <div key={c.dimension}>
                <div className="text-xs font-semibold text-muted mb-1.5 uppercase tracking-wide">{c.dimension}</div>
                <ul className="space-y-1">
                  {c.top_contributors.map((row) => (
                    <li key={row.category} className="flex items-center justify-between text-sm">
                      <span className="text-text">{row.category}</span>
                      <span className={row.change >= 0 ? "text-positive" : "text-negative"}>
                        {row.change >= 0 ? "+" : ""}{row.change.toLocaleString()}
                        {row.share_of_total_change != null && ` (${row.share_of_total_change}% of total change)`}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-muted mt-4">{data.note}</p>
        </>
      )}
    </div>
  );
}
