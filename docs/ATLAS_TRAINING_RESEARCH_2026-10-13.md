# Actual ATLAS model training: research and implementation decision

Reviewed 13 October 2026. Scope: the customer-agent XGBoost sales/CSAT model, as confirmed by Sam. “Premium” is evaluated as paid data access or managed training capability, not a guarantee of better predictions.

**Decision:** use the existing local XGBoost trainer and collect actual, linked outcomes first. Retain AWS SageMaker as the best-fitting paid training option when a justified workload and an AWS account exist. No paid provider has been activated and no real customer training session is claimed. Windows access and the existing bridge token are unavailable in the current connection.

## Paid training options

| Option | Verified capability | Fit for the present code | Activation requirement / status |
| --- | --- | --- | --- |
| AWS SageMaker AI | Built-in XGBoost and custom XGBoost training scripts; pinned container versions; CSV/LibSVM/Parquet inputs | Closest fit to preserving the paired sales/CSAT implementation. Custom-script mode is needed to preserve the native JSON bundle contract. | AWS account, IAM role, approved region/compute, S3 input/output and real dataset. Not configured. |
| Azure Machine Learning AutoML | Tries algorithms and hyperparameters for classification and regression; supports labeled data and final test evaluation | Useful for comparing alternatives. Its resulting model format cannot be substituted directly for the current XGBoost bundle loader. | Azure subscription, workspace, compute, dataset and evaluated model adapter. Not configured. |
| Google Cloud tabular AutoML | Structured classification/regression; CSV or BigQuery; chronological or manual splitting | Supports this problem type, but requires at least 1,000 rows. A model adapter would be required. | Cloud project, billing, storage and suitable labeled data. Not configured. |
| Local XGBoost | Scikit-learn interface, explicit validation/early stopping and configurable CPU threads | Already implemented, preserves current runtime, no new cloud subscription. Uses one CPU thread per model. | Connected ATLAS Windows service and enough observed outcomes. Source ready; live intake connection pending. |

Cloud providers supply compute and orchestration; they do not supply Sam's customer outcomes. AWS managed warm pools are themselves billable. Azure documents VM, storage and related infrastructure costs, including some stopped-resource costs. No total price is quoted without a region, resource size, duration and budget.

## Sources of actual training data

| Source | Useful evidence | Gap that must be resolved |
| --- | --- | --- |
| ATLAS owner-recorded outcomes | Direct numeric snapshots, outcome time, actual sale result and actual CSAT | Values must come from completed interactions and pre-interaction agent measurements. Manual confirmation is an assertion, not independent verification. |
| Zendesk paid CSAT access | Incremental ticket exports, audit events and numeric survey response ratings; CSAT responses available on Support Professional+ or Suite Growth+ | Must join to the actual sale and immutable pre-interaction features. Preserve the documented survey scale. Legacy good/bad scores are not 1..5 observations. No Zendesk tenant/token has been supplied or connected. |
| CRM deal events, such as HubSpot | Documented deal-change webhooks provide a route to capture completed commercial outcomes | A deal is not automatically an agent interaction. Requires a reliable interaction-ID association, CSAT measurement, attribution and feature history. No automatic import was activated. |
| UCI Bank Marketing | Actual historical telephone campaign data with a deposit-subscription target | Different population and feature schema; no matching agent CSAT target. Cannot replace this paired training dataset. Contact duration is known after the contact and would leak future information into pre-contact routing. |

None of the examined public datasets was validated as a complete drop-in source containing all five ATLAS agent features, linked sale outcomes and 1..5 observed CSAT. Missing fields must not be invented to make a paid or public dataset fit.

## Applied to the code

- Protected Google-owner model UI, scoring, observed-outcome intake and bounded offline training route.
- Duplicate protection by interaction ID, including safe retry and transactional migration from the early timestamp-unique schema.
- Chronological splitting that keeps simultaneous groups together and accommodates mixed timestamp precision.
- Shared OS writer lock across API workers and CLI sessions; atomic paired native-JSON model publication.
- Session ID, dataset hash, time ranges and best iterations in model metadata. Held-out log loss and CSAT MAE are compared with constants calculated only from training targets.
- Previous rankings are invalidated when their inputs or weights change, and obsolete in-flight results are ignored.
- Minimum 50 rows and both sale classes in every chronological part. This is a technical minimum; production readiness remains false.
- XGBoost minimum raised to 3.1.3 after reproducing a save failure with scikit-learn1.8/XGBoost3.0.5 and checking the official compatibility fix. No Windows environment upgrade was performed while disconnected.

MLflow's documented XGBoost autologging is a useful later experiment-tracking option. The current metadata captures essential provenance without introducing an additional service or sending customer data elsewhere. MLflow is not installed or connected in production.

## Commercial decision

Keep the feature if an observed-data pilot improves conversion or service quality enough to cover its operating cost. Compare routed interactions against the existing allocation policy under comparable customer mix; record conversion, actual CSAT, handling time and net contribution after cost. Offline AUC or MAE alone cannot establish incremental revenue or causal benefit. Consider a controlled pilot only after adequate actual data and satisfactory baseline comparisons. Paid cloud capacity is justified by measured training time, scale or team-management requirements, not by the word “premium.”

## Primary references

1. XGBoost sklearn interface: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html
2. XGBoost3.1.3 compatibility fix: https://xgboost.readthedocs.io/en/stable/changes/v3.1.0.html
3. SageMaker XGBoost/custom scripts: https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-how-to-use.html
4. SageMaker pricing: https://aws.amazon.com/sagemaker/ai/pricing/
5. SageMaker warm pool billing: https://docs.aws.amazon.com/sagemaker/latest/dg/train-warm-pools.html
6. Azure AutoML: https://learn.microsoft.com/en-us/azure/machine-learning/concept-automated-ml?view=azureml-api-2
7. Azure costs: https://learn.microsoft.com/en-us/azure/machine-learning/concept-plan-manage-cost?view=azureml-api-2
8. Google tabular training requirements: https://cloud.google.com/vertex-ai/docs/tabular-data/classification-regression/prepare-data
9. Zendesk CSAT export and plan eligibility: https://developer.zendesk.com/documentation/ticketing/data-and-reporting/incremental-ticket-export-csat/
10. Zendesk numeric rating structure: https://developer.zendesk.com/api-reference/ticketing/ticket-management/csat_survey_responses/
11. HubSpot webhook configuration: https://developers.hubspot.com/docs/apps/developer-platform/build-apps/features/configure-webhooks
12. UCI Bank Marketing: https://archive.ics.uci.edu/dataset/222/bank+marketing
13. MLflow XGBoost integration: https://mlflow.org/docs/latest/ml/traditional-ml/xgboost/
