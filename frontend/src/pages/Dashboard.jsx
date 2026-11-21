import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Lightbulb, ShieldCheck, Download, FileText } from "lucide-react";
import KpiCard from "../components/KpiCard";
import ChartRenderer from "../components/ChartRenderer";
import FilterBar from "../components/FilterBar";
import DetailedAnalysis from "../components/DetailedAnalysis";
import ColumnProfileTable from "../components/ColumnProfileTable";
import ForecastPanel from "../components/ForecastPanel";
import AnomalyPanel from "../components/AnomalyPanel";
import RootCausePanel from "../components/RootCausePanel";
import WhatIfPanel from "../components/WhatIfPanel";
import { api, exportDatasetUrl } from "../api/client";
import { exportElementAsPdf } from "../utils/exportReport";

const KPI_GRID_COLS = {
  1: "md:grid-cols-1", 2: "md:grid-cols-2", 3: "md:grid-cols-3",
  4: "md:grid-cols-4", 5: "md:grid-cols-5", 6: "md:grid-cols-6",
};

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "segment", label: "Detail by segment" },
  { id: "trend", label: "Trend analysis" },
  { id: "anomalies", label: "Anomaly Detection" },
  { id: "forecast", label: "Forecast" },
  { id: "whatif", label: "What-If Analysis" },
  { id: "quality", label: "Data quality" },
];

const TREND_CHART_TYPES = ["line", "stackedbar", "groupedbar"];

function InsightsPanel({ insights }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
        <Lightbulb size={16} className="text-primary" /> Business Insights
      </div>
      {insights.length ? (
        <ul className="space-y-2 text-sm text-text">
          {insights.map((text, i) => <li key={i} className="flex gap-2"><span className="text-muted">•</span>{text}</li>)}
        </ul>
      ) : (
        <p className="text-sm text-muted">No significant findings for this dataset yet.</p>
      )}
    </div>
  );
}

