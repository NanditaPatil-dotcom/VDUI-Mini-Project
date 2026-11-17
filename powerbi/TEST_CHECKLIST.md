# Manual test checklist (Power BI Desktop) – nothing below has been run by me

I generated and statically checked the project, but I cannot run Power BI Desktop here. Tick each line yourself and send me
any line that fails (screenshot or the red error text). **Do not treat any item as "fixed" until you have ticked it.**

## 0. Open
- [ ] Delete old `Team11_Final.*` items in `powerbi/`, unzip `Team11_Final_pbip.zip`, open `Team11_Final.pbip`.
- [ ] `RepoRoot` parameter = your repo folder. Close & Apply finishes with no red errors (10–15 min the first time).
- [ ] Model view: relationships include `shap_local_explanations → shap_importance` (Nandita's) and `shap_local_explanations → PassengerSelectorTable` (added so her slicer drives her cards/bars).

Demo steps with exact clicks: `DRILL_DOWN_STEPS.md`, `DRILL_THROUGH_STEPS.md`, `DEMO_GUIDE.md`.

## 1. AI EXPLAINABILITY (copied from AI_Explainability.pbix)
- [ ] Page shows: Top-5 SHAP chart, Gemini explanation, individual SHAP bars, probability / predicted-class / actual-class cards, passenger list slicer, recommendations table, Key Explainability Findings text.
- [ ] Slicer starts on 76523. Pick 2884 → SHAP bars, probability, predicted/actual class, Gemini explanation AND recommendations all change (1 recommendation row for 2884, 2 for 76523). Pick 76523 again → they change back.
- [ ] Compare side by side with `AI_Explainability.pbix` (unchanged in the repo): same fields, same text.

## 2. Navigation, slicers, interactions
- [ ] Every page has the same navy title bar with the three centred white lines (BEYOND THE BOARDING PASS / Uncovering the Key Drivers of Airline Passenger Satisfaction / TEAM 11 | PASSENGER EXPERIENCE ANALYTICS) and no header buttons. The standard page tabs at the bottom switch pages.
- [ ] Overview "Follow the story" buttons open Overview / EDA / AI Explainability / Conclusion.
- [ ] Conclusion buttons open Overview, EDA, AI Explainability and Passenger Segment Detail (hidden drill-through page; the button just opens it unfiltered).
- [ ] Slicers Gender / Class / Customer Type / Type of Travel on Overview: KPI cards, donut, class chart, findings table update.
- [ ] Go to EDA: the same slicer selections are still applied (View > Sync slicers shows the four groups on Overview and EDA).
- [ ] Click a bar in the class chart: other visuals on the page cross-filter. Click again to clear.
- [ ] Passenger Segment Detail: the matrix shows Total Passengers, Satisfaction Rate, High Tier Rate, delays, distance and service rating (no "Something went wrong").
- [ ] EDA class chart: use the drill arrows (down arrow, "expand to next level"): Class → Type of Travel; up arrow drills back.
- [ ] Right-click a class bar → Drill through → Passenger Segment Detail opens with that class; the **← Back** button returns to the page you came from with your filters intact.
- [ ] Model page: Model slicer and Passenger-attribute slicer change the charts.

## 3. Findings text
- [ ] Overview "Key findings" and Conclusion "What the data says" / "Recommendations" are static text boxes generated from the CSVs (they do not change with slicers; that is stated on each box). The earlier dynamic "Live observations" visual was removed because its DAX could not be made reliable.

## 4. Numbers
- [ ] Overview cards equal `expected_values.csv` (129,487 passengers, 43.4 % satisfied, XGBoost best Macro F1 96.4 %).
- [ ] `validation_report.md` shows 37/37 checks passed (models, 5-fold CV, error bands, confusion matrices, subgroups, SHAP vs correlation).

## 5. Layout
- [ ] No visual overlaps or is cut off on any page (View > Selection pane to inspect). Each page has at most 5 charts/tables.
- [ ] Bookmarks (View > Bookmarks): the four story bookmarks exist; they are optional (the buttons use page navigation).
