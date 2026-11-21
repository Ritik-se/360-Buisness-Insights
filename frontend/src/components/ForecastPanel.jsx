import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { TrendingUp, Info } from "lucide-react";
import { getForecast } from "../api/client";

export default function ForecastPanel({ datasetId }) {
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getForecast(datasetId, 3)
      .then(setForecast)
      .catch((err) => setError(err?.response?.data?.detail || "Could not generate a forecast for this dataset."))
      .finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) return <p className="text-sm text-muted">Fitting a forecast model…</p>;
  if (error) return <p className="text-sm text-muted bg-card border border-border rounded-lg p-4">{error}</p>;
  if (!forecast) return null;

  const historyX = forecast.history.x;
  const forecastX = forecast.forecast.x;
  const allX = [...historyX, ...forecastX];
  const historySeries = [...forecast.history.y, ...Array(forecastX.length).fill(null)];
  const bridge = forecast.history.y[forecast.history.y.length - 1];
  const forecastSeries = [...Array(historyX.length - 1).fill(null), bridge, ...forecast.forecast.y];

  const option = {
    grid: { left: 50, right: 16, top: 30, bottom: 48 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0, textStyle: { color: "#8A8176", fontSize: 11 } },
    xAxis: { type: "category", data: allX, axisLine: { lineStyle: { color: "#EAE3D9" } } },
    yAxis: { type: "value", name: forecast.metric, nameTextStyle: { color: "#8A8176", fontSize: 11 }, splitLine: { lineStyle: { color: "#EAE3D9" } } },
    series: [
      { name: "Actual", data: historySeries, type: "line", smooth: true, lineStyle: { color: "#9CAF88", width: 2 }, itemStyle: { color: "#9CAF88" } },
      { name: "Forecast", data: forecastSeries, type: "line", smooth: true, lineStyle: { color: "#E0A899", width: 2, type: "dashed" }, itemStyle: { color: "#E0A899" } },
    ],
  };

  const MODEL_LABELS = {
    linear: "Linear regression", polynomial: "Polynomial regression",
    exponential_smoothing: "Exponential smoothing", arima: "ARIMA",
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-text mb-1">
        <TrendingUp size={16} className="text-primary" /> Forecast — {forecast.metric}
      </div>
      <p className="text-xs text-muted mb-3">
        Next {forecastX.length} months, projected from your data's own history. {forecast.method}
      </p>
      <ReactECharts option={option} notMerge style={{ height: 280 }} />
      <div className="flex items-center gap-1.5 mt-3 text-xs text-muted">
        <Info size={12} />
        {forecast.accuracy_pct != null
          ? `Backtested accuracy: ${forecast.accuracy_pct}% using ${MODEL_LABELS[forecast.model_used] || forecast.model_used} (how well this model would have predicted the most recent known months).`
          : "Not enough history to measure backtested accuracy."}
      </div>

      {forecast.model_comparison?.length > 1 && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="text-xs font-semibold text-text mb-2">Model comparison (lower = better fit)</div>
          <table className="text-xs w-full">
            <thead>
              <tr className="text-muted">
                <th className="text-left pb-1">Model</th>
                <th className="text-right pb-1">MAE</th>
                <th className="text-right pb-1">RMSE</th>
                <th className="text-right pb-1">MAPE</th>
              </tr>
            </thead>
            <tbody>
              {forecast.model_comparison.map((c) => (
                <tr key={c.model} className={`border-t border-border ${c.model === forecast.model_used ? "text-text font-medium" : "text-muted"}`}>
                  <td className="py-1">{MODEL_LABELS[c.model] || c.model}{c.model === forecast.model_used && " ✓"}</td>
                  <td className="text-right">{c.mae.toLocaleString()}</td>
                  <td className="text-right">{c.rmse.toLocaleString()}</td>
                  <td className="text-right">{c.mape}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
