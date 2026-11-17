# Presentation script – Beyond the Boarding Pass (Team 11)
Power BI data model, dashboard and integration · about 8–9 minutes · every number below comes from the project CSVs (`DATA_AUDIT.md`)

## 1. Opening and what I built (1 min)
"Our question is: what drives airline passenger satisfaction, and can a model predict and explain it? We have 129,487 cleaned passenger records. My part was the Power BI side: the data model, the DAX measures, the dashboard and putting my teammates' results together. Nandika did the correlations and model comparison, Anusha the Random Forest and XGBoost models and subgroup analysis, Nandita the SHAP and Gemini explanations."

"Behind the dashboard I built a star schema. One fact table has one row per passenger, loaded from the cleaned file. Small dimension tables for travel (class, type of travel), passenger profile (gender, customer type, age band) and satisfaction feed it. The 14 service ratings are unpivoted into a second fact table, so we can compare services. Filters flow one way, from dimensions to facts, so a slicer can never double-count."

"One design rule: satisfaction is always the original binary column. The Low / Average / High tier is a separate derived label built from six service ratings, so we show it on its own and never use it as a predictor."

## 2. Overview page (1.5 min)
"The title bar is the same on every page. The five cards are DAX measures, not typed numbers:
- **Total Passengers 129,487** – a distinct count of the passenger ID.
- **Satisfaction Rate 43.45 %** and **Neutral/Dissatisfied 56.55 %** – satisfied (or not) divided by total, using DIVIDE so an empty filter never divides by zero.
- **Average Service Rating 3.28** – the average of valid ratings only. A zero means not applicable, so it is excluded and never counted as a bad score.
- **High Tier Count 42,695** – passengers in the top third of the tier split."

"The donut shows the 43/57 split. The tier chart shows the three tiers are about equal thirds by design. The class chart shows the story in one glance: **Business 69 % satisfied, Economy 19 %, Economy Plus 25 %**. The SHAP chart shows what the model relies on most: in-flight Wi-Fi, type of travel, customer type, online boarding, class."

"The four slicers (gender, class, customer type, type of travel) are checkbox lists on the right. They are synced, so a selection on Overview stays on the EDA page. Notice the model-level charts don't move when I filter – SHAP is about the model, not individual passengers. If I tick Female, the count becomes 65,703; clearing the filters brings back 129,487."

## 3. EDA page – the main demo (2.5 min)
"The EDA page answers: how do class, delay and service quality relate to satisfaction? It has four KPI cards (passengers, satisfaction rate, average arrival delay 15.1 min, average service rating) and four charts."

**Class chart (drill-down).** "Bars are 100 % stacked, so we compare percentages inside each class, not raw counts. This chart has a hierarchy, Class → Type of Travel. I click the down arrow to turn drill mode on, click Business, and it splits into business and personal travel. The up arrow drills back up. Personal travellers are only about 10 % satisfied, business travellers about 58 %, so the class gap is partly a trip-purpose gap."

**Drill-through.** "Now I tick Female in the slicer. I right-click the Economy bar, choose Drill through, then Passenger Segment Detail. A detail page opens already filtered to Economy and Female: passenger count, satisfaction rate, high-tier rate, delays, distance and average rating by segment, plus the rating by service. I click the amber Back button at the top left and I am back on EDA with the Female filter still on. We used drill-through because a judge can go from the summary to the exact segment in two clicks, with the filters carried over automatically."

**Delay chart.** "Satisfaction falls from about 46 % on time to 36 % when arrival is more than 15 minutes late. 22.8 % of passengers arrive that late."

**Service survey and rating gap.** "The survey chart shows Poor (1–2), Average (3) and Good (4–5) as a share of rated answers only; zeros are excluded from the denominator. The rating-gap chart is the satisfied group's average rating minus the unhappy group's. Online boarding has the biggest gap, +1.45, then entertainment and Wi-Fi. The lowest-rated service overall is in-flight Wi-Fi at 2.81 out of 5."

## 4. Model Performance (1.5 min)
"Anusha's models are evaluated on the same held-out test set of 25,898 passengers. **XGBoost is best: accuracy 96.43 %, Macro F1 96.36 %, ROC-AUC 0.995**; Random Forest 95.98 % F1; Logistic Regression 90.15 %. We use Macro F1 because it weights both classes equally, and ROC-AUC because it measures ranking quality independent of a threshold."

"Cross-validation checks stability: five folds, mean Macro F1 0.9636 with a standard deviation of 0.0014, so the result isn't a lucky split. The subgroup chart shows recall for the satisfied class by group. It is lowest for Personal travel (59.8 %) and highest for Business class (98.6 %). That is a performance gap to investigate, caused partly by class balance, not proof of discrimination."

## 5. AI Explainability (1 min)
"This page is Nandita's work, copied exactly into the report. SHAP shows which features push a prediction up or down. In the `row_index` list I pick 2884: the model predicts Neutral/Dissatisfied with 99.88 % probability, the bars show Type of Travel and Wi-Fi pulling it down, and Gemini writes a plain-language explanation and one recommendation. I pick 76523: predicted Satisfied, 99.95 %, with two recommendations. Gemini only restates the SHAP values; it doesn't invent numbers."

## 6. Close and honest limitations (30 s)
"In summary: a clean star schema, DAX measures that trace back to the data, synced slicers, drill-down and drill-through, and validated model results. Limits: findings show association, not cause; the tier is derived from six ratings; subgroup gaps need more data before any fairness claim; and there is no date or route field, so no time trend or map."

---
## Likely questions
- **Why 129,487, not 129,880?** The Kaggle original has more rows; our validated cleaned file has 129,487, and everything is built on that.
- **Why 100 % stacked?** The classes have very different sizes; percentages inside each bar compare fairly.
- **Why is the average rating 3.28 and not 3.21?** 3.21 averages only six attributes with zeros included (used only to cut the tiers). 3.28 uses all 14 attributes, excluding N/A.
- **Why do the slicers not change SHAP?** SHAP and model results are model-level; they have no passenger key to filter.
- **Is XGBoost's high accuracy leakage?** The models train on the cleaned file, which has no tier or average-rating column; both target columns are dropped from the inputs, and all three models use the same train/test row indices (training and test rows never overlap).
- **Where is each number from?** `DATA_AUDIT.md` (KPIs) and `validation_report.md` (models, CV, subgroups).
