# Evaluation report

Measured on the attributed UCI-derived daily dataset. Three products, 373 days each (2010-12-01 to 2011-12-08). Holdout: 2011-11-11 to 2011-12-08.

Product selection uses only the first 120 days. Four earlier 14-day folds choose a model by MAE. The holdout is reported once and is not used to change that choice.

| Product | Selected | Validation MAE | Holdout MAE | Holdout WAPE | Band coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| 22423 | seasonal_naive | 16.45 | 27.82 | 95.6% | 78.6% |
| 85099B | ridge | 142.96 | 102.06 | 75.8% | 78.6% |
| 85123A | seasonal_naive | 76.88 | 64.18 | 57.9% | 85.7% |

MAE is in units per day. WAPE is total absolute error divided by total observed units. Coverage is the share of holdout days inside the exploratory error band, not simultaneous coverage.

## Both candidates on the same holdout

| Product | Weekly baseline MAE | Ridge MAE |
| --- | ---: | ---: |
| 22423 | 27.82 | 17.97 |
| 85099B | 270.64 | 102.06 |
| 85123A | 64.18 | 65.82 |

## Interpretation

- For 85099B, Ridge improved holdout MAE relative to the weekly baseline in this experiment. This does not imply general retail superiority.
- For 22423, validation favoured the baseline narrowly, but Ridge performed better on the later holdout. The selected model was kept unchanged to avoid selecting on test data.
- For 85123A, the simpler baseline remained competitive. Complexity did not consistently help.
- Large errors and below-90% band coverage limit the usefulness of these forecasts for purchasing. Promotions, stock availability and wholesale order patterns are missing.
- No cost savings, stockout reduction or business deployment is claimed.

## Reproduce

`python -m forecast.train` regenerates the artifact from the bundled public aggregate. Its SHA-256 source fingerprint is stored in the artifact. Tests cover future-target leakage, the weekly baseline, malformed daily series and API validation.

Next experiments should use new chronological evaluation windows, not repeatedly tune against this holdout.
