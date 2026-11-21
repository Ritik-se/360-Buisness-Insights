import { useEffect, useState } from "react";
import { Beaker } from "lucide-react";
import { getChartOptions, simulateWhatIf } from "../api/client";

export default function WhatIfPanel({ datasetId }) {
  const [metrics, setMetrics] = useState(null);
  const [adjustments, setAdjustments] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getChartOptions(datasetId).then((o) => setMetrics(o.metrics));
  }, [datasetId]);

  async function run() {
    const payload = Object.entries(adjustments)
      .filter(([, v]) => v !== "" && v != null && Number(v) !== 0)
      .map(([column, pct_change]) => ({ column, pct_change: Number(pct_change) }));
    if (payload.length === 0) {
      setError("Set at least one non-zero % assumption first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await simulateWhatIf(datasetId, payload));
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not run this simulation.");
    } finally {
      setLoading(false);
    }
  }

  if (!metrics) return <p className="text-sm text-muted">Loading columns…</p>;

  return (
    <div className="space-y-4">
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-text mb-1">
          <Beaker size={16} className="text-primary" /> What-If Analysis
        </div>
        <p className="text-xs text-muted mb-4">
          Set a % assumption for one or more columns to see the estimated impact on every KPI.
          This recalculates real formulas on adjusted data — it's a simulation, not historical fact.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          {metrics.map((m) => (
            <div key={m}>
              <label className="text-xs text-muted block mb-1">{m} (%)</label>
              <input
                type="number" placeholder="0"
                value={adjustments[m] ?? ""}
                onChange={(e) => setAdjustments((a) => ({ ...a, [m]: e.target.value }))}
                className="w-full text-sm border border-border rounded-lg px-2 py-1.5 bg-bg text-text outline-none focus:border-primary"
              />
            </div>
          ))}
        </div>
        <button onClick={run} disabled={loading} className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-60">
          {loading ? "Simulating…" : "Run simulation"}
        </button>
        {error && <p className="text-sm text-negative mt-2">{error}</p>}
      </div>

      {result && (
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm font-semibold text-text mb-3">
            Estimated impact of {result.adjustments.map((a) => `${a.column} ${a.pct_change >= 0 ? "+" : ""}${a.pct_change}%`).join(", ")}
          </div>
          <table className="text-sm w-full">
            <thead>
              <tr className="text-muted text-xs">
                <th className="text-left pb-2">KPI</th>
                <th className="text-right pb-2">Actual</th>
                <th className="text-right pb-2">Simulated</th>
                <th className="text-right pb-2">Change</th>
              </tr>
            </thead>
            <tbody>
              {result.comparison.map((row) => (
                <tr key={row.label} className="border-t border-border">
                  <td className="py-2 text-text">{row.label}</td>
                  <td className="py-2 text-right text-muted">{row.actual.toLocaleString()}</td>
                  <td className="py-2 text-right text-text font-medium">{row.simulated.toLocaleString()}</td>
                  <td className={`py-2 text-right ${row.change_pct >= 0 ? "text-positive" : "text-negative"}`}>
                    {row.change_pct != null ? `${row.change_pct >= 0 ? "+" : ""}${row.change_pct}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
