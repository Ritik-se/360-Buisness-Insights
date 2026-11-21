import { ArrowUp, ArrowDown } from "lucide-react";

export default function DetailedAnalysis({ segments }) {
  if (!segments) return null;
  const { dimension, metric, top, bottom } = segments;

  return (
    <div className="bg-card border border-border rounded-lg p-4 mb-6">
      <div className="text-sm font-semibold text-text mb-1">Detailed Analysis</div>
      <div className="text-xs text-muted mb-4">{metric} by {dimension}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-positive mb-2">
            <ArrowUp size={13} /> Top performing {dimension}
          </div>
          <ul className="space-y-1.5">
            {top.map((row) => (
              <li key={row.name} className="flex items-center justify-between text-sm">
                <span className="text-text">{row.name}</span>
                <span className="font-medium text-text">{row.value.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-negative mb-2">
            <ArrowDown size={13} /> Lowest performing {dimension}
          </div>
          <ul className="space-y-1.5">
            {bottom.map((row) => (
              <li key={row.name} className="flex items-center justify-between text-sm">
                <span className="text-text">{row.name}</span>
                <span className="font-medium text-text">{row.value.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
