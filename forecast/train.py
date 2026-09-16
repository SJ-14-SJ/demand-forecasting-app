import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from .engine import validate_series, evaluate_series

ROOT = Path(__file__).resolve().parents[1]


def build(source, output, origin=None):
    data = validate_series(pd.read_csv(source))
    provenance_path = Path(source).with_name("provenance.json")
    # Only the bundled public-data filename inherits adjacent provenance.
    provenance = (
        json.loads(provenance_path.read_text())
        if provenance_path.exists() and Path(source).name == "daily_demand.csv"
        else {}
    )
    origin = origin or (
        "UCI Online Retail · historical UK sales"
        if provenance.get("source") == "UCI Online Retail"
        else "User-supplied dataset"
    )
    artifact = {
        "schema_version": 1,
        "data_origin": origin,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "interval_note": "Exploratory bands use the 90th percentile of 14-day validation absolute errors. No 90% future or simultaneous coverage guarantee.",
        "series": [],
    }
    for sku, group in data.groupby("sku"):
        dates = group.date.tolist()
        values = group.units.to_numpy()
        evaluation = evaluate_series(values, dates)
        future = pd.date_range(dates[-1] + pd.Timedelta(days=1), periods=28)
        radius = evaluation["interval_radius"]
        artifact["series"].append(
            {
                "sku": str(sku),
                "description": provenance.get("descriptions", {}).get(
                    str(sku), str(sku)
                ),
                "observations": len(group),
                "history_start": str(dates[0].date()),
                "history_end": str(dates[-1].date()),
                "history": [
                    {"date": str(row.date.date()), "units": float(row.units)}
                    for row in group.tail(84).itertuples()
                ],
                "holdout_start": str(dates[-28].date()),
                **{k: v for k, v in evaluation.items() if k != "forecast"},
                "forecast": [
                    {
                        "date": str(d.date()),
                        "units": float(v),
                        "lower": max(0, float(v - radius)),
                        "upper": float(v + radius),
                    }
                    for d, v in zip(future, evaluation["forecast"])
                ],
            }
        )
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")
    return artifact


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "data/daily_demand.csv"))
    p.add_argument("--output", default=str(ROOT / "artifacts/model.json"))
    p.add_argument("--origin")
    a = p.parse_args()
    artifact = build(a.input, a.output, a.origin)
    for s in artifact["series"]:
        print(
            s["sku"],
            s["selected_model"],
            s["holdout"][s["selected_model"]],
            "coverage",
            round(s["holdout_coverage"], 3),
        )
