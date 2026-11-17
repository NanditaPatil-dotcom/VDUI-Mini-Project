# Integration notes – Team11_Final

## Sources wired in (all relative to `RepoRoot`)
| Table | File | Owner |
|---|---|---|
| FactPassenger / dims / FactServiceRating | `airline_satisfaction_tiered.csv` (129,487 cleaned rows; no duplicate fact table loaded) | data prep |
| ModelComparison | `models/model_comparison.csv` | Nandika |
| CVScores | `models/cross_validation_scores.csv` | Nandika |
| SubgroupPerformance | `models/subgroup_model_comparison.csv` (3 models × 9 groups; positive class = *Satisfied*) | Anusha |
| ShapImportance | `explainability/shap_importance.csv` (22 features) | Nandita |
| ShapLocal | `explainability/shap_local_explanations.csv` | Nandita |
| GeminiInsights / GeminiRecommendations | `powerbi/data/*_flat.csv` ← flattened from `explainability/gemini_insights.json` by `build/prepare_data.py` | Nandita |
| CorrelationRanking | `correlation/correlation_ranking.csv` | Nandika |
| Images | beeswarm, error-band, XGBoost confusion matrix (embedded as report resources) | Nandita / Nandika |

Note: the repo-root `shap_importance.csv` (6 rows, Seat Comfort = 0) is an older export and is **not** used; the report reads the full `explainability/` file.

## Relationships (all one-to-many, single direction, active)
FactPassenger and FactServiceRating → DimTravel (TravelKey), DimPassengerProfile (ProfileKey), DimSatisfaction (SatisfactionKey);
FactServiceRating → DimServiceAttribute; ModelComparison / CVScores / SubgroupPerformance → DimModel; ShapLocal and GeminiRecommendations → GeminiInsights (Passenger Index).
No many-to-many, no bidirectional filters, no date table (the data has no flight date).

## Decisions worth knowing
* **Passenger ID** does not exist in the CSV; an index column is added in Power Query for DISTINCTCOUNT / drill-through. It is hidden and never used as an ML feature.
* **Zero ratings** = "not applicable" (matches the preprocessing used for the models) → excluded from `[Average Service Rating]`, shown as *Not Rated* in the survey chart.
* **Subgroup recall** is the recall of the *Satisfied* class (file convention). `[Recall Gap]` = max – min across the groups in view; gaps are labelled as performance diagnostics, not discrimination.
* **CV std-dev** shown is the sample std (ddof = 1) from `model_comparison.csv`.
* **Top-N** visuals use DAX (`[Top 5 SHAP]`, `[Top 10 SHAP]` return blank beyond the rank) so they stay correct when the SHAP file is refreshed.
* **Narrative text** (Key Findings, Conclusion, model conclusion) is produced by measures (`Insight - …`, rendered through the `Insights` helper table) so it re-computes with slicers. Only the "Analyst observations", "Recommendations" and "Limitations" boxes are static text, generated from the same CSVs at build time.

## Final checks to tick off in Desktop
- [ ] Model view: 12 relationships as above, all 1:* single (the build script keeps them in `relationships.tmdl`).
- [ ] Overview cards equal `expected_values.csv` (129,487 / 43.4 % / 33.0 % / 3.28 / 96.4 %).
- [ ] Change each slicer – Overview, EDA and Service pages respond; Model pages do not (by design).
- [ ] Right-click a Class bar → Drill through → Passenger Segment Detail → Back.
- [ ] Hover a Top-5 SHAP bar → tooltip shows rank, correlation, avg rating, Gemini note.
- [ ] View → Bookmarks: click 1–4; buttons on Overview/Conclusion jump the same way.
- [ ] Optimize → Performance analyzer → record while changing slicers; heaviest object should be the 1.8 M-row survey chart.
- [ ] Confirm with the teacher whether the visual limit applies per page (KPI cards, charts, tables and slicers all count; Overview has ~17 data visuals).
- [ ] Save As `Team11_Final.pbix`; capture screenshots into `powerbi/final_dashboard_screenshots/`.
