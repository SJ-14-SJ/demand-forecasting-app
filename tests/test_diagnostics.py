import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from forecast.diagnostics import build


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "daily.csv"
        self.artifact = self.root / "model.json"
        self.data = pd.DataFrame({
            "sku": "001", "date": pd.date_range("2024-01-01", periods=180),
            "units": np.r_[np.full(152, 10), np.full(28, 20)],
        })
        self.data.to_csv(self.source, index=False)
        self.model = {
            "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "series": [{
                "sku": "001", "observations": 180, "selected_model": "seasonal_naive",
                "history_end": "2024-06-28", "holdout_start": "2024-06-01",
                "holdout_prediction": [12] * 28, "interval_radius": 3,
            }],
        }
        self.artifact.write_text(json.dumps(self.model))

    def test_known_errors_coverage_and_preholdout_threshold(self):
        artifact_before = self.artifact.read_bytes()
        frame, grouped = build(self.source, self.artifact, self.root / "report")
        overall = grouped[grouped.dimension == "overall"].iloc[0]
        self.assertEqual(overall.mae, 8)
        self.assertEqual(overall.bias, -8)
        self.assertEqual(overall.band_coverage, 0)
        self.assertEqual(overall.wape, 0.4)
        self.assertEqual(frame.high_demand_threshold.unique().tolist(), [10])
        self.assertEqual(frame.demand_group.unique().tolist(), ["high"])
        self.assertEqual(frame.sku.unique().tolist(), ["001"])
        self.assertEqual(grouped[grouped.dimension == "horizon_week"].days.tolist(), [7] * 4)
        self.assertEqual(self.artifact.read_bytes(), artifact_before)

    def test_mismatched_source_is_rejected(self):
        with self.source.open("a") as handle:
            handle.write("\n")
        with self.assertRaisesRegex(ValueError, "checksum"):
            build(self.source, self.artifact, self.root / "report")

    def test_shifted_holdout_or_invalid_predictions_are_rejected(self):
        for field, value in [("holdout_start", "2024-05-31"), ("holdout_prediction", [12] * 27), ("interval_radius", -1)]:
            with self.subTest(field=field):
                original = self.model["series"][0][field]
                self.model["series"][0][field] = value
                self.artifact.write_text(json.dumps(self.model))
                with self.assertRaisesRegex(ValueError, "Invalid holdout"):
                    build(self.source, self.artifact, self.root / "report")
                self.model["series"][0][field] = original


if __name__ == "__main__":
    unittest.main()
