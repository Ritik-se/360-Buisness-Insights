import { useEffect, useState } from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { getAnomalies } from "../api/client";

const SEVERITY_COLOR = { high: "text-negative", medium: "text-muted", low: "text-muted" };

export default function AnomalyPanel({ datasetId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    getAnomalies(datasetId).then(setData).catch(() => setError("Could not run anomaly detection on this dataset."));
  }, [datasetId]);

  if (error) return <p className="text-sm text-muted bg-card border border-border rounded-lg p-4">{error}</p>;
  if (!data) return <p className="text-sm text-muted">Scanning for anomalies…</p>;
  if (data.anomalies.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-6 text-center text-sm text-muted">
        No significant anomalies detected across {data.row_count.toLocaleString()} records.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {data.anomalies.map((a, i) => (
        <div key={i} className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-start gap-2 mb-2">
            <AlertTriangle size={16} className={`mt-0.5 shrink-0 ${SEVERITY_COLOR[a.severity]}`} />
            <div>
              <div className="text-sm font-semibold text-text">
                {a.affected_count} flagged — {a.method}
                {a.column && <span className="text-muted font-normal"> · {a.column}</span>}
              </div>
              <div className="text-xs text-muted mt-0.5">{a.description}</div>
            </div>
          </div>
          {a.samples?.length > 0 && (
            <div className="overflow-x-auto mt-2">
              <table className="text-xs w-full">
                <thead>
                  <tr className="text-muted">
                    {Object.keys(a.samples[0]).map((k) => <th key={k} className="text-left pr-4 pb-1 font-medium">{k}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {a.samples.map((s, j) => (
                    <tr key={j} className="border-t border-border">
                      {Object.values(s).map((v, k) => <td key={k} className="pr-4 py-1 text-text">{String(v)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
      <p className="text-[11px] text-muted flex items-center gap-1.5">
        <ShieldAlert size={12} /> A flagged record is unusual, not necessarily wrong — review before acting on it.
      </p>
    </div>
  );
}
