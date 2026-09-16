"""Audit a frozen forecast artifact without selecting or retraining models."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import metrics, validate_series
from .train import ROOT


def residuals(source, artifact_path):
    artifact = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    if artifact.get("source_sha256") != digest:
        raise ValueError("Source checksum differs from the frozen model artifact; train the intended source first")
    data = validate_series(pd.read_csv(source, dtype={"sku": str}))
    if {str(s["sku"]) for s in artifact["series"]} != set(data.sku):
        raise ValueError("Artifact products do not match the source")
    rows = []
    for series in artifact["series"]:
        sku = str(series["sku"])
        group = data[data.sku == sku].sort_values("date")
        holdout = group.tail(28)
        prediction = np.asarray(series["holdout_prediction"], dtype=float)
        radius = float(series["interval_radius"])
        if (
            prediction.shape != (28,)
            or not np.isfinite(prediction).all()
            or (prediction < 0).any()
            or not np.isfinite(radius)
            or radius < 0
            or series["holdout_start"] != str(holdout.date.iloc[0].date())
            or series["history_end"] != str(holdout.date.iloc[-1].date())
            or series["observations"] != len(group)
        ):
            raise ValueError(f"Invalid holdout predictions or date coverage for {sku}")
        # Diagnostic cutoff uses only the pre-holdout history. It does not alter
        # the original model selection, error band or future forecast.
        threshold = float(np.quantile(group.units.iloc[:-28], 0.9, method="higher"))
        for horizon, (observed, predicted) in enumerate(zip(holdout.itertuples(), prediction), 1):
            lower = max(0.0, float(predicted - radius))
            upper = float(predicted + radius)
            rows.append(
                {
                    "sku": sku,
                    "date": str(observed.date.date()),
                    "selected_model": series["selected_model"],
                    "horizon": horizon,
                    "horizon_week": f"{1 + 7 * ((horizon - 1) // 7)}–{7 * (1 + (horizon - 1) // 7)}",
                    "weekday": observed.date.day_name(),
                    "actual": float(observed.units),
                    "prediction": float(predicted),
                    "error": float(predicted - observed.units),
                    "absolute_error": float(abs(predicted - observed.units)),
                    "lower": lower,
                    "upper": upper,
                    "covered": bool(lower <= observed.units <= upper),
                    "high_demand_threshold": threshold,
                    "demand_group": "high" if observed.units > threshold else "other",
                }
            )
    return pd.DataFrame(rows), digest


def summarize(frame):
    return {
        "days": len(frame),
        **metrics(frame.actual, frame.prediction),
        "bias": float(frame.error.mean()),
        "band_coverage": float(frame.covered.mean()),
    }


def slices(frame):
    rows = []
    for sku, group in frame.groupby("sku", sort=True):
        rows.append({"sku": sku, "dimension": "overall", "segment": "all", **summarize(group)})
        for dimension in ["horizon_week", "weekday", "demand_group"]:
            for segment, part in group.groupby(dimension, sort=False):
                rows.append({"sku": sku, "dimension": dimension, "segment": segment, **summarize(part)})
    return pd.DataFrame(rows)


def report(frame, grouped, digest):
    text = [
        "# Forecast error analysis",
        "",
        f"Frozen holdout: **{frame.date.min()} to {frame.date.max()}**, {len(frame)} product-days. This report audits the already selected models; it does not refit them or change selection using test outcomes.",
        "",
        "A positive bias means overprediction; a negative bias means underprediction. MAE and bias are in units per day. Each product has only 28 holdout observations. These are descriptive slices of one forecast origin, not independent repeated experiments.",
        "",
        "## Error by product",
        "",
        "| Product | Model | MAE | Bias | WAPE | Band coverage |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in grouped[grouped.dimension == "overall"].itertuples():
        model = frame[frame.sku == row.sku].selected_model.iloc[0]
        wape = "undefined" if pd.isna(row.wape) else f"{row.wape:.1%}"
        text.append(f"| {row.sku} | {model} | {row.mae:.2f} | {row.bias:+.2f} | {wape} | {row.band_coverage:.1%} |")
    text += [
        "", "## Error by forecast horizon", "",
        "Each cell is one seven-day portion of the same holdout. Calendar effects and horizon effects are confounded here; a rolling-origin experiment is needed to separate them.", "",
        "| Product | Days ahead | Observations | MAE | Bias | Band coverage |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in grouped[grouped.dimension == "horizon_week"].itertuples():
        text.append(f"| {row.sku} | {row.segment} | {row.days} | {row.mae:.2f} | {row.bias:+.2f} | {row.band_coverage:.1%} |")
    text += [
        "", "## High-demand days", "",
        "A high-demand day exceeds the product's 90th-percentile demand in its pre-holdout history (including validation). The cutoff never uses holdout values. This retrospective label explains failures; it is not known when a forecast is made. Missing groups have zero observations and are omitted.", "",
        "| Product | Group | Pre-holdout cutoff | Days | MAE | Bias | Band coverage |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in grouped[grouped.dimension == "demand_group"].itertuples():
        cutoff = frame[frame.sku == row.sku].high_demand_threshold.iloc[0]
        text.append(f"| {row.sku} | {row.segment} | {cutoff:.0f} | {row.days} | {row.mae:.2f} | {row.bias:+.2f} | {row.band_coverage:.1%} |")
    text += [
        "", "## Two largest misses per product", "",
        "These examples are selected by absolute error after evaluation and are not representative averages.", "",
        "| Product | Date | Days ahead | Actual | Forecast | Absolute error | In band? |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, group in frame.groupby("sku", sort=True):
        for row in group.sort_values(["absolute_error", "date"], ascending=[False, True]).head(2).itertuples():
            text.append(f"| {row.sku} | {row.date} | {row.horizon} | {row.actual:.0f} | {row.prediction:.2f} | {row.absolute_error:.2f} | {'yes' if row.covered else 'no'} |")
    text += [
        "", "## Interpretation and next experiment", "",
        "- Compare bias with high-demand errors before adding model complexity. Sales spikes and stock availability are not explained by this dataset's daily quantities alone; the report does not establish a causal explanation.",
        "- Exploratory bands were calibrated on 14-day validation forecasts and evaluated here over 28 days. They do not promise 90% future coverage. Check calibration separately at the intended deployment horizon.",
        "- Weekday metrics are in `error-slices.csv`; each weekday has just four observations per product. Treat apparent differences as hypotheses.",
        "- Freeze this report as a historical experiment. Predeclare a new rolling-origin protocol before comparing another candidate or changing parameters; repeatedly tuning on this known holdout would invalidate a fresh-test claim.",
        "- Demand-only ordering recommendations are illustrative. These errors do not demonstrate reduced stockouts, increased revenue or a deployable purchasing policy.",
        "", "## Reproduce", "",
        "```bash", "python -m forecast.train", "python -m forecast.diagnostics", "```", "",
        "Outputs: `outputs/error-analysis/ERROR-ANALYSIS.md`, `holdout-residuals.csv`, `error-slices.csv` and `metadata.json`. The command checks that the source checksum matches the frozen model artifact before calculating anything.", "",
        f"Source SHA-256: `{digest}`.", "",
    ]
    return "\n".join(text)


def build(source, artifact_path, output):
    frame, digest = residuals(source, artifact_path)
    grouped = slices(frame)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "holdout-residuals.csv", index=False, float_format="%.10g")
    grouped.to_csv(output / "error-slices.csv", index=False, float_format="%.10g")
    (output / "ERROR-ANALYSIS.md").write_text(report(frame, grouped, digest), encoding="utf-8")
    metadata = {
        "schema_version": 1,
        "source_sha256": digest,
        "artifact_sha256": hashlib.sha256(Path(artifact_path).read_bytes()).hexdigest(),
        "holdout_product_days": len(frame),
        "interpretation": "Descriptive audit of one frozen holdout; no model selection or refitting",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return frame, grouped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/daily_demand.csv")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/model.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/error-analysis")
    args = parser.parse_args()
    frame, _ = build(args.input, args.artifact, args.output)
    print(f"Audited {len(frame)} frozen holdout predictions; reports in {args.output}")
