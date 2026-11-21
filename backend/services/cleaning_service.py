"""Data profiling and cleaning. Detects concrete, explainable issues in an
uploaded dataset and lets the user accept/reject a recommended fix per issue —
nothing is changed automatically. Cleaning always produces a new dataframe;
the original file on disk is never modified."""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from services.semantic_engine import tag_columns, _norm

NON_NEGATIVE_HINTS = ["quantity", "qty", "count", "age", "price", "amount", "units",
                       "clicks", "impressions", "stock", "inventory", "duration"]


def _sample_rows(df: pd.DataFrame, mask: pd.Series, cols: List[str], n: int = 5) -> List[dict]:
    # float columns can't hold Python None (pandas silently turns it back into NaN),
    # so cast to object first or NaN leaks through and breaks JSON serialization.
    subset = df.loc[mask, cols].head(n).astype(object)
    return subset.where(subset.notna(), None).to_dict(orient="records")


def profile_issues(df: pd.DataFrame) -> List[dict]:
    issues: List[dict] = []
    tags = tag_columns(df)
    n = len(df)

    # dataset-level: duplicate rows
    dup_mask = df.duplicated()
    if dup_mask.sum() > 0:
        issues.append({
            "column": None,
            "issue_type": "duplicate_records",
            "affected_rows": int(dup_mask.sum()),
            "sample_records": _sample_rows(df, dup_mask, list(df.columns)[:5]),
            "recommended_method": "drop_duplicates",
            "severity": "medium",
            "description": f"{int(dup_mask.sum())} fully duplicated rows found.",
        })

    for col in df.columns:
        series = df[col]
        tag = tags[col]
        norm = _norm(col)

        # empty column
        if series.isna().all():
            issues.append({
                "column": col, "issue_type": "empty_column", "affected_rows": n,
                "sample_records": [], "recommended_method": "drop_column", "severity": "high",
                "description": f"'{col}' has no values at all.",
            })
            continue

        # constant column
        if series.dropna().nunique() == 1:
            issues.append({
                "column": col, "issue_type": "constant_column", "affected_rows": n,
                "sample_records": _sample_rows(df, pd.Series(True, index=df.index), [col]),
                "recommended_method": "drop_column", "severity": "low",
                "description": f"'{col}' has the same value in every row.",
            })

        # missing values
        missing_mask = series.isna()
        if 0 < missing_mask.sum() < n:
            method = "fill_median" if tag["is_numeric"] else "fill_mode"
            issues.append({
                "column": col, "issue_type": "missing_values", "affected_rows": int(missing_mask.sum()),
                "sample_records": _sample_rows(df, missing_mask, [c for c in df.columns if c != col][:4] + [col]),
                "recommended_method": method, "severity": "medium" if missing_mask.mean() < 0.3 else "high",
                "description": f"{int(missing_mask.sum())} missing values ({round(missing_mask.mean()*100,1)}%).",
            })

        if tag["role"] == "date":
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            bad_mask = parsed.isna() & series.notna()
            if bad_mask.sum() > 0:
                issues.append({
                    "column": col, "issue_type": "invalid_date_format", "affected_rows": int(bad_mask.sum()),
                    "sample_records": _sample_rows(df, bad_mask, [col]),
                    "recommended_method": "standardize_dates", "severity": "medium",
                    "description": f"{int(bad_mask.sum())} values don't parse as dates.",
                })
            continue

        if tag["is_numeric"]:
            clean = series.dropna()
            if len(clean) >= 5:
                q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    out_mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
                    out_mask = out_mask.fillna(False)
                    if out_mask.sum() > 0:
                        issues.append({
                            "column": col, "issue_type": "outliers", "affected_rows": int(out_mask.sum()),
                            "sample_records": _sample_rows(df, out_mask, [col]),
                            "recommended_method": "cap_outliers_iqr", "severity": "low",
                            "description": f"{int(out_mask.sum())} values fall outside the normal range ({round(q1-1.5*iqr,2)} to {round(q3+1.5*iqr,2)}).",
                        })
            if any(h in norm for h in NON_NEGATIVE_HINTS):
                neg_mask = series < 0
                if neg_mask.sum() > 0:
                    issues.append({
                        "column": col, "issue_type": "invalid_numerical_values", "affected_rows": int(neg_mask.sum()),
                        "sample_records": _sample_rows(df, neg_mask, [col]),
                        "recommended_method": "fix_negative", "severity": "medium",
                        "description": f"{int(neg_mask.sum())} negative values in a column that should likely be non-negative.",
                    })
        else:
            # column stored as text but mostly numeric -> wrong dtype
            coerced = pd.to_numeric(series, errors="coerce")
            if series.notna().sum() > 0 and coerced.notna().mean() > 0.8 and coerced.notna().sum() < series.notna().sum():
                bad_mask = series.notna() & coerced.isna()
                issues.append({
                    "column": col, "issue_type": "incorrect_data_type", "affected_rows": int(bad_mask.sum()),
                    "sample_records": _sample_rows(df, bad_mask, [col]),
                    "recommended_method": "convert_numeric", "severity": "medium",
                    "description": f"'{col}' looks numeric but is stored as text; {int(bad_mask.sum())} values won't convert cleanly.",
                })
            elif tag["role"] in ("dimension", "geo"):
                normalized = series.dropna().astype(str).str.strip().str.lower()
                raw = series.dropna().astype(str)
                if normalized.nunique() < raw.nunique():
                    mismatch_mask = series.notna() & (series.astype(str) != series.astype(str).str.strip().str.title())
                    collapsed_groups = raw.groupby(normalized).nunique()
                    if (collapsed_groups > 1).any():
                        issues.append({
                            "column": col, "issue_type": "inconsistent_categorical_values",
                            "affected_rows": int(raw.nunique() - normalized.nunique()),
                            "sample_records": _sample_rows(df, mismatch_mask, [col]),
                            "recommended_method": "normalize_categories", "severity": "low",
                            "description": f"'{col}' has values that differ only in case/spacing (e.g. 'North' vs 'north').",
                        })

    return issues


