# Make this project your own

1. Run both models and explain why model selection cannot use the final holdout.
2. Trace the lag and rolling features for one date by hand.
3. Investigate product 22423: the validation winner was not the best model in hindsight. Keep the original holdout report; use a new future holdout for later experiments.
4. Add one justified candidate, such as a model for intermittent demand or gradient boosting. Select its settings using validation only.
5. Review the implemented [horizon and high-demand error analysis](ERROR-ANALYSIS.md). Design an additional rolling-origin evaluation to separate calendar effects from horizon effects; the current horizon slices come from only one origin.
6. Add promotions or holidays only when the information would have been available at prediction time.
7. Extend inventory planning to costs, open orders and safety stock, with clearly labelled simulation assumptions.
8. Add actuals ingestion and rolling error monitoring before claiming production readiness.

For interviews, be ready to explain the API contract, frontend request cancellation, failure states, source-data assumptions and why a baseline can outperform a trained model.
