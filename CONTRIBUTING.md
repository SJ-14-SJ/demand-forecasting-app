# Contributing

Use Python 3.12 and Node.js 22+. Follow the [local setup](README.md#run-locally), then make a focused change on a branch.

- **Forecasting:** state the hypothesis and chronological split before running comparisons. Keep the original holdout results; a known holdout cannot be reused as a fresh final test after tuning.
- **API:** document any response or validation changes and exercise the relevant route tests.
- **Interface:** check desktop and mobile controls, keyboard access and the API error state. Run the browser tests for interface changes.
- **Data:** retain provenance and licensing. Share aggregates and synthetic fixtures; do not add customer identifiers.

Run `python -m unittest discover -s tests -v`. When changing training or evaluation, also run `python -m forecast.train` and `python -m forecast.diagnostics`. The README lists the frontend build and browser checks. Include the commands you actually ran in the pull request.

Describe assistance from AI tools and verify the resulting code. Keep limitations and failed experiments in the report; measured error is more useful than an unsupported accuracy claim.
