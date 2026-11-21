import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { FileText, Sparkles, ShieldCheck, AlertTriangle, TrendingUp, Lightbulb } from "lucide-react";
import { getExecutiveReport } from "../api/client";
import { exportElementAsPdf } from "../utils/exportReport";

export default function Report({ dashboardData }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!dashboardData?.dataset_id) return;
    setReport(null);
    setError(null);
    getExecutiveReport(dashboardData.dataset_id)
      .then(setReport)
      .catch(() => setError("Could not generate the executive report for this dataset."));
  }, [dashboardData?.dataset_id]);

  if (!dashboardData) return <Navigate to="/upload" replace />;

  async function handleExport() {
    setExporting(true);
    try {
      await exportElementAsPdf("report-capture", `${report.filename.replace(/\.(csv|xlsx|xls)$/i, "")}_executive_report.pdf`);
    } catch {
      setError("Could not generate the PDF. Try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="p-6 max-w-[1000px] mx-auto">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-text">Executive Report</h1>
          <p className="text-sm text-muted mt-1">A one-page summary of KPIs, data quality, risks and recommendations — every figure here is computed, not estimated.</p>
        </div>
        {report && (
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-border rounded-lg bg-card hover:bg-card-soft disabled:opacity-60"
          >
            <FileText size={14} /> {exporting ? "Generating…" : "Download PDF"}
          </button>
        )}
      </div>

      {error && <p className="text-sm text-negative bg-card border border-border rounded-lg p-4">{error}</p>}
      {!report && !error && <p className="text-sm text-muted">Assembling the report…</p>}

      {report && (
        <div id="report-capture" className="space-y-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm font-semibold text-text mb-1">{report.filename}</div>
            <div className="text-xs text-muted">{report.row_count.toLocaleString()} rows · {report.column_count} columns</div>
          </div>

          {report.ai_summary ? (
            <div className="bg-primary-soft border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-text mb-2">
                <Sparkles size={16} className="text-primary" /> AI Executive Summary
              </div>
              <p className="text-sm text-text leading-relaxed">{report.ai_summary}</p>
            </div>
          ) : (
            <p className="text-xs text-muted px-1">
              {report.ai_configured
                ? "AI narrative summary unavailable for this report — showing computed findings below."
                : "AI narrative summary needs a free GEMINI_API_KEY on the backend. Showing computed findings below."}
            </p>
          )}

          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm font-semibold text-text mb-3">KPI Summary</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {report.kpis.map((k) => (
                <div key={k.label} className="border border-border rounded-lg p-3">
                  <div className="text-xs text-muted">{k.label}</div>
                  <div className="text-lg font-bold text-text">{k.value.toLocaleString()} {k.unit}</div>
                  {k.delta_pct != null && (
                    <div className={`text-xs ${k.delta_pct >= 0 ? "text-positive" : "text-negative"}`}>
                      {k.delta_pct >= 0 ? "+" : ""}{k.delta_pct}% vs last period
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
              <ShieldCheck size={16} className="text-primary" /> Data Quality
            </div>
            <div className="flex items-center gap-3 mb-2">
              <div className="text-2xl font-bold text-text">{report.data_quality.score}</div>
              <div className="text-xs text-muted">/ 100</div>
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs text-muted">
              <div>Completeness: <span className="text-text font-medium">{report.data_quality.completeness}%</span></div>
              <div>Uniqueness: <span className="text-text font-medium">{report.data_quality.uniqueness}%</span></div>
              <div>Validity: <span className="text-text font-medium">{report.data_quality.validity}%</span></div>
              <div>Consistency: <span className="text-text font-medium">{report.data_quality.consistency}%</span></div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
              <Lightbulb size={16} className="text-primary" /> Key Insights
            </div>
            {report.insights.length ? (
              <ul className="space-y-1.5 text-sm text-text">
                {report.insights.map((t, i) => <li key={i} className="flex gap-2"><span className="text-muted">•</span>{t}</li>)}
              </ul>
            ) : <p className="text-sm text-muted">No significant findings.</p>}
          </div>

          {report.anomalies.length > 0 && (
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
                <AlertTriangle size={16} className="text-primary" /> Anomalies Detected
              </div>
              <ul className="space-y-1.5 text-sm text-text">
                {report.anomalies.map((a, i) => (
                  <li key={i} className="flex gap-2"><span className="text-muted">•</span>{a.description}</li>
                ))}
              </ul>
            </div>
          )}

          {report.forecast && (
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-text mb-2">
                <TrendingUp size={16} className="text-primary" /> Forecast — {report.forecast.metric}
              </div>
              <p className="text-sm text-text mb-1">
                {report.forecast.forecast.x.map((d, i) => `${d}: ${report.forecast.forecast.y[i].toLocaleString()}`).join(" · ")}
              </p>
              <p className="text-xs text-muted">{report.forecast.method} Backtest accuracy: {report.forecast.accuracy_pct}%.</p>
            </div>
          )}

          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm font-semibold text-text mb-3">Recommendations</div>
            <ul className="space-y-1.5 text-sm text-text">
              {report.recommendations.map((r, i) => <li key={i} className="flex gap-2"><span className="text-muted">•</span>{r}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
