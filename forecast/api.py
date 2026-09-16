"""Read-only prediction API serving a versioned, precomputed forecast artifact."""

import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]


def create_app(artifact_path=None):
    app = FastAPI(title="DemandLab API", version="1.0.0")
    artifact_path = Path(
        artifact_path or os.getenv("MODEL_PATH", str(ROOT / "artifacts/model.json"))
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    cache = {}

    def artifact():
        if not artifact_path.exists():
            raise HTTPException(
                503, "Forecast artifact unavailable. Run python -m forecast.train."
            )
        stamp = artifact_path.stat().st_mtime_ns
        if cache.get("stamp") != stamp:
            try:
                payload = json.loads(artifact_path.read_text())
                if payload["schema_version"] != 1 or not isinstance(
                    payload["series"], list
                ):
                    raise ValueError("Unsupported artifact")
            except (ValueError, KeyError):
                raise HTTPException(503, "Forecast artifact is invalid")
            cache.update(stamp=stamp, data=payload)
        return cache["data"]

    def series(sku):
        return next((s for s in artifact()["series"] if s["sku"] == sku), None)

    @app.get("/api/health")
    def health():
        data = artifact()
        return {
            "status": "ok",
            "series": len(data["series"]),
            "source_sha256": data["source_sha256"],
        }

    @app.get("/api/catalog")
    def catalog():
        data = artifact()
        return {
            "data_origin": data["data_origin"],
            "interval_note": data["interval_note"],
            "products": [
                {
                    "sku": s["sku"],
                    "description": s.get("description", s["sku"]),
                    "selected_model": s["selected_model"],
                    "history_end": s["history_end"],
                }
                for s in data["series"]
            ],
        }

    @app.get("/api/forecast/{sku}")
    def forecast(sku: str, horizon: int = Query(14, ge=1, le=28)):
        found = series(sku)
        if found is None:
            raise HTTPException(404, "Unknown SKU")
        return {**found, "forecast": found["forecast"][:horizon]}

    @app.get("/api/inventory/{sku}")
    def inventory(
        sku: str,
        lead_days: int = Query(7, ge=1, le=28),
        on_hand: int = Query(0, ge=0, le=1000000),
    ):
        found = series(sku)
        if found is None:
            raise HTTPException(404, "Unknown SKU")
        demand = sum(p["units"] for p in found["forecast"][:lead_days])
        return {
            "expected_demand": round(demand, 1),
            "on_hand": on_hand,
            "suggested_order": max(0, int(__import__("math").ceil(demand - on_hand))),
            "note": "Illustrative demand-only calculation. Excludes safety stock, open orders, costs and supplier constraints.",
        }

    static = ROOT / "frontend/dist"
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return app


app = create_app()
