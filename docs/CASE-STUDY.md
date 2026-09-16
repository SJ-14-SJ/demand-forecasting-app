# A forecasting service that exposes its mistakes

## Question and scope

Can a simple trained model improve on repeating last week's sales, and can its limitations be made visible in a usable application?

DemandLab studies three products from UCI Online Retail, using 373 daily observations per product. It connects a reproducible Python experiment to a read-only FastAPI service and a React interface for forecast inspection and illustrative inventory scenarios. These are historical sales from 2010–2011, not predictions for a current retailer.

## Experimental decisions

| Decision | Reason | Evidence |
| --- | --- | --- |
| Select products using the first 120 days | Product choice must not depend on future holdout popularity. | [`provenance.json`](../data/provenance.json) |
| Compare with a weekly baseline | A trained model must justify its complexity against a useful simple alternative. | [`engine.py`](../forecast/engine.py) |
| Use lagged features and recursive forecasts | Future actual sales cannot be used when forecasting multiple days ahead. | Feature and leakage tests in [`test_engine.py`](../tests/test_engine.py) |
| Select on four earlier validation windows | Keep the last 28 days separate from model choice. | [Evaluation report](EVALUATION.md) |
| Audit frozen predictions by slice | An aggregate metric can hide systematic bias and large misses. | [Error analysis](ERROR-ANALYSIS.md) and [`diagnostics.py`](../forecast/diagnostics.py) |
| Serve a versioned JSON artifact | Training stays explicit, and the API does not need to execute a serialized Python model. | [`train.py`](../forecast/train.py) and [`api.py`](../forecast/api.py) |

## What the experiment found

Validation selected the weekly baseline for two products and Ridge for one. For product 85099B, Ridge's holdout MAE was 102.06 units/day versus 270.64 for the weekly baseline. For product 22423, the validation winner was not the best holdout model in hindsight; the original selection remained unchanged.

The error audit adds an important qualification. On the three high-demand holdout days for 85099B, MAE was 338.70 units/day, compared with 73.66 on the other 25 days. Its overall bias was positive, yet the high-demand group was underpredicted. A single average hides that difference. These groups are retrospective diagnostics with small counts, not a causal claim or a predictive spike detector.

Exploratory band coverage was 78.6%–85.7% across products. Bands based on 14-day validation errors did not establish 90% coverage for this 28-day holdout. The data lacks stock availability and promotion information, and calendar zero-filling assumes complete capture. These limitations matter before any purchasing use.

## Application evidence

- [Desktop screenshot](demo-desktop.png) and [mobile screenshot](demo-mobile.png).
- FastAPI routes validate product, horizon and inventory inputs; a missing artifact returns an explicit unavailable response.
- Browser tests exercise forecast controls, the accessible table, CSV download, inventory inputs, mobile overflow and failure/retry behaviour.
- The diagnostic command checks the source checksum and leaves the frozen artifact unchanged. CI retains generated reports alongside the trained artifact.

Run the [README setup](../README.md#run-locally), then inspect `/docs` for the API contract. There is currently no public hosted instance. Inventory recommendations are demand-only scenarios; no cost saving or stockout reduction has been measured.

## Next experiment

Predeclare a new rolling-origin protocol with the intended 28-day horizon, then compare an additional justified candidate and assess band calibration. Keep this original report as historical evidence rather than reusing its known holdout as a fresh final test.

Implemented with Codex assistance. The [development exercises](NEXT-STEPS.md) focus on explaining and extending the modelling and application choices.
