const ROLE_LABEL = {
  metric: "Metric", currency_metric: "Metric (currency)", count_metric: "Metric (count)",
  rating_metric: "Metric (rating)", dimension: "Dimension", geo: "Geography",
  date: "Date", text: "Text", identifier: "Identifier",
};

export default function ColumnProfileTable({ columns }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-sm font-semibold text-text mb-3">Column profile</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted border-b border-border">
              <th className="py-2 pr-4">Column</th>
              <th className="py-2 pr-4">Detected role</th>
              <th className="py-2 pr-4">Type</th>
              <th className="py-2 pr-4">Missing</th>
              <th className="py-2 pr-4">Unique values</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((c) => (
              <tr key={c.name} className="border-b border-border last:border-0">
                <td className="py-2 pr-4 font-medium text-text">{c.name}</td>
                <td className="py-2 pr-4 text-muted">{ROLE_LABEL[c.role] || c.role}</td>
                <td className="py-2 pr-4 text-muted">{c.dtype}</td>
                <td className="py-2 pr-4">
                  {c.missing_count > 0 ? (
                    <span className="text-negative">{c.missing_count} ({c.missing_pct}%)</span>
                  ) : (
                    <span className="text-positive">None</span>
                  )}
                </td>
                <td className="py-2 pr-4 text-muted">{c.unique_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
