"""Executive report assembly. Every field in the returned payload is built
from numbers the rest of the engine already computed (KPIs, data quality,
insights, anomalies, forecast) — nothing here invents a figure. Recommendations
are generated from fixed, explainable thresholds on those computed numbers;
an LLM is only ever used to narrate those same facts in prose, never to
produce new numbers."""

import json
import os
from typing import Dict, List, Optional

import pandas as pd

from services import ai_assistant_service, anomaly_service, forecasting, semantic_engine


def _recommendations(kpis: List[dict], quality: dict, anomalies: List[dict],
                      forecast: Optional[dict], segments: Optional[dict]) -> List[str]:
    recs: List[str] = []

    if quality["score"] < 70:
        recs.append(
            f"Data quality is {quality['score']}/100 — review completeness ({quality['completeness']}%) "
            f"and consistency ({quality['consistency']}%) in Data Preparation before relying on these numbers."
        )
    elif quality["score"] < 90:
        recs.append(f"Data quality is {quality['score']}/100 — acceptable, but worth a cleaning pass to reach 90+.")

    declining = [k for k in kpis if k["delta_pct"] is not None and k["delta_pct"] <= -10]
    for k in declining[:3]:
        recs.append(f"'{k['label']}' dropped {abs(k['delta_pct'])}% vs the previous period — investigate the cause before it compounds.")

    growing = [k for k in kpis if k["delta_pct"] is not None and k["delta_pct"] >= 15]
    for k in growing[:2]:
        recs.append(f"'{k['label']}' grew {k['delta_pct']}% vs the previous period — identify what drove it and reinforce it.")

    high_severity = [a for a in anomalies if a.get("severity") == "high"]
    for a in high_severity[:2]:
        recs.append(f"{a['description']} ({a['method']}) — worth a manual review of these records.")

    if segments:
        top = segments["top"][0] if segments["top"] else None
        bottom = segments["bottom"][0] if segments["bottom"] else None
        if top and bottom and bottom["value"] > 0 and top["value"] / bottom["value"] >= 3:
            recs.append(
                f"'{top['name']}' outperforms '{bottom['name']}' by {round(top['value']/bottom['value'],1)}x on "
                f"{segments['metric']} — consider applying whatever is working for '{top['name']}' more broadly, "
                f"or investigating what's limiting '{bottom['name']}'."
            )

    if forecast:
        hist_avg = sum(forecast["history"]["y"]) / len(forecast["history"]["y"])
        fcast_avg = sum(forecast["forecast"]["y"]) / len(forecast["forecast"]["y"])
        if hist_avg and fcast_avg < hist_avg * 0.9:
            recs.append(
                f"The {forecast['model_used']} forecast projects '{forecast['metric']}' trending down "
                f"over the next {len(forecast['forecast']['x'])} period(s) (accuracy {forecast['accuracy_pct']}% on backtest) — plan accordingly."
            )
        elif hist_avg and fcast_avg > hist_avg * 1.1:
            recs.append(
                f"The {forecast['model_used']} forecast projects '{forecast['metric']}' trending up "
                f"over the next {len(forecast['forecast']['x'])} period(s) (accuracy {forecast['accuracy_pct']}% on backtest) — plan capacity/inventory accordingly."
            )

    if not recs:
        recs.append("No significant risks or opportunities crossed the reporting thresholds — the dataset looks stable.")

    return recs[:8]


def _ai_summary(filename: str, kpis: List[dict], quality: dict, insights: List[str],
                anomalies: List[dict], forecast: Optional[dict], recommendations: List[str]) -> Optional[str]:
    if not ai_assistant_service.is_configured():
        return None
    try:
        from google import genai
    except ImportError:
        return None

    facts = {
        "dataset": filename,
        "kpis": [{"label": k["label"], "value": k["value"], "unit": k["unit"], "delta_pct": k["delta_pct"]} for k in kpis],
        "data_quality_score": quality["score"],
        "insights": insights[:6],
        "anomaly_count": len(anomalies),
        "forecast": {"metric": forecast["metric"], "model": forecast["model_used"], "accuracy_pct": forecast["accuracy_pct"]} if forecast else None,
        "recommendations": recommendations,
    }

    prompt = (
        "Here are pre-computed business facts from a dataset, as JSON. Write a short (3-5 sentence) "
        "executive summary paragraph in plain business language, narrating ONLY these facts — do not "
        "introduce any number that isn't in the JSON below.\n\n" + json.dumps(facts, default=str)
    )

    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = ai_assistant_service._generate_with_retry(client, model=ai_assistant_service.GEMINI_MODEL, contents=prompt)
        return (response.text or "").strip() or None
    except Exception:
        return None


def build_report(df: pd.DataFrame, tags: Dict[str, dict], filename: str) -> dict:
    kpis = semantic_engine.generate_kpis(df, tags)
    quality = semantic_engine.data_quality_score(df)
    insights = semantic_engine.generate_insights(df, tags, kpis)
    segments = semantic_engine.top_bottom_segments(df, tags)
    anomalies = anomaly_service.detect_anomalies(df, tags)

    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    forecast = None
    if metric_cols and date_cols:
        primary = max(metric_cols, key=lambda c: semantic_engine._metric_priority(c, tags[c]))
        forecast = forecasting.forecast_metric(df, date_cols[0], primary, periods=3)

    recommendations = _recommendations(kpis, quality, anomalies, forecast, segments)
    ai_summary = _ai_summary(filename, kpis, quality, insights, anomalies, forecast, recommendations)

    return {
        "filename": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "kpis": kpis,
        "data_quality": quality,
        "insights": insights,
        "segments": segments,
        "anomalies": anomalies,
        "forecast": forecast,
        "recommendations": recommendations,
        "ai_summary": ai_summary,
        "ai_configured": ai_assistant_service.is_configured(),
    }
