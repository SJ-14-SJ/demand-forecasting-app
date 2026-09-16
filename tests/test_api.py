import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from forecast.api import create_app


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name, "model.json")
        self.path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "data_origin": "test",
                    "source_sha256": "example",
                    "interval_note": "test",
                    "series": [
                        {
                            "sku": "A",
                            "selected_model": "seasonal_naive",
                            "history_end": "2025-01-01",
                            "forecast": [
                                {
                                    "date": "2025-01-02",
                                    "units": 5,
                                    "lower": 3,
                                    "upper": 7,
                                }
                            ]
                            * 28,
                        }
                    ],
                }
            )
        )
        self.client = TestClient(create_app(self.path))

    def tearDown(self):
        self.temp.cleanup()

    def test_horizon_and_inventory_validation(self):
        self.assertEqual(self.client.get("/api/forecast/A?horizon=29").status_code, 422)
        self.assertEqual(
            self.client.get("/api/inventory/A?on_hand=-1").status_code, 422
        )

    def test_unknown_sku(self):
        self.assertEqual(self.client.get("/api/forecast/unknown").status_code, 404)

    def test_inventory_does_not_recommend_negative_orders(self):
        self.assertEqual(
            self.client.get("/api/inventory/A?on_hand=100&lead_days=7").json()[
                "suggested_order"
            ],
            0,
        )

    def test_missing_artifact_is_explicit(self):
        self.path.unlink()
        self.assertEqual(self.client.get("/api/health").status_code, 503)

    def test_forecast_limits_horizon(self):
        self.assertEqual(
            len(self.client.get("/api/forecast/A?horizon=7").json()["forecast"]), 7
        )


if __name__ == "__main__":
    unittest.main()
