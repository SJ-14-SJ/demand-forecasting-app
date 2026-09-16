# Model card

## Intended use

A reproducible educational benchmark and portfolio application for gross recorded product sales. Not a deployed procurement or demand-planning system.

## Training and evaluation

Product selection uses the first 120 calendar days. Four expanding-origin 14-day folds precede the final 28-day holdout. Model selection uses pooled validation MAE separately for each product. Ridge uses a fixed alpha of 10; the holdout is not used to tune this setting. A test changes holdout values and verifies that model choice, validation scores and band radius stay unchanged.

Ridge inputs: lags 1/7/14/28, prior 7/28-day means, sine/cosine of weekday and time index. Each rolling feature excludes the target day. Standardization is fitted on each training fold. Multi-step forecasts recursively consume predictions, never actual future values. Negative outputs are clipped to zero.

The baseline repeats the last seven available days. An exact validation tie prefers this simpler baseline.

## Artifact and serving

`artifacts/model.json` records a schema version and source CSV checksum, fold dates, historical summaries, metrics, forecast points, and numeric scaler/coefficient parameters for selected Ridge models. It contains no executable pickle. The API serves forecast points from this artifact; it does not run an LLM or retrain on request.

## Limitations

Three UK gift products and one year cannot establish broad retail performance. Wholesale orders create large spikes. There are no promotion, price-change, stockout or holiday features. Recorded sales do not identify lost demand. Returns are not reconciled against original sales. Zero filling assumes no upstream capture gaps.

Error bands are pooled across 14-step validation horizons and shown for up to 28 steps; coverage can deteriorate with horizon and distribution change. The observed holdout coverage is below 90% for all three series. Do not treat the band as a service-level guarantee.

## Monitoring and extensions

The health endpoint exposes readiness and a source checksum, not full production drift monitoring. A next iteration should ingest new actuals, measure rolling error/coverage by horizon and product, alert on missing capture, and version retraining candidates. Those are explicit future tasks.
