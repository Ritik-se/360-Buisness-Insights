import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ShieldCheck } from "lucide-react";
import IssueCard from "../components/IssueCard";
import { profileIssues, previewCleaning, applyCleaning } from "../api/client";

export default function DataPrep({ dashboardData, onCleaned }) {
  const [issues, setIssues] = useState(null);
  const [selection, setSelection] = useState({}); // { issueKey: {selected, method} }
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [applying, setApplying] = useState(false);
  const navigate = useNavigate();

  const datasetId = dashboardData?.dataset_id;

  useEffect(() => {
    if (!datasetId) return;
    setIssues(null);
    setPreview(null);
    profileIssues(datasetId).then((res) => {
      setIssues(res.issues);
      const init = {};
      res.issues.forEach((issue, i) => {
        const key = `${i}-${issue.column}-${issue.issue_type}`;
        init[key] = { selected: true, method: issue.recommended_method };
      });
      setSelection(init);
    }).catch(() => setError("Could not analyze this dataset."));
  }, [datasetId]);

  if (!datasetId) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-text mb-1">Data Preparation</h1>
        <p className="text-sm text-muted">Upload a dataset first to review and clean it.</p>
      </div>
    );
  }

  function buildOperations() {
    return issues
      .map((issue, i) => {
        const key = `${i}-${issue.column}-${issue.issue_type}`;
        const sel = selection[key];
        if (!sel?.selected) return null;
        return { column: issue.column, method: sel.method };
      })
      .filter(Boolean);
  }

  async function handlePreview() {
    setError(null);
    try {
      const result = await previewCleaning(datasetId, buildOperations());
      setPreview(result);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not generate a preview.");
    }
  }

  async function handleApply() {
    setApplying(true);
    setError(null);
    try {
      const result = await applyCleaning(datasetId, buildOperations());
      onCleaned(result);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not apply cleaning.");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-text mb-1">Data Preparation</h1>
      <p className="text-sm text-muted mb-6">
        Issues detected in <span className="font-medium text-text">{dashboardData.filename}</span>.
        Review each one, adjust the fix if needed, then preview before applying. The original file is never changed —
        cleaning creates a new dataset.
      </p>

      {!issues && <p className="text-sm text-muted">Analyzing dataset…</p>}
      {issues && issues.length === 0 && (
        <div className="bg-card border border-border rounded-lg p-6 text-center text-sm text-muted">
          No issues detected — this dataset looks clean.
        </div>
      )}

      {issues && issues.length > 0 && (
        <>
          <div className="space-y-3 mb-6">
            {issues.map((issue, i) => {
              const key = `${i}-${issue.column}-${issue.issue_type}`;
              const sel = selection[key] || { selected: true, method: issue.recommended_method };
              return (
                <IssueCard
                  key={key}
                  issue={issue}
                  selected={sel.selected}
                  method={sel.method}
                  onToggle={(checked) => setSelection((s) => ({ ...s, [key]: { ...sel, selected: checked } }))}
                  onMethodChange={(m) => setSelection((s) => ({ ...s, [key]: { ...sel, method: m } }))}
                />
              );
            })}
          </div>

          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={handlePreview}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card hover:bg-card-soft text-sm font-medium text-text"
            >
              <Sparkles size={15} /> Preview changes
            </button>
            <button
              onClick={handleApply}
              disabled={applying}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              <ShieldCheck size={15} /> {applying ? "Applying…" : "Apply cleaning"}
            </button>
          </div>

          {error && <p className="text-sm text-negative mb-4">{error}</p>}

          {preview && (
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="text-sm font-semibold text-text mb-3">Preview</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
                <div>
                  <div className="text-muted text-xs">Rows</div>
                  <div className="text-text font-medium">{preview.summary.rows_before} → {preview.summary.rows_after}</div>
                </div>
                <div>
                  <div className="text-muted text-xs">Columns</div>
                  <div className="text-text font-medium">{preview.summary.columns_before} → {preview.summary.columns_after}</div>
                </div>
                <div>
                  <div className="text-muted text-xs">Data Quality</div>
                  <div className="text-text font-medium">{preview.quality_before.score} → {preview.quality_after.score}</div>
                </div>
                <div>
                  <div className="text-muted text-xs">Columns removed</div>
                  <div className="text-text font-medium">{preview.summary.columns_removed.join(", ") || "None"}</div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="text-xs w-full">
                  <thead>
                    <tr className="text-muted">
                      {preview.preview_rows[0] && Object.keys(preview.preview_rows[0]).map((k) => (
                        <th key={k} className="text-left pr-3 pb-1 font-medium">{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview_rows.map((row, i) => (
                      <tr key={i} className="border-t border-border">
                        {Object.values(row).map((v, j) => (
                          <td key={j} className="pr-3 py-1 text-text">{v === null ? <span className="text-muted">—</span> : String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
