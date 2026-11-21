import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { Info } from "lucide-react";
import { ensureWorldMap } from "../utils/worldMap";
import ChartOptionsMenu from "./ChartOptionsMenu";

const COLORS = ["#9CAF88", "#E0A899", "#D9C98E", "#B8A9C9", "#A9B7A0", "#C9A9A0", "#9FBF9F", "#C7B8D6"];
const AXIS_LINE = "#EAE3D9";
const AXIS_TEXT = "#8A8176";

function trimZero(x) {
  return (Math.round(x * 10) / 10).toString();
}

function formatAxisNumber(v) {
  const n = Number(v);
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${trimZero(n / 1_000_000)}M`;
  if (abs >= 1_000) return `${trimZero(n / 1_000)}K`;
  return String(n);
}

const VALUE_AXIS_LABEL = { formatter: formatAxisNumber, color: AXIS_TEXT, fontSize: 11 };

function chartDescription(chart) {
  switch (chart.type) {
    case "line":
      return `${chart.series_label} totals aggregated by month, from your uploaded ${chart.x_label}. The dashed line marks the overall average.`;
    case "bar":
    case "hbar":
      return `${chart.series_label} summed per ${chart.x_label}, ranked highest to lowest.`;
    case "donut":
      return "Record count distribution across the top categories in this column.";
    case "scatter":
      return `Each point is one record, plotting ${chart.x_label} against ${chart.y_label} to reveal any relationship between them.`;
    case "stackedbar":
      return `${chart.y_label} by month, broken down and stacked by ${chart.series?.length ? "category" : ""}.`;
    case "groupedbar":
      return "Two metrics compared side-by-side for the same time period.";
    case "map":
      return "Countries shaded by total value — darker means higher. Drag to pan, scroll to zoom.";
    case "treemap":
      return "Box size represents each item's share of the total; smaller items are grouped into \"Other\".";
    case "histogram":
      return "How often values fall into each range — shows the overall shape of the distribution.";
    case "boxplot":
      return "Each box shows the middle 50% of values per category; the line is the median and dots are outliers.";
    case "heatmap":
      return "Correlation between every pair of numeric columns, from -1 (opposite) to 1 (move together).";
    default:
      return "";
  }
}

function buildOption(chart) {
  const base = {
    grid: { left: 40, right: 16, top: 30, bottom: 36 },
    tooltip: { trigger: "axis" },
    textStyle: { fontFamily: "Inter, system-ui, sans-serif", color: "#3A3530" },
  };

  switch (chart.type) {
    case "line":
      return {
        ...base,
        grid: { left: 50, right: 16, top: 30, bottom: 48 },
        xAxis: { type: "category", data: chart.x, name: chart.x_label, nameLocation: "middle", nameGap: 28, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", name: chart.y_label, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{
          name: chart.series_label, data: chart.y, type: "line", smooth: true,
          areaStyle: { color: "rgba(156,175,136,0.12)" }, lineStyle: { color: COLORS[0], width: 2 },
          itemStyle: { color: COLORS[0] },
          markLine: chart.average != null ? {
            silent: true, symbol: "none", label: { formatter: "Avg", color: AXIS_TEXT, fontSize: 10 },
            lineStyle: { color: "#C9BEB0", type: "dashed" },
            data: [{ yAxis: chart.average }],
          } : undefined,
        }],
      };
    case "bar":
      return {
        ...base,
        grid: { left: 50, right: 16, top: 30, bottom: 48 },
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: chart.x, name: chart.x_label, nameLocation: "middle", nameGap: 28, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", name: chart.y_label, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{ name: chart.series_label, data: chart.y, type: "bar", itemStyle: { color: COLORS[0], borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 }],
      };
    case "hbar":
      return {
        ...base,
        grid: { left: 100, right: 16, top: 20, bottom: 40 },
        xAxis: { type: "value", name: chart.y_label, nameLocation: "middle", nameGap: 28, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "category", data: chart.x, axisLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{ name: chart.series_label, data: chart.y, type: "bar", itemStyle: { color: COLORS[0], borderRadius: [0, 4, 4, 0] }, barMaxWidth: 20 }],
      };
    case "donut":
      return {
        ...base,
        tooltip: { trigger: "item" },
        legend: { bottom: 0, textStyle: { color: AXIS_TEXT, fontSize: 11 } },
        series: [{
          type: "pie", radius: ["45%", "72%"],
          data: chart.labels.map((l, i) => ({ name: l, value: chart.values[i], itemStyle: { color: COLORS[i % COLORS.length] } })),
          label: { show: false },
        }],
      };
    case "scatter":
      return {
        ...base,
        xAxis: { type: "value", name: chart.x_label, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", name: chart.y_label, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{ data: chart.points, type: "scatter", symbolSize: 7, itemStyle: { color: COLORS[0], opacity: 0.75 } }],
      };
    case "stackedbar":
      return {
        ...base,
        grid: { left: 50, right: 16, top: 24, bottom: 46 },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
        legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: AXIS_TEXT, fontSize: 11 } },
        xAxis: { type: "category", data: chart.x, axisLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: chart.series.map((s, i) => ({
          name: s.label, data: s.data, type: "bar", stack: "total",
          itemStyle: { color: COLORS[i % COLORS.length] }, barMaxWidth: 36,
        })),
      };
    case "groupedbar":
      return {
        ...base,
        grid: { left: 50, right: 16, top: 24, bottom: 46 },
        tooltip: { trigger: "axis" },
        legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: AXIS_TEXT, fontSize: 11 } },
        xAxis: { type: "category", data: chart.x, axisLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: chart.series.map((s, i) => ({
          name: s.label, data: s.data, type: "bar",
          itemStyle: { color: COLORS[i % COLORS.length], borderRadius: [3, 3, 0, 0] }, barMaxWidth: 16,
        })),
      };
    case "map": {
      const values = chart.items.map((i) => i.value);
      return {
        tooltip: { trigger: "item", formatter: (p) => `${p.name}: ${(p.value || 0).toLocaleString()}` },
        visualMap: {
          min: 0, max: Math.max(...values, 1), left: "left", bottom: 10,
          text: [`High (${formatAxisNumber(Math.max(...values, 1))})`, "Low (0)"], calculable: true,
          formatter: (v) => formatAxisNumber(v),
          inRange: { color: ["#F1EDE3", COLORS[0]] },
          textStyle: { color: AXIS_TEXT, fontSize: 10 },
        },
        series: [{
          type: "map", map: "world", roam: true,
          emphasis: { label: { show: true }, itemStyle: { areaColor: COLORS[1] } },
          itemStyle: { borderColor: "#fff", borderWidth: 0.5 },
          data: chart.items,
        }],
      };
    }
    case "treemap":
      return {
        tooltip: { formatter: (p) => `${p.name}: ${p.value.toLocaleString()}` },
        series: [{
          type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
          itemStyle: { borderColor: "#fff", borderWidth: 2, gapWidth: 2 },
          label: {
            fontSize: 11, color: "#fff", overflow: "truncate",
            formatter: (p) => (p.name.length > 12 ? `${p.name.slice(0, 11)}…` : p.name),
          },
          colorMappingBy: "index",
          color: COLORS,
          data: chart.items.map((it) => ({ name: it.name, value: it.value })),
        }],
      };
    case "histogram":
      return {
        ...base,
        xAxis: { type: "category", data: chart.x, axisLine: { lineStyle: { color: AXIS_LINE } } },
        yAxis: { type: "value", axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{ data: chart.y, type: "bar", itemStyle: { color: COLORS[1], borderRadius: [4, 4, 0, 0] } }],
      };
    case "boxplot":
      return {
        grid: { left: 50, right: 16, top: 20, bottom: 40 },
        tooltip: { trigger: "item" },
        xAxis: { type: "category", data: chart.labels, axisLine: { lineStyle: { color: AXIS_LINE } }, axisLabel: { color: AXIS_TEXT, fontSize: 11, interval: 0, rotate: chart.labels.length > 5 ? 30 : 0 } },
        yAxis: { type: "value", name: chart.y_label, nameTextStyle: { color: AXIS_TEXT, fontSize: 11 }, axisLabel: VALUE_AXIS_LABEL, splitLine: { lineStyle: { color: AXIS_LINE } } },
        series: [{
          type: "boxplot", data: chart.data,
          itemStyle: { color: COLORS[0] + "33", borderColor: COLORS[0] },
        }],
      };
    case "heatmap": {
      const values = chart.cells.map((c) => c[2]);
      return {
        grid: { left: 90, right: 16, top: 20, bottom: 70 },
        tooltip: { trigger: "item", formatter: (p) => `${chart.labels[p.data[0]]} vs ${chart.labels[p.data[1]]}: ${p.data[2]}` },
        xAxis: { type: "category", data: chart.labels, axisLabel: { color: AXIS_TEXT, fontSize: 10, rotate: 30 }, splitArea: { show: true } },
        yAxis: { type: "category", data: chart.labels, axisLabel: { color: AXIS_TEXT, fontSize: 10 }, splitArea: { show: true } },
        visualMap: {
          min: -1, max: 1, calculable: true, orient: "horizontal", left: "center", bottom: 0,
          inRange: { color: ["#D98888", "#F6F1EC", COLORS[0]] },
          textStyle: { color: AXIS_TEXT, fontSize: 10 },
        },
        series: [{
          type: "heatmap", data: chart.cells,
          label: { show: true, color: "#3A3530", fontSize: 10 },
        }],
      };
    }
    default:
      return base;
  }
}

export default function ChartRenderer({ chart, datasetId, onReplace, onReset, isCustom }) {
  const [mapReady, setMapReady] = useState(chart.type !== "map");

  useEffect(() => {
    if (chart.type === "map") {
      ensureWorldMap().then(() => setMapReady(true)).catch(() => setMapReady(false));
    }
  }, [chart.type]);

  return (
    <div className="bg-card border border-border rounded-lg p-3">
      <div className="flex items-center justify-between gap-1.5 mb-2 px-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="text-xs font-semibold text-text truncate">{chart.title}</div>
          <span className="tip-wrap text-muted shrink-0">
            <Info size={12} />
            <span className="tip-bubble">{chartDescription(chart)}</span>
          </span>
        </div>
        {datasetId && (
          <ChartOptionsMenu datasetId={datasetId} onReplace={onReplace} onReset={onReset} isCustom={isCustom} />
        )}
      </div>
      {mapReady ? (
        <ReactECharts option={buildOption(chart)} notMerge={true} lazyUpdate={true} style={{ height: 220 }} />
      ) : (
        <div className="h-[220px] flex items-center justify-center text-xs text-muted">Loading world map…</div>
      )}
    </div>
  );
}
