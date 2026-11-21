"""Time-series forecasting for the primary metric. Several real models are
fit and backtested (held-out real months), and the one with the lowest
out-of-sample error is used — this is genuine model selection, not a fixed
choice, and the reported accuracy always comes from that held-out test."""

import warnings
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from sklearn.preprocessing import PolynomialFeatures

warnings.filterwarnings("ignore")


def _monthly_series(df: pd.DataFrame, date_col: str, metric_col: str) -> pd.Series:
    dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    values = pd.to_numeric(df[metric_col], errors="coerce")
    valid = dates.notna() & values.notna()
    frame = pd.DataFrame({"date": dates[valid], "value": values[valid]}).set_index("date")
    return frame.resample("MS")["value"].sum().dropna()


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(actual, predicted)), 2),
        "rmse": round(float(mean_squared_error(actual, predicted) ** 0.5), 2),
        "mape": round(float(mean_absolute_percentage_error(actual, predicted)) * 100, 1),
    }


def _linear_poly_forecast(y: np.ndarray, degree: int, train_len: int, horizon: int):
    x = np.arange(len(y))
    poly = PolynomialFeatures(degree=degree)
    model = LinearRegression()
    model.fit(poly.fit_transform(x[:train_len].reshape(-1, 1)), y[:train_len])
    future_x = np.arange(train_len, train_len + horizon)
    return model.predict(poly.transform(future_x.reshape(-1, 1)))


def _ets_forecast(y: np.ndarray, train_len: int, horizon: int):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    model = ExponentialSmoothing(y[:train_len], trend="add", damped_trend=True).fit()
    return model.forecast(horizon)


def _arima_forecast(y: np.ndarray, train_len: int, horizon: int):
    from statsmodels.tsa.arima.model import ARIMA
    model = ARIMA(y[:train_len], order=(1, 1, 1)).fit()
    result = model.get_forecast(horizon)
    return result.predicted_mean, result.conf_int(alpha=0.2)


def _fit_and_predict(name: str, y: np.ndarray, train_len: int, horizon: int):
    try:
        if name == "linear":
            preds = _linear_poly_forecast(y, 1, train_len, horizon)
        elif name == "polynomial":
            preds = _linear_poly_forecast(y, 2, train_len, horizon)
        elif name == "exponential_smoothing":
            preds = _ets_forecast(y, train_len, horizon)
        elif name == "arima":
            preds, _ = _arima_forecast(y, train_len, horizon)
        else:
            return None
        preds = np.asarray(preds, dtype=float)
        if np.isnan(preds).any() or np.isinf(preds).any():
            return None
        return preds
    except Exception:
        return None


def forecast_metric(df: pd.DataFrame, date_col: str, metric_col: str, periods: int = 3) -> Optional[Dict]:
    series = _monthly_series(df, date_col, metric_col)
    if len(series) < 4:
        return None

    y = series.values.astype(float)
    holdout = min(3, max(1, len(y) // 4))
    if len(y) - holdout < 3:
        holdout = max(1, len(y) - 3)
    backtest_train_len = len(y) - holdout
    test_actual = y[backtest_train_len:]

    candidates = ["linear", "polynomial"]
    if len(y) >= 8:
        candidates.append("exponential_smoothing")
    if len(y) >= 10:
        candidates.append("arima")

    comparison: List[dict] = []
    best_name, best_mape = None, float("inf")
    for name in candidates:
        preds = _fit_and_predict(name, y, backtest_train_len, holdout)
        if preds is None or len(preds) != holdout:
            continue
        m = _metrics(test_actual, preds)
        comparison.append({"model": name, **m})
        if m["mape"] < best_mape:
            best_mape, best_name = m["mape"], name

    if best_name is None:
        return None

    # Refit the winning model on ALL real history (train_len = len(y)) to produce the
    # actual future forecast — the backtest above only used it to pick a model.
    if best_name == "arima":
        future_preds, conf_int = _arima_forecast(y, len(y), periods)
        future_preds = np.asarray(future_preds, dtype=float)
        lower, upper = conf_int[:, 0].tolist(), conf_int[:, 1].tolist()
    else:
        future_preds = _fit_and_predict(best_name, y, len(y), periods)
        lower = upper = None

    future_preds = np.maximum(future_preds, 0)
    accuracy_pct = round(max(0.0, 1 - best_mape / 100) * 100, 1)

    last_date = series.index[-1]
    future_dates = pd.date_range(last_date, periods=periods + 1, freq="MS")[1:]

    return {
        "metric": metric_col,
        "history": {"x": [d.strftime("%b %Y") for d in series.index], "y": [round(float(v), 2) for v in y]},
        "forecast": {"x": [d.strftime("%b %Y") for d in future_dates], "y": [round(float(v), 2) for v in future_preds]},
        "prediction_interval": {"lower": [round(float(v), 2) for v in lower], "upper": [round(float(v), 2) for v in upper]} if lower else None,
        "accuracy_pct": accuracy_pct,
        "model_used": best_name,
        "model_comparison": sorted(comparison, key=lambda c: c["mape"]),
        "method": f"Compared {len(comparison)} model(s) by backtesting on the last {holdout} real month(s); "
                  f"selected '{best_name}' (lowest error) and refit it on all {len(y)} months of history.",
    }
