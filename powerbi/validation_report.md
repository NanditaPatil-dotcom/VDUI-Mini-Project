# Model Performance validation (report data vs existing CSV outputs)

The report reads these CSVs unchanged. Validated metrics were **not** modified; this only checks internal consistency.

| Result | Check | Detail |
|---|---|---|
| PASS | CV folds = 5 (Logistic Regression) | 5 folds |
| PASS | CV mean matches model_comparison (Logistic Regression) | 0.901128 vs 0.901128 |
| PASS | CV std (ddof=1) matches model_comparison (Logistic Regression) | 0.000550 vs 0.000550 |
| PASS | error band [0.9006, 0.9017] brackets most folds (Logistic Regression) | 4/5 folds inside the band |
| PASS | CV folds = 5 (Random Forest) | 5 folds |
| PASS | CV mean matches model_comparison (Random Forest) | 0.958302 vs 0.958302 |
| PASS | CV std (ddof=1) matches model_comparison (Random Forest) | 0.001019 vs 0.001019 |
| PASS | error band [0.9573, 0.9593] brackets most folds (Random Forest) | 3/5 folds inside the band |
| PASS | CV folds = 5 (XGBoost) | 5 folds |
| PASS | CV mean matches model_comparison (XGBoost) | 0.963584 vs 0.963584 |
| PASS | CV std (ddof=1) matches model_comparison (XGBoost) | 0.001435 vs 0.001435 |
| PASS | error band [0.9621, 0.9650] brackets most folds (XGBoost) | 3/5 folds inside the band |
| PASS | confusion matrix total = test rows (Logistic Regression) | 25898 vs 25898 |
| PASS | accuracy from confusion matrix = model_comparison (Logistic Regression) | 0.903236 vs 0.903236 |
| PASS | Power BI confusion measures (sum of Gender subgroups) = confusion matrix (Logistic Regression) | (np.int64(13409), np.int64(1236), np.int64(1270), np.int64(9983)) vs (np.int64(13409), np.int64(1236), np.int64(1270), np.int64(9983)) |
| PASS | confusion matrix total = test rows (Random Forest) | 25898 vs 25898 |
| PASS | accuracy from confusion matrix = model_comparison (Random Forest) | 0.960615 vs 0.960615 |
| PASS | Power BI confusion measures (sum of Gender subgroups) = confusion matrix (Random Forest) | (np.int64(14279), np.int64(366), np.int64(654), np.int64(10599)) vs (np.int64(14279), np.int64(366), np.int64(654), np.int64(10599)) |
| PASS | confusion matrix total = test rows (XGBoost) | 25898 vs 25898 |
| PASS | accuracy from confusion matrix = model_comparison (XGBoost) | 0.964322 vs 0.964322 |
| PASS | Power BI confusion measures (sum of Gender subgroups) = confusion matrix (XGBoost) | (np.int64(14347), np.int64(298), np.int64(626), np.int64(10627)) vs (np.int64(14347), np.int64(298), np.int64(626), np.int64(10627)) |
| PASS | subgroup passengers sum to test rows (Logistic Regression / Class) | 25898 |
| PASS | subgroup passengers sum to test rows (Logistic Regression / Customer Type) | 25898 |
| PASS | subgroup passengers sum to test rows (Logistic Regression / Gender) | 25898 |
| PASS | subgroup passengers sum to test rows (Logistic Regression / Type of Travel) | 25898 |
| PASS | subgroup passengers sum to test rows (Random Forest / Class) | 25898 |
| PASS | subgroup passengers sum to test rows (Random Forest / Customer Type) | 25898 |
| PASS | subgroup passengers sum to test rows (Random Forest / Gender) | 25898 |
| PASS | subgroup passengers sum to test rows (Random Forest / Type of Travel) | 25898 |
| PASS | subgroup passengers sum to test rows (XGBoost / Class) | 25898 |
| PASS | subgroup passengers sum to test rows (XGBoost / Customer Type) | 25898 |
| PASS | subgroup passengers sum to test rows (XGBoost / Gender) | 25898 |
| PASS | subgroup passengers sum to test rows (XGBoost / Type of Travel) | 25898 |
| PASS | subgroup Recall / Precision / FPR recompute from TP-FP-FN-TN | 0 mismatching rows of 27 |
| PASS | SHAP ranks are 1..N without gaps | 22 features |
| PASS | SHAP sorted by mean |SHAP| descending |  |
| PASS | SHAP and association rankings are positively related (rank correlation shown for info) | rank correlation over 22 shared features = 0.54 |

- Top-5 SHAP: In-flight Wifi Service, Type of Travel, Customer Type, Online Boarding, Class
- Top-5 |Spearman|: Online Boarding, In-flight Entertainment, In-flight Wifi Service, Seat Comfort, On-board Service

**37 of 37 checks passed.**
