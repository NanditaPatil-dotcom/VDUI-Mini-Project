# Model Performance validation (report data vs existing CSV outputs)

The report reads these CSVs unchanged. Validated metrics were **not** modified; this only checks internal consistency.

| Result | Check | Detail |
|---|---|---|
| PASS | cleaned file: 129,487 passenger rows x 24 columns | 129,487 x 24 |
| PASS | cleaned file: 73,225 Neutral/Dissatisfied and 56,262 Satisfied | 56.55% / 43.45% |
| PASS | tiered file = cleaned file + 2 columns, identical rows in identical order (tier can be attached by position) | 24 shared columns identical |
| PASS | unfiltered passenger count (rows = Total Passengers) is 129,487 | 129,487 rows |
| PASS | Satisfied + Neutral/Dissatisfied = total | 56,262 satisfied |
| PASS | High + Average + Low tier = total | High 42,695 |
| PASS | DimTravel: left-outer merge keeps every passenger and finds every key | 6 dimension rows, 129,487 fact rows |
| PASS | DimPassengerProfile: left-outer merge keeps every passenger and finds every key | 16 dimension rows, 129,487 fact rows |
| PASS | DimSatisfaction: left-outer merge keeps every passenger and finds every key | 6 dimension rows, 129,487 fact rows |
| PASS | FactServiceRating rows = 14 x passengers after unpivot | 1,812,818 rows |
| PASS | row_index values in SHAP local file = Gemini passengers | [np.int64(2884), np.int64(76523)] |
| PASS | passenger 2884: SHAP rows, predicted class and probability agree between SHAP file and Gemini file | 22 SHAP rows, Neutral or Dissatisfied, p=0.9988, 1 recommendation row(s) |
| PASS | passenger 76523: SHAP rows, predicted class and probability agree between SHAP file and Gemini file | 22 SHAP rows, Satisfied, p=0.9995, 2 recommendation row(s) |
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

**50 of 50 checks passed.**
