import { AlertTriangle, AlertCircle, Info } from "lucide-react";

const ISSUE_LABELS = {
  duplicate_records: "Duplicate records",
  missing_values: "Missing values",
  outliers: "Outliers",
  invalid_numerical_values: "Invalid numerical values",
  incorrect_data_type: "Incorrect data type",
  invalid_date_format: "Invalid date format",
  inconsistent_categorical_values: "Inconsistent category values",
  constant_column: "Constant column",
  empty_column: "Empty column",
};

const METHOD_LABELS = {
  drop_duplicates: "Remove duplicate rows",
  fill_mean: "Fill with column mean",
  fill_median: "Fill with column median",
  fill_mode: "Fill with most common value",
  convert_numeric: "Convert to numeric",
  standardize_dates: "Standardize date format",
  normalize_categories: "Normalize text (trim + title case)",
  cap_outliers_iqr: "Cap to normal range",
  remove_outliers_iqr: "Remove affected rows",
  drop_column: "Remove this column",
  fix_negative: "Replace negative values with median",
};

const METHOD_OPTIONS = {
  outliers: ["cap_outliers_iqr", "remove_outliers_iqr"],
};

const SEVERITY_STYLE = {
  high: { icon: AlertTriangle, color: "text-negative" },
  medium: { icon: AlertCircle, color: "text-muted" },
  low: { icon: Info, color: "text-muted" },
};

export default function IssueCard({ issue, selected, method, onToggle, onMethodChange }) {
  const { icon: Icon, color } = SEVERITY_STYLE[issue.severity] || SEVERITY_STYLE.low;
  const options = METHOD_OPTIONS[issue.issue_type] || [issue.recommended_method];

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-start gap-2">
          <Icon size={16} className={`mt-0.5 shrink-0 ${color}`} />
          <div>
            <div className="text-sm font-semibold text-text">
              {ISSUE_LABELS[issue.issue_type] || issue.issue_type}
              {issue.column && <span className="text-muted font-normal"> — {issue.column}</span>}
            </div>
            <div className="text-xs text-muted mt-0.5">{issue.description}</div>
          </div>
        </div>
        <label className="flex items-center gap-1.5 text-xs text-muted shrink-0 cursor-pointer">
          <input type="checkbox" checked={selected} onChange={(e) => onToggle(e.target.checked)} />
          Apply fix
        </label>
      </div>

      {issue.sample_records?.length > 0 && (
        <div className="overflow-x-auto mb-3 mt-2">
          <table className="text-xs w-full">
            <thead>
              <tr className="text-muted">
                {Object.keys(issue.sample_records[0]).map((k) => (
                  <th key={k} className="text-left pr-3 pb-1 font-medium">{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {issue.sample_records.map((row, i) => (
                <tr key={i} className="border-t border-border">
                  {Object.values(row).map((v, j) => (
                    <td key={j} className="pr-3 py-1 text-text">{v === null ? <span className="text-muted">—</span> : String(v)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {options.length > 1 ? (
        <select
          value={method}
          onChange={(e) => onMethodChange(e.target.value)}
          disabled={!selected}
          className="text-xs border border-border rounded-lg px-2 py-1.5 bg-bg text-text disabled:opacity-50"
        >
          {options.map((m) => <option key={m} value={m}>{METHOD_LABELS[m] || m}</option>)}
        </select>
      ) : (
        <div className="text-xs text-primary font-medium">{METHOD_LABELS[options[0]] || options[0]}</div>
      )}
    </div>
  );
}
