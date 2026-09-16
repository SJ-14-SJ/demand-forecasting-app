import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = [
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "mean_7",
    "mean_28",
    "weekday_sin",
    "weekday_cos",
    "trend",
]


def features(history, target_date, index):
    if len(history) < 28:
        raise ValueError("At least 28 prior days are required")
    dow = pd.Timestamp(target_date).dayofweek
    return [
        history[-1],
        history[-7],
        history[-14],
        history[-28],
        np.mean(history[-7:]),
        np.mean(history[-28:]),
        np.sin(2 * np.pi * dow / 7),
        np.cos(2 * np.pi * dow / 7),
        index,
    ]


def fit_ridge(values, dates):
    if len(values) < 56:
        raise ValueError("At least 56 observations are required")
    x = np.array([features(values[:i], dates[i], i) for i in range(28, len(values))])
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    model.fit(x, np.asarray(values[28:]))
    return model


def predict(values, dates, horizon, kind):
    if kind not in ["seasonal_naive", "ridge"]:
        raise ValueError("Unknown model")
    model = fit_ridge(values, dates) if kind == "ridge" else None
    history = list(map(float, values))
    future = pd.date_range(
        pd.Timestamp(dates[-1]) + pd.Timedelta(days=1), periods=horizon
    )
    result = []
    for day in future:
        value = (
            history[-7]
            if model is None
            else model.predict([features(history, day, len(history))])[0]
        )
        value = max(0.0, float(value))
        result.append(value)
        history.append(value)
    return np.array(result), model


def metrics(actual, prediction):
    actual = np.array(actual)
    prediction = np.array(prediction)
    error = np.abs(actual - prediction)
    return {
        "mae": float(np.mean(error)),
        "rmse": float(np.sqrt(np.mean((actual - prediction) ** 2))),
        "wape": float(error.sum() / np.abs(actual).sum())
        if np.abs(actual).sum() > 0
        else None,
    }


def validate_series(frame):
    required = {"date", "sku", "units"}
    if not required.issubset(frame):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    if frame.empty:
        raise ValueError("Demand dataset cannot be empty")
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["units"] = pd.to_numeric(data["units"], errors="raise")
    if (
        data[["date", "sku", "units"]].isna().any().any()
        or not np.isfinite(data.units).all()
        or (data.units < 0).any()
    ):
        raise ValueError("Missing, negative or nonfinite demand values")
    if data.duplicated(["sku", "date"]).any():
        raise ValueError("Duplicate sku/date rows")
    for _, group in data.groupby("sku"):
        dates = group.sort_values("date").date
        if len(dates) < 180:
            raise ValueError("At least 180 daily observations per SKU are required")
        if not dates.diff().dropna().eq(pd.Timedelta(days=1)).all():
            raise ValueError(
                "Daily series must be complete; resolve missing days upstream"
            )
    return data.sort_values(["sku", "date"])


def evaluate_series(values, dates):
    """Four expanding 14-day folds; final 28 days are untouched by selection."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    folds = [n - 84, n - 70, n - 56, n - 42]
    candidates = {}
    residuals = {}
    fold_records = []
    for kind in ["seasonal_naive", "ridge"]:
        actuals = []
        predictions = []
        for end in folds:
            prediction, _ = predict(values[:end], dates[:end], 14, kind)
            truth = values[end : end + 14]
            actuals.extend(truth)
            predictions.extend(prediction)
            fold_records.append(
                {
                    "model": kind,
                    "train_end": str(pd.Timestamp(dates[end - 1]).date()),
                    "validation_start": str(pd.Timestamp(dates[end]).date()),
                    "validation_end": str(pd.Timestamp(dates[end + 13]).date()),
                    **metrics(truth, prediction),
                }
            )
        candidates[kind] = metrics(actuals, predictions)
        residuals[kind] = np.abs(np.array(actuals) - np.array(predictions))
    # Prefer the simpler baseline on an exact tie.
    selected = min(candidates, key=lambda name: candidates[name]["mae"])
    holdout = {}
    hold_predictions = {}
    for kind in candidates:
        pred, _ = predict(values[:-28], dates[:-28], 28, kind)
        holdout[kind] = metrics(values[-28:], pred)
        hold_predictions[kind] = pred
    radius = float(np.quantile(residuals[selected], 0.9, method="higher"))
    chosen = hold_predictions[selected]
    coverage = float(
        np.mean(
            (values[-28:] >= np.maximum(0, chosen - radius))
            & (values[-28:] <= chosen + radius)
        )
    )
    forecast, model = predict(values, dates, 28, selected)
    parameters = None
    if model is not None:
        scaler = model.named_steps["standardscaler"]
        ridge = model.named_steps["ridge"]
        parameters = {
            "features": FEATURE_NAMES,
            "means": scaler.mean_.tolist(),
            "scales": scaler.scale_.tolist(),
            "coefficients": ridge.coef_.tolist(),
            "intercept": float(ridge.intercept_),
        }
    return {
        "selected_model": selected,
        "validation": candidates,
        "holdout": holdout,
        "folds": fold_records,
        "interval_radius": radius,
        "holdout_coverage": coverage,
        "forecast": forecast.tolist(),
        "parameters": parameters,
        "holdout_prediction": chosen.tolist(),
    }
