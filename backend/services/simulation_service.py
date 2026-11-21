"""What-if simulation: applies user-entered percentage assumptions to real
columns in the dataset, then recomputes real KPIs from the adjusted data.
Every output number is a genuine recalculation — never a guessed impact — and
the response always separates "actual" from "simulated"."""

from typing import Dict, List

import pandas as pd

from services import semantic_engine


def simulate(df: pd.DataFrame, tags: Dict[str, dict], adjustments: List[dict]) -> dict:
    base_kpis = semantic_engine.generate_kpis(df, tags)

    adjusted = df.copy()
    applied = []
    for adj in adjustments:
        col = adj.get("column")
        pct = adj.get("pct_change")
        if col not in adjusted.columns or pct is None:
            continue
        factor = 1 + (float(pct) / 100)
        adjusted[col] = pd.to_numeric(adjusted[col], errors="coerce") * factor
        applied.append({"column": col, "pct_change": float(pct)})

    if not applied:
        raise ValueError("No valid adjustments were provided.")

    simulated_kpis = semantic_engine.generate_kpis(adjusted, tags)

    base_by_label = {k["label"]: k for k in base_kpis}
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
        })

    return {"adjustments": applied, "comparison": comparison}
