import { useEffect, useState } from "react";
import { Settings2 } from "lucide-react";
import { getChartOptions, buildCustomChart } from "../api/client";

const TYPE_LABELS = {
  bar: "Bar", hbar: "Horizontal bar", line: "Line (over time)", donut: "Donut",
  scatter: "Scatter", histogram: "Histogram", boxplot: "Box plot",
};

export default function ChartOptionsMenu({ datasetId, onReplace, onReset, isCustom }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState(null);
  const [type, setType] = useState("bar");
  const [metric, setMetric] = useState("");
  const [metric2, setMetric2] = useState("");
  const [dimension, setDimension] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && !options) {
      getChartOptions(datasetId).then((res) => {
        setOptions(res);
        setMetric(res.metrics[0] || "");
        setMetric2(res.metrics[1] || "");
        setDimension(res.dimensions[0] || "");
      });
    }
  }, [open, datasetId, options]);

  async function apply() {
    setError(null);
    try {
      const chart = await buildCustomChart(datasetId, { chart_type: type, metric, metric2, dimension });
      onReplace(chart);
      setOpen(false);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not build that chart.");
    }
  }

  const needsDimension = ["bar", "hbar", "donut", "boxplot"].includes(type);
  const needsMetric2 = type === "scatter";

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="text-muted hover:text-text" title="Change this chart">
        <Settings2 size={13} />
      </button>
      {open && (
        <div className="absolute right-0 top-5 z-20 bg-card border border-border rounded-lg p-3 w-56 shadow-lg">
          {!options ? (
            <p className="text-xs text-muted">Loading columns…</p>
          ) : (
            <div className="space-y-2">
              <select value={type} onChange={(e) => setType(e.target.value)} className="w-full text-xs border border-border rounded px-2 py-1 bg-bg text-text">
                {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              {type !== "donut" && (
                <select value={metric} onChange={(e) => setMetric(e.target.value)} className="w-full text-xs border border-border rounded px-2 py-1 bg-bg text-text">
                  {options.metrics.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              )}
              {needsMetric2 && (
                <select value={metric2} onChange={(e) => setMetric2(e.target.value)} className="w-full text-xs border border-border rounded px-2 py-1 bg-bg text-text">
                  {options.metrics.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              )}
              {needsDimension && (
                <select value={dimension} onChange={(e) => setDimension(e.target.value)} className="w-full text-xs border border-border rounded px-2 py-1 bg-bg text-text">
                  {options.dimensions.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              )}
              {error && <p className="text-[11px] text-negative">{error}</p>}
              <div className="flex gap-2">
                <button onClick={apply} className="flex-1 text-xs bg-primary text-white rounded px-2 py-1 font-medium hover:opacity-90">Apply</button>
                {isCustom && (
                  <button onClick={() => { onReset(); setOpen(false); }} className="text-xs border border-border rounded px-2 py-1 text-muted">Reset</button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
