"""Dynamic, dataset-agnostic analysis engine.

Pipeline: tag_columns -> generate_kpis / recommend_charts / generate_insights
/ data_quality_score. Nothing here assumes a fixed schema or a fixed list of
business categories — every output is derived from whatever columns are
actually present in the uploaded file.
"""

import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

KEYWORD_ROLES = {
    "currency_metric": ["revenue", "sales", "profit", "expense", "cost", "spend",
                         "price", "amount", "income", "margin", "budget", "cogs"],
    "count_metric": ["quantity", "qty", "units", "clicks", "impressions", "conversions",
                      "visitors", "count", "volume", "orders", "stock", "inventory"],
    "rating_metric": ["rating", "score", "stars"],
    "date": ["date", "month", "year", "period", "day", "timestamp"],
    "geo": ["region", "country", "state", "city", "territory", "location", "zip",
            "postal", "warehouse"],
    "dimension": ["category", "segment", "department", "channel", "product", "type",
                  "status", "team", "campaign", "brand"],
    "identifier": ["id", "code", "sku", "uuid"],
    "text": ["review", "comment", "feedback", "description", "notes", "summary"],
}

RATIO_PAIRS = [
    ("clicks", "impressions", "CTR"),
    ("conversions", "clicks", "Conversion Rate"),
    ("profit", "revenue", "Margin"),
    ("cogs", "revenue", "COGS Ratio"),
]

#: Exact country names as they appear in the echarts world.json (map/json/world.json, v4.9.0 build)
#: this is what the map renderer matches against, so output names must be byte-for-byte identical.
WORLD_MAP_COUNTRIES = {
    "Afghanistan", "Albania", "Algeria", "Angola", "Argentina", "Armenia", "Australia", "Austria",
    "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
    "Bolivia", "Bosnia and Herz.", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
    "Cambodia", "Cameroon", "Canada", "Central African Rep.", "Chad", "Chile", "China", "Colombia",
    "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Rep.", "Côte d'Ivoire", "Dem. Rep. Congo",
    "Dem. Rep. Korea", "Denmark", "Djibouti", "Dominican Rep.", "Ecuador", "Egypt", "El Salvador",
    "Eq. Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia",
    "Georgia", "Germany", "Ghana", "Greece", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti",
    "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
    "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Korea", "Kuwait", "Kyrgyzstan", "Lao PDR",
    "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Lithuania", "Luxembourg", "Macedonia",
    "Madagascar", "Malawi", "Malaysia", "Mali", "Malta", "Mauritania", "Mauritius", "Mexico", "Moldova",
    "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nepal", "Netherlands",
    "New Zealand", "Nicaragua", "Niger", "Nigeria", "Norway", "Oman", "Pakistan", "Palestine", "Panama",
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania",
    "Russia", "Rwanda", "S. Sudan", "Saudi Arabia", "Senegal", "Serbia", "Sierra Leone", "Singapore",
    "Slovakia", "Slovenia", "Somalia", "South Africa", "Spain", "Sri Lanka", "Sudan", "Suriname",
    "Swaziland", "Sweden", "Switzerland", "Syria", "São Tomé and Principe", "Tajikistan", "Tanzania",
    "Thailand", "Timor-Leste", "Togo", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
    "Uzbekistan", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
}

_WORLD_MAP_LOOKUP = {name.lower(): name for name in WORLD_MAP_COUNTRIES}

COUNTRY_ALIASES = {
    "usa": "United States", "us": "United States", "u.s.a.": "United States", "u.s.": "United States",
    "america": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "u.a.e.": "United Arab Emirates", "emirates": "United Arab Emirates",
    "russian federation": "Russia",
    "south korea": "Korea", "korea, south": "Korea", "republic of korea": "Korea",
    "north korea": "Dem. Rep. Korea", "korea, north": "Dem. Rep. Korea",
    "czech republic": "Czech Rep.", "czechia": "Czech Rep.",
    "bosnia and herzegovina": "Bosnia and Herz.",
    "ivory coast": "Côte d'Ivoire", "cote d'ivoire": "Côte d'Ivoire",
    "laos": "Lao PDR",
    "democratic republic of congo": "Dem. Rep. Congo", "dr congo": "Dem. Rep. Congo",
    "congo-kinshasa": "Dem. Rep. Congo", "drc": "Dem. Rep. Congo",
    "republic of congo": "Congo", "congo-brazzaville": "Congo",
    "swaziland": "Swaziland", "eswatini": "Swaziland",
    "north macedonia": "Macedonia", "burma": "Myanmar",
    "south sudan": "S. Sudan",
    "antigua and barbuda": "Antigua and Barb.",
    "holland": "Netherlands", "the netherlands": "Netherlands",
    "central african republic": "Central African Rep.",
    "equatorial guinea": "Eq. Guinea",
}


