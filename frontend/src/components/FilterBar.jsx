import { Search, RotateCcw } from "lucide-react";

export default function FilterBar({ filters, value, onChange, onReset }) {
  if (!filters) return null;
  const { date_column, date_min, date_max, dimension_column, dimension_values } = filters;
  const hasAny = date_column || dimension_column;
  if (!hasAny) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-3 mb-6 flex items-center gap-3 flex-wrap">
      {date_column && (
        <>
          <input
            type="date"
            value={value.start_date || ""}
            min={date_min}
            max={date_max}
            onChange={(e) => onChange({ ...value, start_date: e.target.value })}
            className="text-sm border border-border rounded-lg px-2 py-1.5 bg-bg text-text"
          />
          <span className="text-sm text-muted">to</span>
          <input
            type="date"
            value={value.end_date || ""}
            min={date_min}
            max={date_max}
            onChange={(e) => onChange({ ...value, end_date: e.target.value })}
            className="text-sm border border-border rounded-lg px-2 py-1.5 bg-bg text-text"
          />
        </>
      )}

      {dimension_column && (
        <select
          value={value.dimension_value || ""}
          onChange={(e) => onChange({ ...value, dimension_value: e.target.value })}
          className="text-sm border border-border rounded-lg px-2 py-1.5 bg-bg text-text"
        >
          <option value="">All {dimension_column}</option>
          {dimension_values.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      )}

      <div className="flex items-center gap-2 border border-border rounded-lg px-2 py-1.5 flex-1 min-w-[160px] bg-bg">
        <Search size={14} className="text-muted" />
        <input
          type="text"
          placeholder="Search records…"
          value={value.search || ""}
          onChange={(e) => onChange({ ...value, search: e.target.value })}
          className="bg-transparent outline-none text-sm w-full text-text"
        />
      </div>

      <button
        onClick={onReset}
        className="flex items-center gap-1.5 text-sm font-medium border border-border rounded-lg px-3 py-1.5 hover:bg-card-soft text-text"
      >
        <RotateCcw size={14} /> Reset
      </button>
    </div>
  );
}
