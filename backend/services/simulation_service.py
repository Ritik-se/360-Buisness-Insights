"""What-if simulation: applies user-entered percentage assumptions to real
columns in the dataset, then recomputes real KPIs from the adjusted data.
Every output number is a genuine recalculation — never a guessed impact — and
the response always separates "actual" from "simulated".

If a metric is found to be a mathematical function of other metrics already
in the dataset (e.g. Sales = Quantity x Unit Price x (1 - Discount/100), see
semantic_engine.detect_derived_metrics), it is recalculated from its drivers'
adjusted values rather than scaled by its own independent percentage — so
raising Unit Price genuinely raises Sales, instead of requiring the user to
separately guess a matching Sales percentage."""

from typing import Dict, List

import pandas as pd

from services import semantic_engine


def simulate(df: pd.DataFrame, tags: Dict[str, dict], adjustments: List[dict]) -> dict:
    base_kpis = semantic_engine.generate_kpis(df, tags)
    derived = semantic_engine.detect_derived_metrics(df, tags)

    adjusted = df.copy()
    applied = []
    adjusted_pct: Dict[str, float] = {}
    for adj in adjustments:
        col = adj.get("column")
        pct = adj.get("pct_change")
        if col not in adjusted.columns or pct is None:
            continue
        if col in derived:
            # Derived metrics are recalculated from their drivers below, not
            # scaled independently — an explicit adjustment for one is ignored
            # so the result never contradicts the formula.
            continue
        factor = 1 + (float(pct) / 100)
        adjusted[col] = pd.to_numeric(adjusted[col], errors="coerce") * factor
        adjusted_pct[col] = float(pct)
        applied.append({"column": col, "pct_change": float(pct)})

    if not applied:
        raise ValueError("No valid adjustments were provided.")

    derived_applied = []
    for target, info in derived.items():
        a, b = info["drivers"]
        pred = pd.to_numeric(adjusted[a], errors="coerce") * pd.to_numeric(adjusted[b], errors="coerce")
        if info["kind"] == "product_with_rate":
            factor_col = info["factor_col"]
            sign = info["factor_sign"]
            rate = pd.to_numeric(adjusted[factor_col], errors="coerce")
            pred = pred * (1 + sign * rate / 100)
        adjusted[target] = pred
        derived_applied.append({"column": target, "formula": info["formula"], "derived_from": info["drivers"]})

    simulated_kpis = semantic_engine.generate_kpis(adjusted, tags)

    base_by_label = {k["label"]: k for k in base_kpis}
    derived_labels = {d["column"] for d in derived_applied}
    comparison = []
    for sim_kpi in simulated_kpis:
        base = base_by_label.get(sim_kpi["label"])
        if base is None:
            continue
        delta_pct = None
        if base["value"]:
            delta_pct = round((sim_kpi["value"] - base["value"]) / abs(base["value"]) * 100, 1)
        comparison.append({
            "label": sim_kpi["label"], "unit": sim_kpi["unit"], "aggregation": sim_kpi["aggregation"],
            "actual": base["value"], "simulated": sim_kpi["value"], "change_pct": delta_pct,
            "derived": sim_kpi["label"] in derived_labels,
        })

    return {"adjustments": applied, "derived_metrics": derived_applied, "comparison": comparison}
