# Forecast error analysis

Frozen holdout: **2011-11-11 to 2011-12-08**, 84 product-days. This report audits the already selected models; it does not refit them or change selection using test outcomes.

A positive bias means overprediction; a negative bias means underprediction. MAE and bias are in units per day. Each product has only 28 holdout observations. These are descriptive slices of one forecast origin, not independent repeated experiments.

## Error by product

| Product | Model | MAE | Bias | WAPE | Band coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| 22423 | seasonal_naive | 27.82 | +2.61 | 95.6% | 78.6% |
| 85099B | ridge | 102.06 | +22.27 | 75.8% | 78.6% |
| 85123A | seasonal_naive | 64.18 | -44.04 | 57.9% | 85.7% |

## Error by forecast horizon

Each cell is one seven-day portion of the same holdout. Calendar effects and horizon effects are confounded here; a rolling-origin experiment is needed to separate them.

| Product | Days ahead | Observations | MAE | Bias | Band coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| 22423 | 1–7 | 7 | 23.29 | +11.00 | 85.7% |
| 22423 | 8–14 | 7 | 19.43 | +2.29 | 85.7% |
| 22423 | 15–21 | 7 | 32.29 | +4.57 | 71.4% |
| 22423 | 22–28 | 7 | 36.29 | -7.43 | 71.4% |
| 85099B | 1–7 | 7 | 181.47 | -11.30 | 57.1% |
| 85099B | 8–14 | 7 | 51.72 | +33.51 | 100.0% |
| 85099B | 15–21 | 7 | 39.71 | +37.33 | 100.0% |
| 85099B | 22–28 | 7 | 135.32 | +29.54 | 57.1% |
| 85123A | 1–7 | 7 | 102.00 | -99.43 | 71.4% |
| 85123A | 8–14 | 7 | 17.57 | -7.57 | 100.0% |
| 85123A | 15–21 | 7 | 68.57 | -41.14 | 85.7% |
| 85123A | 22–28 | 7 | 68.57 | -28.00 | 85.7% |

## High-demand days

A high-demand day exceeds the product's 90th-percentile demand in its pre-holdout history (including validation). The cutoff never uses holdout values. This retrospective label explains failures; it is not known when a forecast is made. Missing groups have zero observations and are omitted.

| Product | Group | Pre-holdout cutoff | Days | MAE | Bias | Band coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 22423 | other | 70 | 26 | 21.19 | +11.58 | 84.6% |
| 22423 | high | 70 | 2 | 114.00 | -114.00 | 0.0% |
| 85099B | other | 329 | 25 | 73.66 | +65.59 | 84.0% |
| 85099B | high | 329 | 3 | 338.70 | -338.70 | 33.3% |
| 85123A | other | 171 | 22 | 30.64 | -5.00 | 100.0% |
| 85123A | high | 171 | 6 | 187.17 | -187.17 | 33.3% |

## Two largest misses per product

These examples are selected by absolute error after evaluation and are not representative averages.

| Product | Date | Days ahead | Actual | Forecast | Absolute error | In band? |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 22423 | 2011-12-06 | 26 | 155 | 10.00 | 145.00 | no |
| 22423 | 2011-11-29 | 19 | 93 | 10.00 | 83.00 | no |
| 85099B | 2011-11-14 | 4 | 640 | 172.83 | 467.17 | no |
| 85099B | 2011-12-02 | 22 | 483 | 112.79 | 370.21 | no |
| 85123A | 2011-11-14 | 4 | 374 | 31.00 | 343.00 | no |
| 85123A | 2011-11-15 | 5 | 349 | 97.00 | 252.00 | no |

## Interpretation and next experiment

- Compare bias with high-demand errors before adding model complexity. Sales spikes and stock availability are not explained by this dataset's daily quantities alone; the report does not establish a causal explanation.
- Exploratory bands were calibrated on 14-day validation forecasts and evaluated here over 28 days. They do not promise 90% future coverage. Check calibration separately at the intended deployment horizon.
- Weekday metrics are in `error-slices.csv`; each weekday has just four observations per product. Treat apparent differences as hypotheses.
- Freeze this report as a historical experiment. Predeclare a new rolling-origin protocol before comparing another candidate or changing parameters; repeatedly tuning on this known holdout would invalidate a fresh-test claim.
- Demand-only ordering recommendations are illustrative. These errors do not demonstrate reduced stockouts, increased revenue or a deployable purchasing policy.

## Reproduce

```bash
python -m forecast.train
python -m forecast.diagnostics
```

Outputs: `outputs/error-analysis/ERROR-ANALYSIS.md`, `holdout-residuals.csv`, `error-slices.csv` and `metadata.json`. The command checks that the source checksum matches the frozen model artifact before calculating anything.

Source SHA-256: `0c846be735eb92ef338d265aaef1a9199028a5670fe5577918d4ec6669ee78c2`.
