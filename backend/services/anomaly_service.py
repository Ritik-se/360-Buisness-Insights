"""Anomaly detection. Picks the method based on the data's own shape rather
than always using one technique: Isolation Forest for multivariate anomalies
when there are enough numeric columns and rows, IQR for a single column or a
small dataset, and rolling z-score for unusual swings over time. Flags
observations as "worth a look", not "fraud" — a statistical outlier is not
automatically an error."""

from typing import Dict, List

import numpy as np
import pandas as pd

from services.semantic_engine import _metric_priority


def _iqr_anomalies(df: pd.DataFrame, col: str) -> dict:
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(series) < 5:
        return None
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return None
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    if mask.sum() == 0:
        return None
    affected = series[mask]
    return {
        "method": "IQR", "scope": "column", "column": col,
        "affected_count": int(mask.sum()),
        "severity": "high" if mask.mean() > 0.1 else "medium",
        "description": f"{int(mask.sum())} '{col}' value(s) fall far outside the normal range ({round(lower,2)} to {round(upper,2)}).",
        "samples": [{"value": round(float(v), 2)} for v in affected.head(5)],
    }


def _isolation_forest_anomalies(df: pd.DataFrame, metric_cols: List[str]) -> dict:
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return None

    numeric = df[metric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric) < 20:
        return None

    model = IsolationForest(contamination=0.05, random_state=42)
    preds = model.fit_predict(numeric)
    scores = model.decision_function(numeric)
    anomaly_mask = preds == -1
    if anomaly_mask.sum() == 0:
        return None

    anomaly_idx = numeric.index[anomaly_mask]
    samples = []
    for idx in list(anomaly_idx)[:5]:
        samples.append({c: round(float(numeric.loc[idx, c]), 2) for c in metric_cols})

    return {
        "method": "Isolation Forest", "scope": "row", "column": None,
        "affected_count": int(anomaly_mask.sum()),
        "severity": "high" if anomaly_mask.mean() > 0.08 else "medium",
        "description": f"{int(anomaly_mask.sum())} records look unusual across the combination of {', '.join(metric_cols)} together (not just one column alone).",
        "samples": samples,
    }


def _time_series_anomalies(df: pd.DataFrame, date_col: str, metric_col: str) -> dict:
    dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    values = pd.to_numeric(df[metric_col], errors="coerce")
    valid = dates.notna() & values.notna()
    if valid.sum() < 6:
        return None
    series = pd.DataFrame({"date": dates[valid], "value": values[valid]}).set_index("date")
    monthly = series.resample("MS")["value"].sum().dropna()
    if len(monthly) < 5:
        return None

    rolling_mean = monthly.rolling(window=3, min_periods=3).mean()
    rolling_std = monthly.rolling(window=3, min_periods=3).std()
    z = (monthly - rolling_mean) / rolling_std.replace(0, np.nan)
    flagged = z[z.abs() > 2].dropna()
    if flagged.empty:
        return None

    samples = [{"period": idx.strftime("%b %Y"), "value": round(float(monthly[idx]), 2), "expected": round(float(rolling_mean[idx]), 2)}
               for idx in flagged.index]
    return {
        "method": "Rolling z-score", "scope": "time", "column": metric_col,
        "affected_count": len(flagged),
        "severity": "medium",
        "description": f"{len(flagged)} month(s) of '{metric_col}' deviate sharply from their recent trend.",
        "samples": samples,
    }


def detect_anomalies(df: pd.DataFrame, tags: Dict[str, dict]) -> List[dict]:
    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    results = []

    if len(metric_cols) >= 2:
        multivariate = _isolation_forest_anomalies(df, metric_cols)
        if multivariate:
            results.append(multivariate)

    # per-column IQR, mainly useful when multivariate detection wasn't possible or to
    # surface a specific column's own extreme values
    for col in metric_cols:
        result = _iqr_anomalies(df, col)
        if result:
            results.append(result)

    if date_cols and metric_cols:
        primary = max(metric_cols, key=lambda c: _metric_priority(c, tags[c]))
        ts_result = _time_series_anomalies(df, date_cols[0], primary)
        if ts_result:
            results.append(ts_result)

    return results[:8]
