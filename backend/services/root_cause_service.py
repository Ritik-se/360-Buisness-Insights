"""Root cause / contribution analysis. Decomposes a metric's period-over-period
change across each dimension column to find which categories explain most of
the movement. This is a contribution analysis — it shows what moved, not
necessarily why — and is always labeled that way, never as proven causation."""

from typing import Dict, List, Optional

import pandas as pd

from services.semantic_engine import _metric_priority


def analyze(df: pd.DataFrame, tags: Dict[str, dict], metric: str, date_col: str) -> Optional[dict]:
    dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    values = pd.to_numeric(df[metric], errors="coerce")
    valid = dates.notna() & values.notna()
    if valid.sum() < 4:
        return None

    monthly = pd.DataFrame({"date": dates[valid], "value": values[valid]}).set_index("date") \
        .resample("MS")["value"].sum().dropna()
    if len(monthly) < 2:
        return None

    previous_period, current_period = monthly.index[-2], monthly.index[-1]
    previous_total, current_total = float(monthly.iloc[-2]), float(monthly.iloc[-1])
    if previous_total == 0:
        return None
    overall_change_pct = round((current_total - previous_total) / previous_total * 100, 1)
    overall_change_abs = round(current_total - previous_total, 2)

    dimension_cols = [c for c, t in tags.items() if t["role"] in ("dimension", "geo") and 2 <= t["cardinality"] <= 30]
    contributions = []

    for dim in dimension_cols:
        mask_prev = valid & (dates.dt.to_period("M") == previous_period.to_period("M"))
        mask_curr = valid & (dates.dt.to_period("M") == current_period.to_period("M"))
        prev_by_cat = values[mask_prev].groupby(df[dim][mask_prev]).sum()
        curr_by_cat = values[mask_curr].groupby(df[dim][mask_curr]).sum()
        categories = set(prev_by_cat.index) | set(curr_by_cat.index)
        rows = []
        for cat in categories:
            p = float(prev_by_cat.get(cat, 0))
            c = float(curr_by_cat.get(cat, 0))
            delta = c - p
            if abs(delta) < 1e-9:
                continue
            rows.append({
                "category": str(cat), "previous": round(p, 2), "current": round(c, 2),
                "change": round(delta, 2),
                "share_of_total_change": round(delta / overall_change_abs * 100, 1) if overall_change_abs else None,
            })
        rows.sort(key=lambda r: abs(r["change"]), reverse=True)
        if rows:
            contributions.append({"dimension": dim, "top_contributors": rows[:5]})

    return {
        "metric": metric,
        "previous_period": previous_period.strftime("%b %Y"),
        "current_period": current_period.strftime("%b %Y"),
        "previous_total": round(previous_total, 2),
        "current_total": round(current_total, 2),
        "overall_change_pct": overall_change_pct,
        "overall_change_abs": overall_change_abs,
        "contributions": contributions,
        "note": "This shows which categories contributed most to the change (contribution analysis), "
                "not a proven cause — other factors outside this dataset may also be involved.",
    }