def _match_countries(series: pd.Series):
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0, {}
    mapping = {}
    matched = 0
    for v in values.unique():
        key = v.strip().lower()
        canonical = COUNTRY_ALIASES.get(key) or _WORLD_MAP_LOOKUP.get(key)
        if canonical:
            mapping[v] = canonical
            matched += 1
    ratio = matched / len(values.unique())
    return ratio, mapping


def _norm(name: str) -> str:
    """Normalizes a column name to lowercase, space-separated words — splitting
    snake_case/kebab-case AND camelCase/PascalCase (e.g. 'PerformanceRating' ->
    'performance rating'), so keyword matching works regardless of the naming
    convention the uploaded file happens to use."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name.strip())
    return re.sub(r"[_\-]+", " ", spaced.lower())


def _keyword_match(norm_name: str) -> Optional[str]:
    for role, keywords in KEYWORD_ROLES.items():
        if any(re.search(rf"\b{re.escape(kw)}\b", norm_name) for kw in keywords):
            return role
    return None


def tag_columns(df: pd.DataFrame) -> Dict[str, dict]:
    """Returns {column_name: {role, dtype_kind, cardinality}} for every column."""
    tags = {}
    n = len(df)
    for col in df.columns:
        norm = _norm(col)
        series = df[col]
        keyword_role = _keyword_match(norm)
        is_numeric = pd.api.types.is_numeric_dtype(series)
        nunique = series.nunique(dropna=True)
        cardinality_ratio = nunique / n if n else 0

        # pandas.to_datetime "succeeds" on almost any plain integer (treating it as a
        # nanosecond/epoch timestamp), so only attempt loose date parsing for non-numeric
        # columns, or numeric columns whose name itself suggests a date.
        if not is_numeric or keyword_role == "date":
            parsed_dates = pd.to_datetime(series, errors="coerce", format="mixed")
            date_ratio = parsed_dates.notna().mean() if n else 0
        else:
            date_ratio = 0

        if keyword_role == "identifier" or (cardinality_ratio > 0.9 and not is_numeric and nunique > 20):
            role = "identifier"
        elif date_ratio > 0.8:
            role = "date"
        elif keyword_role == "geo":
            role = "geo"
        elif keyword_role == "text" or (not is_numeric and series.dropna().astype(str).str.len().mean() > 40):
            role = "text"
        elif is_numeric:
            role = keyword_role if keyword_role in ("currency_metric", "count_metric", "rating_metric") else "metric"
        elif keyword_role == "dimension" or (not is_numeric and cardinality_ratio < 0.5):
            role = "dimension"
        else:
            role = "dimension"

        tags[col] = {
            "role": role,
            "is_numeric": is_numeric,
            "cardinality": int(nunique),
            "cardinality_ratio": round(float(cardinality_ratio), 3),
        }
    return tags


def _is_unit_rate(norm: str) -> bool:
    """True for per-unit/per-item rate fields — these are rates, not additive totals,
    and should never be summed or chosen as the headline metric over a real total like
    Sales or Revenue. Covers explicit 'unit price'/'unit cost'/'per unit' phrasing AND
    a bare 'price' field (e.g. 'Item Price', 'List Price', 'Price') — a column is almost
    never literally named just "price" unless it's a per-unit rate; a real total is
    named 'revenue', 'sales', 'amount', 'total price', etc. instead."""
    if re.search(r"\btotal\b", norm):
        return False
    if re.search(r"\bunit\b.*\b(price|cost)\b|\b(price|cost)\b.*\bunit\b|\bper unit\b", norm):
        return True
    return bool(re.search(r"\bprice\b", norm))


def _metric_priority(col: str, tag: dict) -> int:
    norm = _norm(col)
    if _is_unit_rate(norm):
        return 0
    if any(kw in norm for kw in ("revenue", "sales", "profit")):
        return 3
    if tag["role"] == "currency_metric":
        return 3
    if tag["role"] in ("count_metric", "rating_metric"):
        return 2
    return 1


CURRENCY_SYMBOLS = {"$": "$", "₹": "₹", "€": "€", "£": "£", "¥": "¥"}


def _unit_for(col: str, tag: dict, series: pd.Series) -> str:
    norm = _norm(col)

    # Explicit unit hint in the column name itself, e.g. "Weight (kg)", "Price ($)", "Revenue (USD)"
    paren_match = re.search(r"\(([^)]+)\)\s*$", col.strip())
    if paren_match:
        hint = paren_match.group(1).strip()
        if hint:
            return hint
    for symbol in CURRENCY_SYMBOLS:
        if symbol in col:
            return symbol

    if tag["role"] == "rating_metric":
        clean = series.dropna()
        if len(clean) and clean.max() <= 5:
            return "/5"
        if len(clean) and clean.max() <= 10:
            return "/10"
        return ""
    if "percent" in norm or norm.endswith(" rate") or "margin" in norm:
        return "%"
    if tag["role"] == "count_metric":
        return "units"
    return ""


def generate_kpis(df: pd.DataFrame, tags: Dict[str, dict], max_kpis: int = 6) -> List[dict]:
    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    date_col = date_cols[0] if date_cols else None

    ranked = sorted(metric_cols, key=lambda c: _metric_priority(c, tags[c]), reverse=True)
    kpis: List[dict] = []

    for col in ranked:
        if len(kpis) >= max_kpis:
            break
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        norm = _norm(col)
        use_avg = (
            tags[col]["role"] == "rating_metric" or "rate" in norm or "%" in col or "margin" in norm
            or "discount" in norm or _is_unit_rate(norm)
        )
        value = float(series.mean()) if use_avg else float(series.sum())

        delta_pct, previous_value = None, None
        if date_col:
            delta_pct, previous_value = _period_over_period_change(df, date_col, col, use_avg)

        kpis.append({
            "label": col,
            "value": round(value, 2),
            "unit": _unit_for(col, tags[col], series),
            "aggregation": "average" if use_avg else "sum",
            "delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
            "previous_value": round(previous_value, 2) if previous_value is not None else None,
        })

    for num_a, num_b, ratio_label in RATIO_PAIRS:
        if len(kpis) >= max_kpis:
            break
        col_a = next((c for c in df.columns if num_a in _norm(c)), None)
        col_b = next((c for c in df.columns if num_b in _norm(c)), None)
        if col_a and col_b and col_a in metric_cols and col_b in metric_cols:
            a = pd.to_numeric(df[col_a], errors="coerce").sum()
            b = pd.to_numeric(df[col_b], errors="coerce").sum()
            if b:
                kpis.append({
                    "label": ratio_label,
                    "value": round(float(a / b * 100), 2),
                    "unit": "%",
                    "aggregation": "ratio_pct",
                    "delta_pct": None,
                    "previous_value": None,
                })

    if len(kpis) < max_kpis:
        kpis.append({
            "label": "Total Records",
            "value": float(len(df)),
            "unit": "rows",
            "aggregation": "count",
            "delta_pct": None,
            "previous_value": None,
        })

    return kpis[:max_kpis]


def _period_over_period_change(df: pd.DataFrame, date_col: str, metric_col: str, use_avg: bool):
    dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    values = pd.to_numeric(df[metric_col], errors="coerce")
    valid = dates.notna() & values.notna()
    if valid.sum() < 4:
        return None, None
    frame = pd.DataFrame({"date": dates[valid], "value": values[valid]})
    monthly = frame.set_index("date").resample("MS")["value"].agg("mean" if use_avg else "sum").dropna()
    if len(monthly) < 2:
        return None, None
    previous, current = monthly.iloc[-2], monthly.iloc[-1]
    if previous == 0:
        return None, None
    return float((current - previous) / previous * 100), float(previous)


def _grouped_by_dimension(df: pd.DataFrame, dim: str, tags: Dict[str, dict], metric: str) -> pd.Series:
    """Groups `metric` by `dim`, using alias-aware country grouping for a well-matched geo
    column instead of raw string grouping (so 'USA' and 'United States' aren't double-counted)."""
    values = pd.to_numeric(df[metric], errors="coerce")
    if tags.get(dim, {}).get("role") == "geo":
        ratio, mapping = _match_countries(df[dim])
        if ratio >= 0.6 and len(mapping) >= 2:
            return values.groupby(df[dim].astype(str).map(mapping)).sum().sort_values(ascending=False)
    return values.groupby(df[dim]).sum().sort_values(ascending=False)


def top_bottom_segments(df: pd.DataFrame, tags: Dict[str, dict], top_n: int = 3) -> Optional[dict]:
    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    dimension_cols = [c for c, t in tags.items() if t["role"] in ("dimension", "geo") and 2 <= t["cardinality"] <= 30]
    if not metric_cols or not dimension_cols:
        return None
    primary_metric = max(metric_cols, key=lambda c: _metric_priority(c, tags[c]))
    dim = dimension_cols[0]
    grouped = _grouped_by_dimension(df, dim, tags, primary_metric)
    if len(grouped) < 2:
        return None
    return {
        "dimension": dim,
        "metric": primary_metric,
        "top": [{"name": str(i), "value": round(float(v), 2)} for i, v in grouped.head(top_n).items()],
        "bottom": [{"name": str(i), "value": round(float(v), 2)} for i, v in grouped.tail(top_n).items()][::-1],
    }


def recommend_charts(df: pd.DataFrame, tags: Dict[str, dict], max_charts: int = 9) -> List[dict]:
    charts: List[dict] = []
    used_dims: set = set()
    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    dimension_cols = [c for c, t in tags.items() if t["role"] in ("dimension", "geo")]
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]

    primary_metric = max(metric_cols, key=lambda c: _metric_priority(c, tags[c])) if metric_cols else None

    # world map: a geo-tagged dimension whose values are mostly recognizable country names
    geo_cols = [c for c, t in tags.items() if t["role"] == "geo"]
    for geo_col in geo_cols:
        if not primary_metric:
            break
        ratio, mapping = _match_countries(df[geo_col])
        if ratio >= 0.6 and len(mapping) >= 2:
            mapped = df[geo_col].astype(str).map(mapping)
            grouped = pd.to_numeric(df[primary_metric], errors="coerce").groupby(mapped).sum()
            charts.append({
                "type": "map",
                "title": f"{primary_metric} by {geo_col} (world map)",
                "items": [{"name": name, "value": round(float(v), 2)} for name, v in grouped.items()],
            })
            used_dims.add(geo_col)
            break

    usable_dims = sorted(
        [c for c in dimension_cols if c not in used_dims and 2 <= tags[c]["cardinality"] <= 15],
        key=lambda c: tags[c]["cardinality"],
    )

    if date_cols and primary_metric:
        dates = pd.to_datetime(df[date_cols[0]], errors="coerce", format="mixed")
        values = pd.to_numeric(df[primary_metric], errors="coerce")
        valid = dates.notna() & values.notna()
        if valid.sum() >= 3:
            series = pd.DataFrame({"date": dates[valid], "value": values[valid]}).set_index("date")
            monthly = series.resample("MS")["value"].sum().dropna()
            if len(monthly) >= 2:
                avg = round(float(monthly.mean()), 2)
                charts.append({
                    "type": "line",
                    "title": f"{primary_metric} over time",
                    "x": [d.strftime("%b %Y") for d in monthly.index],
                    "y": [round(float(v), 2) for v in monthly.values],
                    "series_label": primary_metric,
                    "x_label": date_cols[0],
                    "y_label": primary_metric,
                    "average": avg,
                })

    # stacked bar: primary metric by month, broken down by the first usable dimension
    if date_cols and primary_metric and usable_dims and len(charts) < max_charts:
        dim = usable_dims[0]
        dates = pd.to_datetime(df[date_cols[0]], errors="coerce", format="mixed")
        values = pd.to_numeric(df[primary_metric], errors="coerce")
        valid = dates.notna() & values.notna() & df[dim].notna()
        frame = pd.DataFrame({"date": dates[valid], "value": values[valid], "dim": df[dim][valid]})
        if len(frame) >= 4:
            pivot = frame.pivot_table(index="date", columns="dim", values="value", aggfunc="sum").resample("MS").sum().fillna(0)
            if pivot.shape[0] >= 2 and pivot.shape[1] >= 2:
                used_dims.add(dim)
                charts.append({
                    "type": "stackedbar",
                    "title": f"{primary_metric} by month and {dim}",
                    "x": [d.strftime("%b %Y") for d in pivot.index],
                    "series": [{"label": str(col), "data": [round(float(v), 2) for v in pivot[col].values]} for col in pivot.columns],
                    "x_label": date_cols[0],
                    "y_label": primary_metric,
                })

    for dim in usable_dims:
        if len(charts) >= max_charts or not primary_metric or dim in used_dims:
            continue
        grouped = df.groupby(dim)[primary_metric].sum(numeric_only=True).sort_values(ascending=False).head(10)
        if grouped.empty:
            continue
        chart_type = "hbar" if tags[dim]["role"] == "geo" or len(grouped) > 6 else "bar"
        used_dims.add(dim)
        charts.append({
            "type": chart_type,
            "title": f"{primary_metric} by {dim}",
            "x": [str(i) for i in grouped.index],
            "y": [round(float(v), 2) for v in grouped.values],
            "series_label": primary_metric,
            "x_label": dim,
            "y_label": primary_metric,
        })
        if len(used_dims) >= 2:
            break

    # treemap: a higher-cardinality dimension not already used, e.g. accounts/products/SKUs
    treemap_dims = [c for c in dimension_cols if c not in used_dims and 4 <= tags[c]["cardinality"] <= 50]
    if treemap_dims and primary_metric and len(charts) < max_charts:
        dim = treemap_dims[0]
        grouped = df.groupby(dim)[primary_metric].sum(numeric_only=True).sort_values(ascending=False)
        if len(grouped) >= 3:
            used_dims.add(dim)
            top = grouped.head(9)
            items = [{"name": str(i), "value": round(float(v), 2)} for i, v in top.items()]
            remainder = grouped.iloc[9:].sum()
            if remainder > 0:
                items.append({"name": f"Other ({len(grouped) - 9})", "value": round(float(remainder), 2)})
            charts.append({
                "type": "treemap",
                "title": f"{primary_metric} by {dim}",
                "items": items,
            })

    if usable_dims and len(charts) < max_charts:
        dim = next((d for d in usable_dims if d not in used_dims), usable_dims[0])
        counts = df[dim].value_counts().head(6)
        charts.append({
            "type": "donut",
            "title": f"Distribution by {dim}",
            "labels": [str(i) for i in counts.index],
            "values": [int(v) for v in counts.values],
        })

    # Two metrics compared (groupedbar over time, or scatter otherwise). Totals-only
    # fields should drive this, not per-unit rates (e.g. Unit Price) — summing a rate
    # monthly, or plotting it against a total, isn't a meaningful comparison.
    comparable_metrics = sorted(
        [c for c in metric_cols if not _is_unit_rate(_norm(c))],
        key=lambda c: _metric_priority(c, tags[c]), reverse=True,
    )
    if len(comparable_metrics) < 2:
        comparable_metrics = sorted(metric_cols, key=lambda c: _metric_priority(c, tags[c]), reverse=True)

    # grouped bar: two metrics compared over time (e.g. won vs lost, revenue vs cost)
    if len(comparable_metrics) >= 2 and date_cols and len(charts) < max_charts:
        m1, m2 = comparable_metrics[0], comparable_metrics[1]
        dates = pd.to_datetime(df[date_cols[0]], errors="coerce", format="mixed")
        v1 = pd.to_numeric(df[m1], errors="coerce")
        v2 = pd.to_numeric(df[m2], errors="coerce")
        valid = dates.notna() & v1.notna() & v2.notna()
        if valid.sum() >= 4:
            frame = pd.DataFrame({"date": dates[valid], "a": v1[valid], "b": v2[valid]}).set_index("date")
            monthly = frame.resample("MS").sum()
            if len(monthly) >= 2:
                charts.append({
                    "type": "groupedbar",
                    "title": f"{m1} vs {m2} by month",
                    "x": [d.strftime("%b %Y") for d in monthly.index],
                    "series": [
                        {"label": m1, "data": [round(float(v), 2) for v in monthly["a"].values]},
                        {"label": m2, "data": [round(float(v), 2) for v in monthly["b"].values]},
                    ],
                    "x_label": date_cols[0], "y_label": "Value",
                })
    elif len(comparable_metrics) >= 2 and len(charts) < max_charts:
        a, b = comparable_metrics[0], comparable_metrics[1]
        pts = df[[a, b]].dropna()
        if len(pts) >= 5:
            charts.append({
                "type": "scatter",
                "title": f"{a} vs {b}",
                "x_label": a, "y_label": b,
                "points": [[round(float(r[a]), 2), round(float(r[b]), 2)] for _, r in pts.head(300).iterrows()],
            })

    if primary_metric and len(charts) < max_charts and not date_cols:
        series = pd.to_numeric(df[primary_metric], errors="coerce").dropna()
        if len(series) >= 5:
            counts, edges = np.histogram(series, bins=min(10, max(4, len(series) // 20 or 4)))
            charts.append({
                "type": "histogram",
                "title": f"Distribution of {primary_metric}",
                "x": [f"{edges[i]:.0f}-{edges[i+1]:.0f}" for i in range(len(edges) - 1)],
                "y": [int(c) for c in counts],
                "x_label": primary_metric,
                "y_label": "Record count",
            })

    # correlation heatmap across all numeric metrics (genuinely useful once there are
    # enough metrics to compare — two metrics are already shown as a scatter above)
    if len(metric_cols) >= 3 and len(charts) < max_charts:
        numeric_df = df[metric_cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr(numeric_only=True)
        cells = []
        for i, a in enumerate(metric_cols):
            for j, b in enumerate(metric_cols):
                val = corr.loc[a, b]
                cells.append([i, j, round(float(val), 2) if pd.notna(val) else 0])
        charts.append({
            "type": "heatmap",
            "title": "Correlation between metrics",
            "labels": metric_cols,
            "cells": cells,
        })

    # box plot: shows the spread/outliers of the primary metric per category, which a
    # bar chart (totals only) can't show
    if primary_metric and usable_dims and len(charts) < max_charts:
        dim = usable_dims[0]
        box_data, categories = [], []
        for name, group in df.groupby(dim)[primary_metric]:
            vals = pd.to_numeric(group, errors="coerce").dropna()
            if len(vals) < 3:
                continue
            q1, med, q3 = vals.quantile(0.25), vals.median(), vals.quantile(0.75)
            categories.append(str(name))
            box_data.append([round(float(vals.min()), 2), round(float(q1), 2), round(float(med), 2),
                              round(float(q3), 2), round(float(vals.max()), 2)])
        if len(box_data) >= 2:
            charts.append({
                "type": "boxplot",
                "title": f"{primary_metric} distribution by {dim}",
                "labels": categories,
                "data": box_data,
                "y_label": primary_metric,
            })

    return charts[:max_charts]


def generate_insights(df: pd.DataFrame, tags: Dict[str, dict], kpis: List[dict]) -> List[str]:
    insights: List[str] = []
    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    dimension_cols = [c for c, t in tags.items() if t["role"] in ("dimension", "geo") and 2 <= t["cardinality"] <= 15]

    for k in kpis:
        if k["delta_pct"] is not None:
            direction = "increased" if k["delta_pct"] >= 0 else "decreased"
            insights.append(f"{k['label']} {direction} by {abs(k['delta_pct'])}% compared to the previous period.")

    if len(metric_cols) >= 2:
        corr_matrix = df[metric_cols].corr(numeric_only=True)
        seen = set()
        for a in metric_cols:
            for b in metric_cols:
                if a == b or (b, a) in seen:
                    continue
                seen.add((a, b))
                val = corr_matrix.loc[a, b]
                if pd.notna(val) and abs(val) >= 0.6:
                    direction = "positively" if val > 0 else "negatively"
                    insights.append(f"'{a}' and '{b}' are strongly {direction} correlated (r={round(float(val),2)}).")

    primary_metric = max(metric_cols, key=lambda c: _metric_priority(c, tags[c])) if metric_cols else None
    if primary_metric and dimension_cols:
        dim = dimension_cols[0]
        grouped = _grouped_by_dimension(df, dim, tags, primary_metric)
        total = grouped.sum()
        if len(grouped) >= 2:
            top, bottom = grouped.index[0], grouped.index[-1]
            insights.append(f"'{top}' is the top-performing {dim} by {primary_metric} ({round(float(grouped.iloc[0]),2)}).")
            insights.append(f"'{bottom}' is the lowest-performing {dim} by {primary_metric} ({round(float(grouped.iloc[-1]),2)}).")
            if total:
                share = round(float(grouped.iloc[0] / total * 100), 1)
                if share >= 30:
                    insights.append(f"'{top}' alone accounts for {share}% of total {primary_metric} across all {dim} values.")
            if grouped.iloc[-1] > 0 and grouped.iloc[0] / grouped.iloc[-1] >= 3:
                ratio = round(float(grouped.iloc[0] / grouped.iloc[-1]), 1)
                insights.append(f"{primary_metric} varies widely by {dim} — the top value is {ratio}x the lowest.")

    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    if date_cols:
        parsed = pd.to_datetime(df[date_cols[0]], errors="coerce", format="mixed").dropna()
        if len(parsed) >= 2:
            span_days = (parsed.max() - parsed.min()).days
            insights.append(f"Data spans {span_days} days, from {parsed.min().strftime('%b %d, %Y')} to {parsed.max().strftime('%b %d, %Y')}.")

    if primary_metric:
        series = pd.to_numeric(df[primary_metric], errors="coerce").dropna()
        if len(series) >= 5:
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            outliers = series[(series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)]
            if len(outliers):
                insights.append(f"'{primary_metric}' has {len(outliers)} outlier value(s) outside the normal range.")
            cv = float(series.std() / series.mean()) if series.mean() else 0
            if cv >= 0.5:
                insights.append(f"'{primary_metric}' shows high variability across records (coefficient of variation: {round(cv,2)}).")

    return insights[:12]


def filter_metadata(df: pd.DataFrame, tags: Dict[str, dict]) -> dict:
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    dimension_cols = [c for c, t in tags.items() if t["role"] in ("dimension", "geo") and 2 <= t["cardinality"] <= 30]
    meta = {"date_column": None, "date_min": None, "date_max": None, "dimension_column": None, "dimension_values": []}
    if date_cols:
        parsed = pd.to_datetime(df[date_cols[0]], errors="coerce", format="mixed").dropna()
        if len(parsed):
            meta["date_column"] = date_cols[0]
            meta["date_min"] = parsed.min().strftime("%Y-%m-%d")
            meta["date_max"] = parsed.max().strftime("%Y-%m-%d")
    if dimension_cols:
        dim = dimension_cols[0]
        meta["dimension_column"] = dim
        meta["dimension_values"] = sorted(str(v) for v in df[dim].dropna().unique())
    return meta


def apply_filters(df: pd.DataFrame, date_col: Optional[str], start_date: Optional[str], end_date: Optional[str],
                   dimension_col: Optional[str], dimension_value: Optional[str], search: Optional[str]) -> pd.DataFrame:
    filtered = df
    if date_col and (start_date or end_date):
        parsed = pd.to_datetime(filtered[date_col], errors="coerce", format="mixed")
        mask = pd.Series(True, index=filtered.index)
        if start_date:
            mask &= parsed >= pd.to_datetime(start_date)
        if end_date:
            mask &= parsed <= pd.to_datetime(end_date)
        filtered = filtered[mask]
    if dimension_col and dimension_value:
        filtered = filtered[filtered[dimension_col].astype(str) == dimension_value]
    if search:
        text_cols = filtered.select_dtypes(exclude=[np.number]).columns
        if len(text_cols):
            mask = pd.Series(False, index=filtered.index)
            for col in text_cols:
                mask |= filtered[col].astype(str).str.contains(search, case=False, na=False)
            filtered = filtered[mask]
    return filtered


def available_chart_options(tags: Dict[str, dict]) -> dict:
    """Column choices for the manual chart-override UI."""
    metrics = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    dimensions = [c for c, t in tags.items() if t["role"] in ("dimension", "geo") and 2 <= t["cardinality"] <= 50]
    dates = [c for c, t in tags.items() if t["role"] == "date"]
    return {"metrics": metrics, "dimensions": dimensions, "dates": dates}


def build_custom_chart(df: pd.DataFrame, tags: Dict[str, dict], chart_type: str,
                        metric: Optional[str] = None, dimension: Optional[str] = None,
                        metric2: Optional[str] = None) -> dict:
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    date_col = date_cols[0] if date_cols else None

    if chart_type == "line" and metric and date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
        values = pd.to_numeric(df[metric], errors="coerce")
        valid = dates.notna() & values.notna()
        series = pd.DataFrame({"date": dates[valid], "value": values[valid]}).set_index("date")
        monthly = series.resample("MS")["value"].sum().dropna()
        return {"type": "line", "title": f"{metric} over time", "x": [d.strftime("%b %Y") for d in monthly.index],
                "y": [round(float(v), 2) for v in monthly.values], "series_label": metric,
                "x_label": date_col, "y_label": metric, "average": round(float(monthly.mean()), 2) if len(monthly) else None}

    if chart_type in ("bar", "hbar") and metric and dimension:
        grouped = df.groupby(dimension)[metric].sum(numeric_only=True).sort_values(ascending=False).head(15)
        return {"type": chart_type, "title": f"{metric} by {dimension}", "x": [str(i) for i in grouped.index],
                "y": [round(float(v), 2) for v in grouped.values], "series_label": metric,
                "x_label": dimension, "y_label": metric}

    if chart_type == "donut" and dimension:
        counts = df[dimension].value_counts().head(8)
        return {"type": "donut", "title": f"Distribution by {dimension}",
                "labels": [str(i) for i in counts.index], "values": [int(v) for v in counts.values]}

    if chart_type == "scatter" and metric and metric2:
        pts = df[[metric, metric2]].dropna()
        return {"type": "scatter", "title": f"{metric} vs {metric2}", "x_label": metric, "y_label": metric2,
                "points": [[round(float(r[metric]), 2), round(float(r[metric2]), 2)] for _, r in pts.head(300).iterrows()]}

    if chart_type == "histogram" and metric:
        series = pd.to_numeric(df[metric], errors="coerce").dropna()
        counts, edges = np.histogram(series, bins=min(10, max(4, len(series) // 20 or 4)))
        return {"type": "histogram", "title": f"Distribution of {metric}",
                "x": [f"{edges[i]:.0f}-{edges[i+1]:.0f}" for i in range(len(edges) - 1)],
                "y": [int(c) for c in counts], "x_label": metric, "y_label": "Record count"}

    if chart_type == "boxplot" and metric and dimension:
        box_data, categories = [], []
        for name, group in df.groupby(dimension)[metric]:
            vals = pd.to_numeric(group, errors="coerce").dropna()
            if len(vals) < 3:
                continue
            q1, med, q3 = vals.quantile(0.25), vals.median(), vals.quantile(0.75)
            categories.append(str(name))
            box_data.append([round(float(vals.min()), 2), round(float(q1), 2), round(float(med), 2),
                              round(float(q3), 2), round(float(vals.max()), 2)])
        return {"type": "boxplot", "title": f"{metric} distribution by {dimension}", "labels": categories,
                "data": box_data, "y_label": metric}

    raise ValueError("That combination of chart type and columns isn't supported — pick different columns.")


def analyze_dataframe(df: pd.DataFrame) -> dict:
    tags = tag_columns(df)
    kpis = generate_kpis(df, tags)
    charts = recommend_charts(df, tags)
    insights = generate_insights(df, tags, kpis)
    quality = data_quality_score(df)
    segments = top_bottom_segments(df, tags)
    filters = filter_metadata(df, tags)

    column_profiles = [{
        "name": col,
        "role": tag["role"],
        "dtype": str(df[col].dtype),
        "missing_count": int(df[col].isna().sum()),
        "missing_pct": round(float(df[col].isna().mean() * 100), 2),
        "unique_count": tag["cardinality"],
    } for col, tag in tags.items()]

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicate_count": int(df.duplicated().sum()),
        "columns": column_profiles,
        "kpis": kpis,
        "charts": charts,
        "insights": insights,
        "data_quality": quality,
        "segments": segments,
        "filters": filters,
    }


def data_quality_score(df: pd.DataFrame) -> dict:
    n_rows, n_cols = len(df), len(df.columns)
    if n_rows == 0 or n_cols == 0:
        return {"score": 0, "completeness": 0, "uniqueness": 0, "validity": 0, "consistency": 0,
                "formula": "Average of completeness, uniqueness, validity and consistency (0-100 each)."}

    completeness = 100 * (1 - df.isna().sum().sum() / (n_rows * n_cols))

    dup_ratio = df.duplicated().sum() / n_rows
    uniqueness = 100 * (1 - dup_ratio)

    valid_cells = 0
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            valid_cells += series.notna().sum()
        else:
            parsed_dates = pd.to_datetime(series, errors="coerce", format="mixed")
            if parsed_dates.notna().mean() > 0.8:
                valid_cells += parsed_dates.notna().sum()
            else:
                valid_cells += series.notna().sum()
    validity = 100 * (valid_cells / (n_rows * n_cols))

    consistency_scores = []
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        type_set = series.map(lambda v: type(v).__name__).nunique()
        consistency_scores.append(100 if type_set == 1 else max(0, 100 - (type_set - 1) * 20))
    consistency = float(np.mean(consistency_scores)) if consistency_scores else 100

    score = round((completeness + uniqueness + validity + consistency) / 4, 1)
    return {
        "score": score,
        "completeness": round(completeness, 1),
        "uniqueness": round(uniqueness, 1),
        "validity": round(validity, 1),
        "consistency": round(consistency, 1),
        "formula": "Average of completeness (non-missing cells), uniqueness (non-duplicate rows), "
                   "validity (cells matching expected type) and consistency (stable type per column), each 0-100.",
    }