export default function Dashboard({ data: initialData }) {
  const [data, setData] = useState(initialData);
  const [filterValue, setFilterValue] = useState({});
  const [loading, setLoading] = useState(false);
  const [filterError, setFilterError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [exportingPdf, setExportingPdf] = useState(false);
  const [chartOverrides, setChartOverrides] = useState({});

  useEffect(() => { setData(initialData); setFilterValue({}); setActiveTab("overview"); setChartOverrides({}); }, [initialData]);

  useEffect(() => {
    if (!initialData) return;
    const hasFilter = filterValue.start_date || filterValue.end_date || filterValue.dimension_value || filterValue.search;
    if (!hasFilter) { setData(initialData); setFilterError(null); return; }

    const timeout = setTimeout(() => {
      setLoading(true);
      api.get(`/api/dashboard/${initialData.dataset_id}`, { params: filterValue })
        .then((res) => { setData(res.data); setFilterError(null); })
        .catch((err) => setFilterError(err?.response?.data?.detail || "No records match these filters."))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timeout);
  }, [filterValue, initialData]);

  if (!initialData) return <Navigate to="/upload" replace />;

  const { filename, row_count, column_count, duplicate_count, kpis, charts, insights, data_quality, uploaded_at, filters, segments, columns } = data;
  const title = filename.replace(/\.(csv|xlsx|xls)$/i, "").replace(/[_-]+/g, " ");
  const trendCharts = charts.filter((c) => TREND_CHART_TYPES.includes(c.type));
  const otherCharts = charts.filter((c) => !TREND_CHART_TYPES.includes(c.type));

  function renderOverridableChart(c) {
    const key = `${c.type}-${c.title}`;
    const override = chartOverrides[key];
    const shown = override || c;
    return (
      <ChartRenderer
        key={key}
        chart={shown}
        datasetId={data.dataset_id}
        isCustom={Boolean(override)}
        onReplace={(newChart) => setChartOverrides((m) => ({ ...m, [key]: newChart }))}
        onReset={() => setChartOverrides((m) => { const n = { ...m }; delete n[key]; return n; })}
      />
    );
  }

  async function handleExportReport() {
    setExportingPdf(true);
    try {
      await exportElementAsPdf("dashboard-capture", `${title.replace(/\s+/g, "_")}_report.pdf`);
    } catch (err) {
      setFilterError("Could not generate the PDF report. Try again.");
    } finally {
      setExportingPdf(false);
    }
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="text-xs text-muted mb-1">Dashboards / <span className="text-text font-medium">{title}</span></div>
      <div className="flex items-start justify-between mb-3 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-text capitalize">{title} Dashboard</h1>
          <p className="text-sm text-muted mt-1">
            {filename} · {row_count.toLocaleString()} rows · {column_count} columns · uploaded {new Date(uploaded_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={exportDatasetUrl(data.dataset_id, filterValue)}
            download
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-border rounded-lg bg-card hover:bg-card-soft"
            title="Download the currently filtered data as CSV"
          >
            <Download size={14} /> Export data
          </a>
          <button
            onClick={handleExportReport}
            disabled={exportingPdf}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-border rounded-lg bg-card hover:bg-card-soft disabled:opacity-60"
            title="Download this dashboard view as a PDF report"
          >
            <FileText size={14} /> {exportingPdf ? "Generating…" : "Export report"}
          </button>
        </div>
      </div>

      <div id="dashboard-capture">
      <div className="flex items-center gap-5 border-b border-border mb-4 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-2 -mb-px border-b-2 transition-colors ${
              activeTab === tab.id ? "border-primary text-primary font-medium" : "border-transparent text-muted hover:text-text"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <FilterBar filters={filters} value={filterValue} onChange={setFilterValue} onReset={() => setFilterValue({})} />

      {loading && <p className="text-sm text-muted mb-4">Updating dashboard for selected filters…</p>}
      {filterError && <p className="text-sm text-negative mb-4">{filterError}</p>}

      {kpis.length > 0 && (
        <div className={`grid gap-3 mb-4 grid-cols-2 ${KPI_GRID_COLS[Math.min(kpis.length, 6)]}`}>
          {kpis.map((k) => <KpiCard key={k.label} kpi={k} />)}
        </div>
      )}

      {activeTab === "overview" && (
        <>
          {charts.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mb-4">
              {charts.map(renderOverridableChart)}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <InsightsPanel insights={insights} />
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
                <ShieldCheck size={16} className="text-primary" /> Data Quality
              </div>
              <div className="flex items-center gap-3 mb-3">
                <div className="text-3xl font-bold text-text">{data_quality.score}</div>
                <div className="text-xs text-muted">/ 100 · {duplicate_count} duplicate rows found</div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted">
                <div>Completeness: <span className="text-text font-medium">{data_quality.completeness}%</span></div>
                <div>Uniqueness: <span className="text-text font-medium">{data_quality.uniqueness}%</span></div>
                <div>Validity: <span className="text-text font-medium">{data_quality.validity}%</span></div>
                <div>Consistency: <span className="text-text font-medium">{data_quality.consistency}%</span></div>
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === "segment" && (
        <>
          <RootCausePanel datasetId={data.dataset_id} />
          <DetailedAnalysis segments={segments} />
          {otherCharts.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mb-4">
              {otherCharts.map((c) => <ChartRenderer key={`${c.type}-${c.title}`} chart={c} />)}
            </div>
          )}
          {!segments && !otherCharts.length && (
            <p className="text-sm text-muted">No categorical breakdown is available for this dataset.</p>
          )}
        </>
      )}

      {activeTab === "trend" && (
        <>
          {trendCharts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              {trendCharts.map((c) => <ChartRenderer key={`${c.type}-${c.title}`} chart={c} />)}
            </div>
          ) : (
            <p className="text-sm text-muted mb-4">No date column was detected, so no trend-over-time chart is available.</p>
          )}
          <InsightsPanel insights={insights} />
        </>
      )}

      {activeTab === "anomalies" && (
        <AnomalyPanel datasetId={data.dataset_id} />
      )}

      {activeTab === "forecast" && (
        <ForecastPanel datasetId={data.dataset_id} />
      )}

      {activeTab === "whatif" && (
        <WhatIfPanel datasetId={data.dataset_id} />
      )}

      {activeTab === "quality" && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
              <ShieldCheck size={16} className="text-primary" /> Data Quality
            </div>
            <div className="flex items-center gap-3 mb-3">
              <div className="text-3xl font-bold text-text">{data_quality.score}</div>
              <div className="text-xs text-muted">/ 100 · {duplicate_count} duplicate rows found</div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-muted mb-2">
              <div>Completeness: <span className="text-text font-medium">{data_quality.completeness}%</span></div>
              <div>Uniqueness: <span className="text-text font-medium">{data_quality.uniqueness}%</span></div>
              <div>Validity: <span className="text-text font-medium">{data_quality.validity}%</span></div>
              <div>Consistency: <span className="text-text font-medium">{data_quality.consistency}%</span></div>
            </div>
            <p className="text-[11px] text-muted">{data_quality.formula}</p>
          </div>
          <ColumnProfileTable columns={columns} />
        </div>
      )}
      </div>
    </div>
  );
}