def apply_cleaning(df: pd.DataFrame, operations: List[dict]) -> pd.DataFrame:
    """operations: [{column, method, value?}]. column is None for dataset-level ops."""
    cleaned = df.copy()

    for op in operations:
        col = op.get("column")
        method = op["method"]

        if method == "drop_duplicates":
            cleaned = cleaned.drop_duplicates()
            continue
        if col is None or col not in cleaned.columns:
            continue

        if method == "drop_column":
            cleaned = cleaned.drop(columns=[col])
        elif method == "fill_mean":
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            cleaned[col] = cleaned[col].fillna(cleaned[col].mean())
        elif method == "fill_median":
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            cleaned[col] = cleaned[col].fillna(cleaned[col].median())
        elif method == "fill_mode":
            mode = cleaned[col].mode()
            if len(mode):
                cleaned[col] = cleaned[col].fillna(mode.iloc[0])
        elif method == "fill_value":
            cleaned[col] = cleaned[col].fillna(op.get("value"))
        elif method == "fix_negative":
            series = pd.to_numeric(cleaned[col], errors="coerce")
            median = series[series >= 0].median()
            cleaned[col] = series.where(series.isna() | (series >= 0), median)
        elif method == "standardize_dates":
            cleaned[col] = pd.to_datetime(cleaned[col], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
        elif method == "convert_numeric":
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
        elif method == "cap_outliers_iqr":
            series = pd.to_numeric(cleaned[col], errors="coerce")
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            cleaned[col] = series.clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)
        elif method == "remove_outliers_iqr":
            series = pd.to_numeric(cleaned[col], errors="coerce")
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            mask = (series >= q1 - 1.5 * iqr) & (series <= q3 + 1.5 * iqr) | series.isna()
            cleaned = cleaned[mask]
        elif method == "normalize_categories":
            cleaned[col] = cleaned[col].astype(str).str.strip().str.title()

    return cleaned


def quality_summary(before: pd.DataFrame, after: pd.DataFrame) -> dict:
    return {
        "rows_before": len(before),
        "rows_after": len(after),
        "rows_removed": len(before) - len(after),
        "columns_before": len(before.columns),
        "columns_after": len(after.columns),
        "columns_removed": [c for c in before.columns if c not in after.columns],
    }
