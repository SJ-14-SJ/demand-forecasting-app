import unittest
import numpy as np
import pandas as pd
from forecast.engine import features, predict, evaluate_series, validate_series, metrics


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2024-01-01", periods=210)
        self.values = np.tile([10, 12, 15, 13, 20, 25, 18], 30).astype(float)

    def test_seasonal_baseline_repeats_without_future_truth(self):
        pred, _ = predict(self.values, self.dates, 14, "seasonal_naive")
        np.testing.assert_array_equal(pred, np.tile(self.values[-7:], 2))

    def test_features_only_use_history(self):
        f = features(list(range(28)), pd.Timestamp("2024-01-29"), 28)
        self.assertEqual(f[0], 27)
        self.assertEqual(f[1], 21)
        self.assertEqual(f[4], 24)

    def test_holdout_does_not_change_model_selection_or_bands(self):
        before = evaluate_series(self.values, self.dates)
        changed = self.values.copy()
        changed[-28:] += 1000
        after = evaluate_series(changed, self.dates)
        self.assertEqual(before["validation"], after["validation"])
        self.assertEqual(before["selected_model"], after["selected_model"])
        self.assertEqual(before["interval_radius"], after["interval_radius"])

    def test_perfect_weekly_pattern_chooses_baseline(self):
        result = evaluate_series(self.values, self.dates)
        self.assertEqual(result["selected_model"], "seasonal_naive")
        self.assertAlmostEqual(result["holdout"]["seasonal_naive"]["mae"], 0)

    def test_missing_days_and_duplicates_rejected(self):
        frame = pd.DataFrame({"date": self.dates, "sku": "a", "units": self.values})
        with self.assertRaises(ValueError):
            validate_series(frame.drop(30))
        with self.assertRaises(ValueError):
            validate_series(pd.concat([frame, frame.iloc[:1]]))

    def test_zero_demand_wape_is_undefined(self):
        self.assertIsNone(metrics([0, 0], [1, 0])["wape"])


if __name__ == "__main__":
    unittest.main()
