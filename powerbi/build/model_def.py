"""Semantic model definition: Power Query (M) sources, columns, relationships and DAX measures."""
from tmdl import column as col, measure as ms, table as tbl, expression, relationship, q

RATING_COLS = [
    "Departure and Arrival Time Convenience", "Ease of Online Booking", "Check-in Service", "Online Boarding",
    "Gate Location", "On-board Service", "Seat Comfort", "Leg Room Service", "Cleanliness", "Food and Drink",
    "In-flight Service", "In-flight Wifi Service", "In-flight Entertainment", "Baggage Handling",
]
SERVICE_GROUPS = {
    "Ease of Online Booking": ("Pre-Flight", 1), "Check-in Service": ("Pre-Flight", 2),
    "Online Boarding": ("Pre-Flight", 3), "Gate Location": ("Pre-Flight", 4),
    "Departure and Arrival Time Convenience": ("Pre-Flight", 5),
    "Seat Comfort": ("Cabin Comfort", 6), "Leg Room Service": ("Cabin Comfort", 7), "Cleanliness": ("Cabin Comfort", 8),
    "Food and Drink": ("In-flight Service", 9), "In-flight Entertainment": ("In-flight Service", 10),
    "In-flight Wifi Service": ("In-flight Service", 11), "In-flight Service": ("In-flight Service", 12),
    "On-board Service": ("In-flight Service", 13), "Baggage Handling": ("Ground & Arrival", 14),
}

CSV_OPTS = 'Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv'


def csv_m(path, types, extra=""):
    """M for a simple CSV table. `types` = list of (col, m-type)."""
    tt = ", ".join('{"%s", %s}' % (c, t) for c, t in types)
    return f'''let
    Source = Csv.Document(File.Contents(Root & "{path}"), [{CSV_OPTS}]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{tt}}}, "en-US"){extra}
in
    {'Final' if extra else 'Typed'}'''


def inline_m(csv_path, types):
    """Embed a small CSV as an inline #table so no extra file is needed."""
    import os, pandas as pd
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    df = pd.read_csv(os.path.join(root, csv_path), keep_default_na=False)
    mt = {"type text": "text", "Int64.Type": "Int64.Type", "type number": "number"}
    hdr = ", ".join('#"%s" = %s' % (c, mt[t]) for c, t in types)
    def v(x, t):
        if t == "type text":
            return '"' + str(x).replace('"', '""') + '"'
        return str(x)
    rows = ", ".join("{" + ", ".join(v(r[c], t) for c, t in types) + "}" for _, r in df.iterrows())
    return f"""let
    Source = #table(type table [{hdr}], {{{rows}}})
in
    Source"""


# ---------------------------------------------------------------------------------------------------
# Expressions (parameter + staging query)
# ---------------------------------------------------------------------------------------------------
def expressions_tmdl():
    stg_types = [("Gender", "type text"), ("Age", "Int64.Type"), ("Customer Type", "type text"),
                 ("Type of Travel", "type text"), ("Class", "type text"), ("Flight Distance", "Int64.Type"),
                 ("Departure Delay", "type number"), ("Arrival Delay", "type number")]
    stg_types += [(c, "Int64.Type") for c in RATING_COLS]
    stg_types += [("Satisfaction", "type text"), ("satisfaction", "Int64.Type"),
                  ("avg_service_rating", "type number"), ("satisfaction_tier", "type text")]
    tt = ", ".join('{"%s", %s}' % (c, t) for c, t in stg_types)
    text_cols = ", ".join('{"%s", each Text.Trim(Text.Clean(_)), type text}' % c for c in
                          ["Gender", "Customer Type", "Type of Travel", "Class", "Satisfaction", "satisfaction_tier"])
    stg = f'''let
    // EXTRACT: one row per cleaned passenger record
    Source = Csv.Document(File.Contents(Root & "airline_satisfaction_tiered.csv"), [{CSV_OPTS}]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    // TRANSFORM: types, text clean-up, label standardisation
    Typed = Table.TransformColumnTypes(Promoted, {{{tt}}}, "en-US"),
    Cleaned = Table.TransformColumns(Typed, {{{text_cols}}}),
    // numeric 0/1 flag duplicates the text target (and differs only by letter case) -> drop it
    DropFlag = Table.RemoveColumns(Cleaned, {{"satisfaction"}}),
    Renamed = Table.RenameColumns(DropFlag, {{{{"Departure Delay", "Departure Delay in Minutes"}}, {{"Arrival Delay", "Arrival Delay in Minutes"}}, {{"satisfaction_tier", "Satisfaction Tier"}}, {{"avg_service_rating", "Passenger Avg Rating"}}}}),
    AddId = Table.AddIndexColumn(Renamed, "Passenger ID", 1, 1, Int64.Type),
    AgeBand = Table.AddColumn(AddId, "Age Band", each if [Age] < 25 then "Young (under 25)" else if [Age] < 40 then "Young Adult (25-39)" else if [Age] < 55 then "Adult (40-54)" else "Senior (55+)", type text),
    AgeSort = Table.AddColumn(AgeBand, "Age Band Sort", each if [Age] < 25 then 1 else if [Age] < 40 then 2 else if [Age] < 55 then 3 else 4, Int64.Type),
    DelayBucket = Table.AddColumn(AgeSort, "Delay Bucket", each if [#"Arrival Delay in Minutes"] <= 0 then "On time / early" else if [#"Arrival Delay in Minutes"] <= 15 then "1-15 min" else if [#"Arrival Delay in Minutes"] <= 60 then "16-60 min" else if [#"Arrival Delay in Minutes"] <= 120 then "61-120 min" else "Over 120 min", type text),
    DelaySort = Table.AddColumn(DelayBucket, "Delay Bucket Sort", each if [#"Arrival Delay in Minutes"] <= 0 then 1 else if [#"Arrival Delay in Minutes"] <= 15 then 2 else if [#"Arrival Delay in Minutes"] <= 60 then 3 else if [#"Arrival Delay in Minutes"] <= 120 then 4 else 5, Int64.Type),
    DistBand = Table.AddColumn(DelaySort, "Distance Band", each if [Flight Distance] < 500 then "Short (<500 mi)" else if [Flight Distance] < 1500 then "Medium (500-1,499 mi)" else if [Flight Distance] < 2500 then "Long (1,500-2,499 mi)" else "Ultra-long (2,500+ mi)", type text),
    DistSort = Table.AddColumn(DistBand, "Distance Band Sort", each if [Flight Distance] < 500 then 1 else if [Flight Distance] < 1500 then 2 else if [Flight Distance] < 2500 then 3 else 4, Int64.Type),
    TierSort = Table.AddColumn(DistSort, "Tier Sort", each if [Satisfaction Tier] = "Low" then 1 else if [Satisfaction Tier] = "Average" then 2 else 3, Int64.Type)
in
    TierSort'''
    out = [expression("RepoRoot", '"C:\\Users\\Nandika Gupta\\Downloads\\VDUI-Mini-Project-main\\VDUI-Mini-Project-main"', parameter=True),
           expression("Root", 'if Text.EndsWith(Text.Trim(RepoRoot), "\\") then Text.Trim(RepoRoot) else Text.Trim(RepoRoot) & "\\"', result="Text"),
           expression("stgPassenger", stg)]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------------------------------
def dim_m(cols, sort_cols, key):
    sel = ", ".join('"%s"' % c for c in cols)
    srt = ", ".join('{"%s", Order.Ascending}' % c for c in sort_cols)
    order = ", ".join('"%s"' % c for c in [key] + cols)
    return f'''let
    Source = stgPassenger,
    Kept = Table.SelectColumns(Source, {{{sel}}}),
    Distinct = Table.Distinct(Kept),
    Sorted = Table.Sort(Distinct, {{{srt}}}),
    Indexed = Table.AddIndexColumn(Sorted, "{key}", 1, 1, Int64.Type),
    Result = Table.ReorderColumns(Indexed, {{{order}}})
in
    Result'''


def tables():
    T = []

    # ---------------- Dimensions ----------------
    T.append(tbl("DimTravel", [
        col("TravelKey", "int64", hidden=True, fmt="0"),
        col("Class"), col("Type of Travel")],
        dim_m(["Class", "Type of Travel"], ["Class", "Type of Travel"], "TravelKey"),
        desc="One row per Class x Type of Travel combination."))
    T[-1] = T[-1].replace("\tpartition ", "\thierarchy 'Travel Hierarchy'\n\t\tlevel Class\n\t\t\tcolumn: Class\n\t\tlevel 'Type of Travel'\n\t\t\tcolumn: 'Type of Travel'\n\n\tpartition ", 1)

    T.append(tbl("DimPassengerProfile", [
        col("ProfileKey", "int64", hidden=True, fmt="0"),
        col("Gender"), col("Customer Type"),
        col("Age Band", sort_by="Age Band Sort"),
        col("Age Band Sort", "int64", hidden=True, fmt="0")],
        dim_m(["Gender", "Customer Type", "Age Band", "Age Band Sort"],
              ["Age Band Sort", "Gender", "Customer Type"], "ProfileKey"),
        desc="One row per Gender x Customer Type x Age Band combination."))

    T.append(tbl("DimSatisfaction", [
        col("SatisfactionKey", "int64", hidden=True, fmt="0"),
        col("Satisfaction"),
        col("Satisfaction Tier", sort_by="Tier Sort"),
        col("Tier Sort", "int64", hidden=True, fmt="0")],
        dim_m(["Satisfaction", "Satisfaction Tier", "Tier Sort"], ["Satisfaction", "Tier Sort"], "SatisfactionKey"),
        desc="Original binary satisfaction x derived Low/Average/High tier."))

    # ---------------- Fact: passengers ----------------
    keep = (["Passenger ID", "TravelKey", "ProfileKey", "SatisfactionKey", "Gender", "Customer Type", "Class",
             "Type of Travel", "Age Band", "Age Band Sort", "Satisfaction", "Satisfaction Tier", "Tier Sort",
             "Age", "Flight Distance", "Distance Band", "Distance Band Sort", "Departure Delay in Minutes",
             "Arrival Delay in Minutes", "Delay Bucket", "Delay Bucket Sort", "Passenger Avg Rating"] + RATING_COLS)
    keep_m = ", ".join('"%s"' % c for c in keep)
    fact_m = f'''let
    Source = stgPassenger,
    // LOAD: surrogate keys via Merge (Left Outer) against the dimensions
    JoinTravel = Table.NestedJoin(Source, {{"Class", "Type of Travel"}}, DimTravel, {{"Class", "Type of Travel"}}, "dt", JoinKind.LeftOuter),
    ExpTravel = Table.ExpandTableColumn(JoinTravel, "dt", {{"TravelKey"}}, {{"TravelKey"}}),
    JoinProfile = Table.NestedJoin(ExpTravel, {{"Gender", "Customer Type", "Age Band"}}, DimPassengerProfile, {{"Gender", "Customer Type", "Age Band"}}, "dp", JoinKind.LeftOuter),
    ExpProfile = Table.ExpandTableColumn(JoinProfile, "dp", {{"ProfileKey"}}, {{"ProfileKey"}}),
    JoinSat = Table.NestedJoin(ExpProfile, {{"Satisfaction", "Satisfaction Tier"}}, DimSatisfaction, {{"Satisfaction", "Satisfaction Tier"}}, "ds", JoinKind.LeftOuter),
    ExpSat = Table.ExpandTableColumn(JoinSat, "ds", {{"SatisfactionKey"}}, {{"SatisfactionKey"}}),
    Typed = Table.TransformColumnTypes(ExpSat, {{{{"TravelKey", Int64.Type}}, {{"ProfileKey", Int64.Type}}, {{"SatisfactionKey", Int64.Type}}}}),
    Result = Table.SelectColumns(Typed, {{{keep_m}}})
in
    Result'''
    fc = [col("Passenger ID", "int64", hidden=True, fmt="0"),
          col("TravelKey", "int64", hidden=True, fmt="0"),
          col("ProfileKey", "int64", hidden=True, fmt="0"),
          col("SatisfactionKey", "int64", hidden=True, fmt="0")]
    for c in ["Gender", "Customer Type", "Class", "Type of Travel", "Age Band", "Satisfaction", "Satisfaction Tier"]:
        fc.append(col(c, hidden=True, desc="Duplicate of the dimension attribute - use the Dim table in visuals."))
    for c in ["Age Band Sort", "Tier Sort", "Distance Band Sort", "Delay Bucket Sort"]:
        fc.append(col(c, "int64", hidden=True, fmt="0"))
    fc += [col("Age", "int64", fmt="0"), col("Flight Distance", "int64", fmt="#,0"),
           col("Distance Band", sort_by="Distance Band Sort"),
           col("Departure Delay in Minutes", "double", fmt="#,0.0"),
           col("Arrival Delay in Minutes", "double", fmt="#,0.0"),
           col("Delay Bucket", sort_by="Delay Bucket Sort"),
           col("Passenger Avg Rating", "double", fmt="0.00", hidden=True)]
    for c in RATING_COLS:
        fc.append(col(c, "int64", hidden=True, fmt="0", desc="Raw 1-5 rating, 0 = not applicable. Use FactServiceRating in visuals."))
    T.append(tbl("FactPassenger", fc, fact_m,
                 desc="Grain: one row per passenger record (surrogate Passenger ID). Not an ML feature."))

    # ---------------- Fact: service ratings (unpivot) ----------------
    ratings_list = ", ".join('"%s"' % c for c in RATING_COLS)
    sr_m = f'''let
    Source = FactPassenger,
    Kept = Table.SelectColumns(Source, {{"Passenger ID", "TravelKey", "ProfileKey", "SatisfactionKey", {ratings_list}}}),
    Unpivoted = Table.UnpivotOtherColumns(Kept, {{"Passenger ID", "TravelKey", "ProfileKey", "SatisfactionKey"}}, "Service Attribute", "Rating"),
    Typed = Table.TransformColumnTypes(Unpivoted, {{{{"Service Attribute", type text}}, {{"Rating", Int64.Type}}}})
in
    Typed'''
    sr_cols = [col("Passenger ID", "int64", hidden=True, fmt="0"),
               col("TravelKey", "int64", hidden=True, fmt="0"),
               col("ProfileKey", "int64", hidden=True, fmt="0"),
               col("SatisfactionKey", "int64", hidden=True, fmt="0"),
               col("Service Attribute"),
               col("Rating", "int64", fmt="0"),
               col("Rating Category", sort_by="Rating Category Sort", expr=(
                   "SWITCH(TRUE(),\n    ISBLANK(FactServiceRating[Rating]), BLANK(),\n"
                   "    FactServiceRating[Rating] = 0, \"Not Rated\",\n"
                   "    FactServiceRating[Rating] <= 2, \"Poor\",\n"
                   "    FactServiceRating[Rating] = 3, \"Average\",\n"
                   "    FactServiceRating[Rating] >= 4, \"Good\")")),
               col("Rating Category Sort", "int64", hidden=True, fmt="0", expr=(
                   "SWITCH(TRUE(),\n    FactServiceRating[Rating] = 0, 4,\n    FactServiceRating[Rating] <= 2, 1,\n"
                   "    FactServiceRating[Rating] = 3, 2,\n    3)"))]
    T.append(tbl("FactServiceRating", sr_cols, sr_m,
                 desc="Grain: one row per passenger x service attribute (14 attributes). Rating 0 = not applicable."))

    rows = ", ".join('{"%s", "%s", %d}' % (a, g, o) for a, (g, o) in SERVICE_GROUPS.items())
    T.append(tbl("DimServiceAttribute", [
        col("Service Attribute", sort_by="Attribute Order"),
        col("Service Group"), col("Attribute Order", "int64", hidden=True, fmt="0")],
        f'''let
    Source = #table(type table [#"Service Attribute" = text, #"Service Group" = text, #"Attribute Order" = Int64.Type], {{{rows}}})
in
    Source''', desc="Service attribute lookup with a logical grouping."))

    # ---------------- Model results ----------------
    models = '{"Logistic Regression", 1}, {"Random Forest", 2}, {"XGBoost", 3}'
    T.append(tbl("DimModel", [col("Model", sort_by="Model Sort"), col("Model Sort", "int64", hidden=True, fmt="0")],
                 f'''let
    Source = #table(type table [Model = text, #"Model Sort" = Int64.Type], {{{models}}})
in
    Source'''))

    mc_cols = ["Accuracy", "Macro Precision", "Macro Recall", "Macro F1", "ROC-AUC", "CV Macro F1 Mean", "CV Macro F1 Std"]
    T.append(tbl("ModelComparison",
                 [col("Model")] + [col(c, "double", fmt="0.0000") for c in mc_cols],
                 csv_m("models\\model_comparison.csv", [("Model", "type text")] + [(c, "type number") for c in mc_cols]),
                 desc="Held-out test metrics + 5-fold CV summary (source: models/model_comparison.csv)."))

    T.append(tbl("CVScores", [col("Model"), col("Fold", "int64", fmt="0"), col("Macro F1", "double", fmt="0.0000")],
                 csv_m("models\\cross_validation_scores.csv",
                       [("Model", "type text"), ("Fold", "Int64.Type"), ("Macro F1", "type number")]),
                 desc="Stratified 5-fold CV Macro F1 per model (source: models/cross_validation_scores.csv)."))

    sg_types = [("Model", "type text"), ("Attribute", "type text"), ("Group", "type text"), ("Sample Count", "Int64.Type"),
                ("Accuracy", "type number"), ("Precision", "type number"), ("Recall", "type number"), ("F1", "type number"),
                ("Macro F1", "type number"), ("FPR", "type number"), ("TN", "Int64.Type"), ("FP", "Int64.Type"),
                ("FN", "Int64.Type"), ("TP", "Int64.Type")]
    sg_extra = ''',
    Renamed = Table.RenameColumns(Typed, {{"Sample Count", "Passengers"}}),
    Final = Table.AddColumn(Renamed, "Group Label", each [Attribute] & ": " & [Group], type text)'''
    T.append(tbl("SubgroupPerformance", [
        col("Model"), col("Attribute"), col("Group"), col("Group Label"),
        col("Passengers", "int64", fmt="#,0"),
        col("Accuracy", "double", fmt="0.0%"), col("Precision", "double", fmt="0.0%"),
        col("Recall", "double", fmt="0.0%"), col("F1", "double", fmt="0.0%"),
        col("Macro F1", "double", fmt="0.0%"), col("FPR", "double", fmt="0.0%"),
        col("TN", "int64", fmt="#,0"), col("FP", "int64", fmt="#,0"), col("FN", "int64", fmt="#,0"), col("TP", "int64", fmt="#,0")],
        csv_m("models\\subgroup_model_comparison.csv", sg_types, sg_extra),
        desc="Per-model subgroup metrics on the held-out test set. Positive class = Satisfied."))

    T.append(tbl("MetricSelector", [col("Metric", sort_by="Metric Order"), col("Metric Order", "int64", hidden=True, fmt="0")],
                 '''let
    Source = #table(type table [Metric = text, #"Metric Order" = Int64.Type], {{"Accuracy", 1}, {"Macro Precision", 2}, {"Macro Recall", 3}, {"Macro F1", 4}, {"ROC-AUC", 5}})
in
    Source''', desc="Disconnected slicer table that drives [Selected Model Metric]."))

    # ---------------- Explainability ----------------
    T.append(tbl("ShapImportance", [
        col("Rank", "int64", fmt="0"), col("Feature"),
        col("Mean Absolute SHAP", "double", fmt="0.0000"), col("Mean SHAP", "double", fmt="0.0000"),
        col("Explained Output"), col("Sample Size", "int64", fmt="#,0")],
        csv_m("explainability\\shap_importance.csv",
              [("Rank", "Int64.Type"), ("Feature", "type text"), ("MeanAbsoluteSHAP", "type number"),
               ("MeanSHAP", "type number"), ("ExplainedOutput", "type text"), ("SampleSize", "Int64.Type")],
              ''',
    Final = Table.RenameColumns(Typed, {{"MeanAbsoluteSHAP", "Mean Absolute SHAP"}, {"MeanSHAP", "Mean SHAP"}, {"ExplainedOutput", "Explained Output"}, {"SampleSize", "Sample Size"}})'''),
        desc="Global mean |SHAP| for the selected model (source: explainability/shap_importance.csv)."))

    sl_types = [("row_index", "Int64.Type"), ("actual_class", "type text"), ("predicted_class", "type text"),
                ("predicted_class_probability", "type number"), ("probability_satisfied", "type number"),
                ("correct_prediction", "type text"), ("feature", "type text"), ("feature_value", "type text"),
                ("shap_value", "type number"), ("direction", "type text"), ("rank_by_absolute_contribution", "Int64.Type")]
    T.append(tbl("ShapLocal", [
        col("Passenger Index", "int64", fmt="0"), col("Actual Class"), col("Predicted Class"),
        col("Predicted Probability", "double", fmt="0.0%"), col("Probability Satisfied", "double", fmt="0.0%"),
        col("Correct Prediction"), col("Feature"), col("Feature Value"),
        col("SHAP Value", "double", fmt="0.0000"), col("Direction"), col("Contribution Rank", "int64", fmt="0")],
        csv_m("explainability\\shap_local_explanations.csv", sl_types,
              ''',
    Final = Table.RenameColumns(Typed, {{"row_index", "Passenger Index"}, {"actual_class", "Actual Class"}, {"predicted_class", "Predicted Class"}, {"predicted_class_probability", "Predicted Probability"}, {"probability_satisfied", "Probability Satisfied"}, {"correct_prediction", "Correct Prediction"}, {"feature", "Feature"}, {"feature_value", "Feature Value"}, {"shap_value", "SHAP Value"}, {"direction", "Direction"}, {"rank_by_absolute_contribution", "Contribution Rank"}})'''),
        desc="Local SHAP contributions for the explained passengers."))

    gi_types = [("Passenger Index", "Int64.Type"), ("Passenger Label", "type text"), ("Actual Class", "type text"),
                ("Predicted Class", "type text"), ("Predicted Probability", "type number"),
                ("Probability Satisfied", "type number"), ("Correct Prediction", "type text"), ("Explanation", "type text"),
                ("Evidence Features", "type text"), ("Uncertainty Note", "type text"), ("Gemini Model", "type text"),
                ("Generated At", "type text")]
    T.append(tbl("GeminiInsights", [
        col("Passenger Index", "int64", fmt="0"), col("Passenger Label"), col("Actual Class"), col("Predicted Class"),
        col("Predicted Probability", "double", fmt="0.0%"), col("Probability Satisfied", "double", fmt="0.0%"),
        col("Correct Prediction"), col("Explanation"), col("Evidence Features"), col("Uncertainty Note"),
        col("Gemini Model"), col("Generated At")],
        inline_m("powerbi/data/gemini_insights_flat.csv", gi_types),
        desc="One row per explained passenger, flattened from explainability/gemini_insights.json by build/prepare_data.py."))

    gr_types = [("Passenger Index", "Int64.Type"), ("Evidence Feature", "type text"),
                ("Recommendation", "type text"), ("Reason", "type text")]
    T.append(tbl("GeminiRecommendations", [
        col("Passenger Index", "int64", fmt="0"), col("Evidence Feature"), col("Recommendation"), col("Reason")],
        inline_m("powerbi/data/gemini_recommendations_flat.csv", gr_types)))

    cr_types = [("Feature", "type text"), ("Method", "type text"), ("EffectValue", "type number"),
                ("AbsoluteEffect", "type number"), ("PValue", "type number"), ("SampleCount", "Int64.Type"),
                ("AdjustedPValue", "type number")]
    T.append(tbl("CorrelationRanking", [
        col("Feature"), col("Method"), col("Effect Value", "double", fmt="0.000"), col("Absolute Effect", "double", fmt="0.000"),
        col("P-value", "double", fmt="0.0E+00"), col("Sample Count", "int64", fmt="#,0"),
        col("Adjusted P-value", "double", fmt="0.0E+00")],
        csv_m("correlation\\correlation_ranking.csv", cr_types,
              ''',
    Final = Table.RenameColumns(Typed, {{"EffectValue", "Effect Value"}, {"AbsoluteEffect", "Absolute Effect"}, {"PValue", "P-value"}, {"SampleCount", "Sample Count"}, {"AdjustedPValue", "Adjusted P-value"}})'''),
        desc="Correlation / association of each feature with satisfaction (source: correlation/correlation_ranking.csv). Methods are NOT directly comparable."))

    ins = [(1, "Headline", "Overview"), (2, "Who is happiest?", "Overview"), (3, "Delay effect", "Overview"),
           (4, "Service gap", "Overview"), (5, "Best model", "Conclusion"), (6, "Stability", "Conclusion"),
           (7, "Fairness check", "Conclusion"), (8, "Explainability", "Conclusion"), (9, "Where to act", "Conclusion"),
           (10, "Fix first", "Recommendation"), (11, "Protect the top driver", "Recommendation"), (12, "Target segments", "Recommendation"),
           (13, "Manage delays", "Recommendation"), (14, "Recognise strengths", "Recommendation"),
           (15, "Travel-type gap", "EDA"), (16, "Customer-type gap", "EDA"), (17, "Gender gap", "EDA")]
    rows = ", ".join('{%d, "%s", "%s"}' % r for r in ins)
    T.append(tbl("Insights", [col("Order", "int64", hidden=True, fmt="0"), col("Topic", sort_by="Order"), col("Page")],
                 f'''let
    Source = #table(type table [Order = Int64.Type, Topic = text, Page = text], {{{rows}}})
in
    Source''', desc="Helper table: each row renders one data-driven sentence through [Insight Text]."))
    T.extend(nandita_tables())
    return T


# ---------------------------------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------------------------------
def _top_bottom(table_expr, key_col, value_measure, kind):
    fn = "MAXX" if kind == "max" else "MINX"
    return (f"VAR t = ADDCOLUMNS({table_expr}, \"@v\", {value_measure})\n"
            f"VAR best = {fn}(t, [@v])\n"
            f"VAR who = MINX(FILTER(t, [@v] = best), {key_col})\n")


def nandita_tables():
    """Tables copied from AI_Explainability.pbix (names, columns, Power Query steps and measure kept as authored).
    Only the hard-coded C:\\Users\\nandi\\Downloads\\ file paths are swapped for the shared Root parameter."""
    import os, re
    base = os.path.join(os.path.dirname(__file__), "assets", "nandita")
    def m_of(name):
        txt = open(os.path.join(base, name + ".m"), encoding="utf-8").read()
        return re.sub(r'File\.Contents\("C:\\Users\\nandi\\Downloads\\([^"]+)"\)', r'File.Contents(Root & "explainability\\\1")', txt)
    out = []
    out.append(tbl("shap_importance", [
        col("Rank", "int64", fmt="0"), col("Feature"), col("MeanAbsoluteSHAP", "double"), col("MeanSHAP", "double"),
        col("ExplainedOutput"), col("SampleSize", "int64", fmt="0")], m_of("shap_importance")))
    out.append(tbl("shap_local_explanations", [
        col("row_index", "int64", fmt="0"), col("actual_class"), col("predicted_class"),
        col("predicted_class_probability", "double", fmt="0.0%"), col("probability_satisfied", "double", fmt="0.0%"),
        col("correct_prediction", "boolean"), col("feature"), col("feature_value"), col("shap_value", "double"),
        col("direction"), col("rank_by_absolute_contribution", "int64", fmt="0")], m_of("shap_local_explanations")))
    gi_cols = [col("status"), col("target.name"), col("target.class_0"), col("target.class_1"), col("target.probability_output"),
               col("model"), col("source"), col("generated_at_utc", "dateTime", fmt="General Date"),
               col("explanations.row_index", "int64", fmt="0"), col("explanations.actual_class"), col("explanations.predicted_class"),
               col("explanations.predicted_class_probability", "double"), col("explanations.probability_satisfied", "double"),
               col("explanations.correct_prediction", "boolean"), col("explanations.explanation")]
    gi_cols += [col(f"explanations.evidence_features.{i}") for i in range(5)]
    gi_cols += [col("evidence_feature"), col("recommendation"), col("reason"), col("explanations.uncertainty_note")]
    disp = ms("Gemini Explanation Display", """VAR SelectedPassenger =
    SELECTEDVALUE(PassengerSelectorTable[row_index])

RETURN
IF(
    ISBLANK(SelectedPassenger),
    "Select a passenger",
    CALCULATE(
        MAX(gemini_insights[explanations.explanation]),
        FILTER(
            ALL(gemini_insights),
            gemini_insights[explanations.row_index]
                = SelectedPassenger
        )
    )
)""")
    out.append(tbl("gemini_insights", gi_cols, m_of("gemini_insights"), measures=[disp]))
    pst = tbl("PassengerSelectorTable", [col("row_index", "int64", fmt="0")],
              """let
    Source = gemini_insights,
    Selected = Table.SelectColumns(Source, {"explanations.row_index"}),
    Renamed = Table.RenameColumns(Selected, {{"explanations.row_index", "row_index"}}),
    Result = Table.Distinct(Renamed)
in
    Result""", desc="Passenger list for the slicer: distinct explanations.row_index of gemini_insights (same values as the original calculated table).")
    out.append(pst)
    return out


def _gap(dim, noun_pl, sentence_tail=""):
    return (f"VAR hi = MAXX(VALUES({dim}), [Satisfaction Rate])\n"
            f"VAR lo = MINX(VALUES({dim}), [Satisfaction Rate])\n"
            f"VAR hiName = CONCATENATEX(TOPN(1, VALUES({dim}), [Satisfaction Rate], DESC), {dim}, \", \")\n"
            f"VAR loName = CONCATENATEX(TOPN(1, VALUES({dim}), [Satisfaction Rate], ASC), {dim}, \", \")\n"
            f"RETURN IF(COUNTROWS(VALUES({dim})) < 2, \"Select more than one {noun_pl} to compare.\", "
            f"hiName & \" is most satisfied (\" & FORMAT(hi, \"0.0%\") & \") vs \" & loName & \" (\" & FORMAT(lo, \"0.0%\") & \") - a \" & FORMAT((hi - lo) * 100, \"0.0\") & \"-pt gap by {noun_pl}.\")")


_SA = "DimServiceAttribute[Service Attribute]"
_GL = "SubgroupPerformance[Group Label]"
OVERRIDES = {
    "Lowest Rated Attribute": f'CONCATENATEX(TOPN(1, VALUES({_SA}), [Average Service Rating], ASC), {_SA}, ", ")',
    "Lowest Attribute Rating": f"MINX(VALUES({_SA}), [Average Service Rating])",
    "Highest Rated Attribute": f'CONCATENATEX(TOPN(1, VALUES({_SA}), [Average Service Rating], DESC), {_SA}, ", ")',
    "Highest Attribute Rating": f"MAXX(VALUES({_SA}), [Average Service Rating])",
    "Recall Gap (pts)": f"(MAXX(VALUES({_GL}), [Subgroup Recall]) - MINX(VALUES({_GL}), [Subgroup Recall])) * 100",
    "FPR Gap (pts)": f"(MAXX(VALUES({_GL}), [Subgroup FPR]) - MINX(VALUES({_GL}), [Subgroup FPR])) * 100",
    "Lowest Recall Group": f'CONCATENATEX(TOPN(1, VALUES({_GL}), [Subgroup Recall], ASC), {_GL}, ", ")',
    "Lowest Group Recall": f"MINX(VALUES({_GL}), [Subgroup Recall])",
    "Strongest Associated Feature": 'CONCATENATEX(TOPN(1, VALUES(CorrelationRanking[Feature]), [Absolute Effect], DESC), CorrelationRanking[Feature], ", ")',
    "Strongest Association Value": "MAXX(VALUES(CorrelationRanking[Feature]), [Absolute Effect])",
    "Insight - Class Gap": _gap("DimTravel[Class]", "travel class"),
    "Insight - Travel-type gap": _gap("DimTravel[Type of Travel]", "travel type"),
    "Insight - Customer-type gap": _gap("DimPassengerProfile[Customer Type]", "customer type"),
    "Insight - Gender gap": _gap("DimPassengerProfile[Gender]", "gender"),
    "Insight - Target segments": ('VAR lo = MINX(VALUES(DimTravel[Class]), [Satisfaction Rate])\n'
                                  'VAR loName = CONCATENATEX(TOPN(1, VALUES(DimTravel[Class]), [Satisfaction Rate], ASC), DimTravel[Class], ", ")\n'
                                  'RETURN "Target " & loName & " passengers (only " & FORMAT(lo, "0.0%") & " satisfied) with service recovery rather than blanket spend."'),
    "Insight - Fairness": ('VAR bm = [Best Model]\n'
                           f'VAR lo = MINX(ALL({_GL}), CALCULATE([Subgroup Recall], SubgroupPerformance[Model] = bm))\n'
                           f'VAR hi = MAXX(ALL({_GL}), CALCULATE([Subgroup Recall], SubgroupPerformance[Model] = bm))\n'
                           f'VAR loName = CONCATENATEX(TOPN(1, ALL({_GL}), CALCULATE([Subgroup Recall], SubgroupPerformance[Model] = bm), ASC), {_GL}, ", ")\n'
                           'RETURN "For " & bm & ", recall for the Satisfied class ranges from " & FORMAT(lo, "0.0%") & " (" & loName & ") to " & FORMAT(hi, "0.0%") '
                           '& ". This is a performance disparity to investigate (group size, class balance, threshold), not proof of discrimination."'),
}


def measure_list():
    M = []

    def add(name, dax, fmt=None, folder=None, desc=None, hidden=False):
        M.append(ms(name, OVERRIDES.get(name, dax), fmt, folder, desc, hidden))

    f1 = "1 Passenger KPIs"
    add("Total Passengers", "DISTINCTCOUNT(FactPassenger[Passenger ID])", "#,0", f1, "One row per passenger record.")
    add("Satisfied Passengers", 'CALCULATE([Total Passengers], FactPassenger[Satisfaction] = "Satisfied")', "#,0", f1)
    add("Neutral or Dissatisfied Passengers", 'CALCULATE([Total Passengers], FactPassenger[Satisfaction] = "Neutral or Dissatisfied")', "#,0", f1)
    add("Satisfaction Rate", "DIVIDE([Satisfied Passengers], [Total Passengers], 0)", "0.0%", f1)
    add("Dissatisfaction Rate", "DIVIDE([Neutral or Dissatisfied Passengers], [Total Passengers], 0)", "0.0%", f1)
    add("High Tier Passengers", 'CALCULATE([Total Passengers], FactPassenger[Satisfaction Tier] = "High")', "#,0", f1)
    add("Average Tier Passengers", 'CALCULATE([Total Passengers], FactPassenger[Satisfaction Tier] = "Average")', "#,0", f1)
    add("Low Tier Passengers", 'CALCULATE([Total Passengers], FactPassenger[Satisfaction Tier] = "Low")', "#,0", f1)
    add("High Tier Rate", "DIVIDE([High Tier Passengers], [Total Passengers], 0)", "0.0%", f1)
    add("Low Tier Rate", "DIVIDE([Low Tier Passengers], [Total Passengers], 0)", "0.0%", f1)
    add("Returning Passengers", 'CALCULATE([Total Passengers], DimPassengerProfile[Customer Type] = "Returning")', "#,0", f1)
    add("First-time Passengers", 'CALCULATE([Total Passengers], DimPassengerProfile[Customer Type] = "First-time")', "#,0", f1)
    add("Returning Share", "DIVIDE([Returning Passengers], [Total Passengers], 0)", "0.0%", f1)
    add("Business Travel Share", 'DIVIDE(CALCULATE([Total Passengers], DimTravel[Type of Travel] = "Business"), [Total Passengers], 0)', "0.0%", f1)
    add("Share of Passengers", "DIVIDE([Total Passengers], CALCULATE([Total Passengers], ALLSELECTED()), 0)", "0.0%", f1,
        "Share of the passengers currently selected by slicers.")
    add("Satisfaction Mix %", "DIVIDE([Total Passengers], CALCULATE([Total Passengers], REMOVEFILTERS(DimSatisfaction)), 0)", "0%", f1,
        "Share of a category's passengers in each satisfaction bucket - bars always add to 100%.")
    add("Overall Satisfaction Rate",
        "CALCULATE([Satisfaction Rate], REMOVEFILTERS(DimTravel), REMOVEFILTERS(DimPassengerProfile), REMOVEFILTERS(DimSatisfaction))",
        "0.0%", f1)
    add("Satisfaction Gap vs Overall (pts)", "([Satisfaction Rate] - [Overall Satisfaction Rate]) * 100", '+0.0;-0.0;0.0', f1)

    f2 = "2 Delay & Distance"
    add("Avg Departure Delay", "AVERAGE(FactPassenger[Departure Delay in Minutes])", "0.0", f2)
    add("Avg Arrival Delay", "AVERAGE(FactPassenger[Arrival Delay in Minutes])", "0.0", f2)
    add("Avg Flight Distance", "AVERAGE(FactPassenger[Flight Distance])", "#,0", f2)
    add("Avg Passenger Age", "AVERAGE(FactPassenger[Age])", "0.0", f2)
    add("Delayed Share",
        "DIVIDE(CALCULATE([Total Passengers], FactPassenger[Arrival Delay in Minutes] > 15), [Total Passengers], 0)", "0.0%", f2)
    add("Satisfaction Rate - On Time", "CALCULATE([Satisfaction Rate], FactPassenger[Arrival Delay in Minutes] <= 15)", "0.0%", f2)
    add("Satisfaction Rate - Delayed", "CALCULATE([Satisfaction Rate], FactPassenger[Arrival Delay in Minutes] > 15)", "0.0%", f2)
    add("Delay Satisfaction Penalty (pts)", "([Satisfaction Rate - Delayed] - [Satisfaction Rate - On Time]) * 100", "+0.0;-0.0;0.0", f2)

    f3 = "3 Service Ratings"
    add("Average Service Rating",
        "CALCULATE(AVERAGE(FactServiceRating[Rating]), FactServiceRating[Rating] > 0)", "0.00", f3,
        "Zero = not applicable, therefore excluded.")
    add("Rating Count", "COUNTROWS(FactServiceRating)", "#,0", f3)
    add("Rated Count", "CALCULATE(COUNTROWS(FactServiceRating), FactServiceRating[Rating] > 0)", "#,0", f3)
    add("Good Rating Share", "DIVIDE(CALCULATE(COUNTROWS(FactServiceRating), FactServiceRating[Rating] >= 4), [Rated Count], 0)", "0.0%", f3)
    add("Poor Rating Share",
        "DIVIDE(CALCULATE(COUNTROWS(FactServiceRating), FactServiceRating[Rating] >= 1, FactServiceRating[Rating] <= 2), [Rated Count], 0)",
        "0.0%", f3)
    add("Not Rated Share", "DIVIDE(CALCULATE(COUNTROWS(FactServiceRating), FactServiceRating[Rating] = 0), [Rating Count], 0)", "0.0%", f3)
    add("Rating Share",
        "DIVIDE(COUNTROWS(FactServiceRating), CALCULATE(COUNTROWS(FactServiceRating), REMOVEFILTERS(FactServiceRating[Rating]), "
        "REMOVEFILTERS(FactServiceRating[Rating Category])), 0)", "0%", f3,
        "Share of an attribute's responses that fall in the rating / category on the axis.")
    add("Avg Rating - Satisfied", 'CALCULATE([Average Service Rating], DimSatisfaction[Satisfaction] = "Satisfied")', "0.00", f3)
    add("Avg Rating - Neutral or Dissatisfied",
        'CALCULATE([Average Service Rating], DimSatisfaction[Satisfaction] = "Neutral or Dissatisfied")', "0.00", f3)
    add("Rating Gap (Satisfied - Not)", "[Avg Rating - Satisfied] - [Avg Rating - Neutral or Dissatisfied]", "+0.00;-0.00;0.00", f3)
    add("Lowest Rated Attribute",
        _top_bottom("VALUES(DimServiceAttribute[Service Attribute])", "DimServiceAttribute[Service Attribute]", "[Average Service Rating]", "min")
        + "RETURN who", None, f3)
    add("Lowest Attribute Rating",
        "MINX(ADDCOLUMNS(VALUES(DimServiceAttribute[Service Attribute]), \"@v\", [Average Service Rating]), [@v])", "0.00", f3)
    add("Highest Rated Attribute",
        _top_bottom("VALUES(DimServiceAttribute[Service Attribute])", "DimServiceAttribute[Service Attribute]", "[Average Service Rating]", "max")
        + "RETURN who", None, f3)
    add("Highest Attribute Rating",
        "MAXX(ADDCOLUMNS(VALUES(DimServiceAttribute[Service Attribute]), \"@v\", [Average Service Rating]), [@v])", "0.00", f3)

    f4 = "4 Model Performance"
    add("Model Accuracy", "AVERAGE(ModelComparison[Accuracy])", "0.0%", f4)
    add("Model Macro Precision", "AVERAGE(ModelComparison[Macro Precision])", "0.0%", f4)
    add("Model Macro Recall", "AVERAGE(ModelComparison[Macro Recall])", "0.0%", f4)
    add("Model Macro F1", "AVERAGE(ModelComparison[Macro F1])", "0.0%", f4)
    add("Model ROC-AUC", "AVERAGE(ModelComparison[ROC-AUC])", "0.000", f4)
    add("Selected Model Metric",
        'SWITCH(SELECTEDVALUE(MetricSelector[Metric], "Macro F1"),\n    "Accuracy", [Model Accuracy],\n'
        '    "Macro Precision", [Model Macro Precision],\n    "Macro Recall", [Model Macro Recall],\n'
        '    "Macro F1", [Model Macro F1],\n    "ROC-AUC", [Model ROC-AUC])', "0.0%", f4,
        "Driven by the MetricSelector slicer.")
    add("Best Macro F1", "MAXX(ALL(ModelComparison), ModelComparison[Macro F1])", "0.0%", f4)
    add("Best Model",
        "VAR b = MAXX(ALL(ModelComparison), ModelComparison[Macro F1])\n"
        "RETURN MINX(FILTER(ALL(ModelComparison), ModelComparison[Macro F1] = b), ModelComparison[Model])", None, f4)
    add("Best Accuracy", "MAXX(ALL(ModelComparison), ModelComparison[Accuracy])", "0.0%", f4)
    add("Best Macro Recall", "MAXX(ALL(ModelComparison), ModelComparison[Macro Recall])", "0.0%", f4)
    add("Best ROC-AUC", "MAXX(ALL(ModelComparison), ModelComparison[ROC-AUC])", "0.000", f4)
    add("Fold Macro F1", "AVERAGE(CVScores[Macro F1])", "0.0000", f4)
    add("CV Mean Macro F1", "AVERAGE(CVScores[Macro F1])", "0.0000", f4)
    add("CV Std Dev", "AVERAGE(ModelComparison[CV Macro F1 Std])", "0.0000", f4, "Sample std-dev (ddof=1) of the 5 fold Macro F1 scores, from Nandika's evaluation.")
    add("CV Lower Band", "[CV Mean Macro F1] - [CV Std Dev]", "0.0000", f4)
    add("CV Upper Band", "[CV Mean Macro F1] + [CV Std Dev]", "0.0000", f4)
    add("CV Min Macro F1", "MIN(CVScores[Macro F1])", "0.0000", f4)
    add("CV Max Macro F1", "MAX(CVScores[Macro F1])", "0.0000", f4)
    add("Best Model CV Std",
        "VAR bm = [Best Model]\nRETURN CALCULATE(AVERAGE(ModelComparison[CV Macro F1 Std]), ModelComparison[Model] = bm, REMOVEFILTERS(DimModel))",
        "0.0000", f4)
    add("Best Model CV Mean",
        "VAR bm = [Best Model]\nRETURN CALCULATE(AVERAGE(ModelComparison[CV Macro F1 Mean]), ModelComparison[Model] = bm, REMOVEFILTERS(DimModel))",
        "0.0000", f4)

    f5 = "5 Subgroup Analysis"
    add("Subgroup Passengers", "MAX(SubgroupPerformance[Passengers])", "#,0", f5)
    add("Subgroup Recall", "DIVIDE(SUM(SubgroupPerformance[TP]), SUM(SubgroupPerformance[TP]) + SUM(SubgroupPerformance[FN]), 0)", "0.0%", f5,
        "Recall of the Satisfied class.")
    add("Subgroup Precision", "DIVIDE(SUM(SubgroupPerformance[TP]), SUM(SubgroupPerformance[TP]) + SUM(SubgroupPerformance[FP]), 0)", "0.0%", f5)
    add("Subgroup FPR", "DIVIDE(SUM(SubgroupPerformance[FP]), SUM(SubgroupPerformance[FP]) + SUM(SubgroupPerformance[TN]), 0)", "0.0%", f5)
    add("Subgroup Accuracy",
        "DIVIDE(SUM(SubgroupPerformance[TP]) + SUM(SubgroupPerformance[TN]), SUM(SubgroupPerformance[TP]) + SUM(SubgroupPerformance[TN]) + "
        "SUM(SubgroupPerformance[FP]) + SUM(SubgroupPerformance[FN]), 0)", "0.0%", f5)
    add("Subgroup Macro F1", "AVERAGE(SubgroupPerformance[Macro F1])", "0.0%", f5)
    add("Recall Gap (pts)",
        "VAR t = ADDCOLUMNS(VALUES(SubgroupPerformance[Group Label]), \"@v\", [Subgroup Recall])\n"
        "RETURN (MAXX(t, [@v]) - MINX(t, [@v])) * 100", "0.0", f5, "Max minus min recall across the groups in context.")
    add("FPR Gap (pts)",
        "VAR t = ADDCOLUMNS(VALUES(SubgroupPerformance[Group Label]), \"@v\", [Subgroup FPR])\n"
        "RETURN (MAXX(t, [@v]) - MINX(t, [@v])) * 100", "0.0", f5)
    add("Lowest Recall Group",
        _top_bottom("VALUES(SubgroupPerformance[Group Label])", "SubgroupPerformance[Group Label]", "[Subgroup Recall]", "min") + "RETURN who",
        None, f5)
    add("Lowest Group Recall",
        "MINX(ADDCOLUMNS(VALUES(SubgroupPerformance[Group Label]), \"@v\", [Subgroup Recall]), [@v])", "0.0%", f5)
    add("Disparity Flag", 'IF([Recall Gap (pts)] > 10, "Material recall gap (>10 pts) - investigate", "Recall gap within 10 pts")', None, f5)

    for k in ("TN", "FP", "FN", "TP"):
        add(f"Confusion {k}", f'CALCULATE(SUM(SubgroupPerformance[{k}]), SubgroupPerformance[Attribute] = "Gender")', "#,0", f5,
            "Test-set confusion-matrix count (each passenger appears once under Gender).")
    f6 = "6 SHAP & Correlation"
    add("Mean Abs SHAP", "SUM(ShapImportance[Mean Absolute SHAP])", "0.000", f6)
    add("Top 5 SHAP", "IF(MAX(ShapImportance[Rank]) <= 5, [Mean Abs SHAP])", "0.000", f6, "Blank for features ranked below 5 so charts show only the top five.")
    add("Top 10 SHAP", "IF(MAX(ShapImportance[Rank]) <= 10, [Mean Abs SHAP])", "0.000", f6)
    add("Signed SHAP Top 10", "IF(MAX(ShapImportance[Rank]) <= 10, AVERAGE(ShapImportance[Mean SHAP]))", "+0.000;-0.000;0.000", f6,
        "Direction of influence: positive pushes toward Satisfied.")
    add("Tooltip Feature", 'SELECTEDVALUE(ShapImportance[Feature], "All features")', None, f6)
    add("Feature Rank", "MAX(ShapImportance[Rank])", "0", f6)
    add("SHAP Share", "DIVIDE([Mean Abs SHAP], CALCULATE([Mean Abs SHAP], REMOVEFILTERS(ShapImportance)), 0)", "0.0%", f6)
    add("Top Feature (SHAP)", "MINX(FILTER(ALL(ShapImportance), ShapImportance[Rank] = 1), ShapImportance[Feature])", None, f6)
    add("Top 5 Share of SHAP",
        "DIVIDE(CALCULATE([Mean Abs SHAP], FILTER(ALL(ShapImportance), ShapImportance[Rank] <= 5)), "
        "CALCULATE([Mean Abs SHAP], REMOVEFILTERS(ShapImportance)), 0)", "0.0%", f6)
    add("Top 3 SHAP Features",
        'CONCATENATEX(TOPN(3, ALL(ShapImportance), ShapImportance[Rank], ASC), ShapImportance[Feature], ", ", ShapImportance[Rank], ASC)', None, f6)
    add("Effect Value", "AVERAGE(CorrelationRanking[Effect Value])", "0.000", f6)
    add("Absolute Effect", "AVERAGE(CorrelationRanking[Absolute Effect])", "0.000", f6)
    add("Strongest Associated Feature",
        _top_bottom("VALUES(CorrelationRanking[Feature])", "CorrelationRanking[Feature]", "[Absolute Effect]", "max") + "RETURN who", None, f6)
    add("Strongest Association Value",
        "MAXX(ADDCOLUMNS(VALUES(CorrelationRanking[Feature]), \"@v\", [Absolute Effect]), [@v])", "0.000", f6)
    add("Significant Features",
        "CALCULATE(DISTINCTCOUNT(CorrelationRanking[Feature]), CorrelationRanking[Adjusted P-value] < 0.05)", "0", f6)
    add("Feature Correlation (tooltip)",
        "CALCULATE(AVERAGE(CorrelationRanking[Effect Value]), TREATAS(VALUES(ShapImportance[Feature]), CorrelationRanking[Feature]))", "0.000", f6)
    add("Feature Corr Method (tooltip)",
        "CALCULATE(MAX(CorrelationRanking[Method]), TREATAS(VALUES(ShapImportance[Feature]), CorrelationRanking[Feature]))", None, f6)
    add("Feature Avg Rating (tooltip)",
        "CALCULATE([Average Service Rating], TREATAS(VALUES(ShapImportance[Feature]), DimServiceAttribute[Service Attribute]))", "0.00", f6)
    add("Feature Gemini Note (tooltip)",
        'VAR f = SELECTEDVALUE(ShapImportance[Feature])\n'
        'VAR note = CALCULATE(MAX(GeminiRecommendations[Recommendation]), FILTER(ALL(GeminiRecommendations), GeminiRecommendations[Evidence Feature] = f))\n'
        'RETURN IF(ISBLANK(note), "No Gemini recommendation was generated for this feature in the explained passengers.", note)', None, f6)

    f7 = "7 Passenger Explanation"
    add("Selected Passenger Index", "SELECTEDVALUE(GeminiInsights[Passenger Index], MINX(ALL(GeminiInsights), GeminiInsights[Passenger Index]))", "0", f7,
        "The passenger picked in the slicer; the first explained passenger when none is picked.")
    def pick(col):
        return f"VAR idx = [Selected Passenger Index]\nRETURN CALCULATE(MAX(GeminiInsights[{col}]), GeminiInsights[Passenger Index] = idx, REMOVEFILTERS(GeminiInsights[Predicted Class]), REMOVEFILTERS(GeminiInsights[Passenger Label]))"
    add("Selected Passenger", pick("Passenger Label"), None, f7)
    add("Selected Predicted Class", pick("Predicted Class"), None, f7)
    add("Selected Actual Class", pick("Actual Class"), None, f7)
    add("Selected P(Satisfied)", pick("Probability Satisfied"), "0.0%", f7)
    add("Selected Prediction Confidence", pick("Predicted Probability"), "0.0%", f7)
    add("Selected Prediction Correct", pick("Correct Prediction"), None, f7)
    add("Gemini Explanation", pick("Explanation"), None, f7)
    add("Gemini Uncertainty Note", pick("Uncertainty Note"), None, f7)
    add("SHAP toward Satisfied", "VAR idx = [Selected Passenger Index]\nVAR v = CALCULATE(SUM(ShapLocal[SHAP Value]), ShapLocal[Passenger Index] = idx)\nRETURN IF(MAX(ShapLocal[Contribution Rank]) <= 10 && v > 0, v)", "+0.000;-0.000;0.000", f7,
        "Top-10 contributions only; positive values push the prediction toward Satisfied.")
    add("SHAP toward Neutral or Dissatisfied", "VAR idx = [Selected Passenger Index]\nVAR v = CALCULATE(SUM(ShapLocal[SHAP Value]), ShapLocal[Passenger Index] = idx)\nRETURN IF(MAX(ShapLocal[Contribution Rank]) <= 10 && v < 0, v)", "+0.000;-0.000;0.000", f7,
        "Top-10 contributions only; negative values push the prediction toward Neutral or Dissatisfied.")
    add("Net SHAP Value", "VAR idx = [Selected Passenger Index]\nRETURN CALCULATE(SUM(ShapLocal[SHAP Value]), ShapLocal[Passenger Index] = idx)", "+0.000;-0.000;0.000", f7)
    add("Top Contributor (Selected Passenger)",
        "VAR idx = [Selected Passenger Index]\nRETURN CALCULATE(MAX(ShapLocal[Feature]), ShapLocal[Passenger Index] = idx, ShapLocal[Contribution Rank] = 1)", None, f7)

    f8 = "8 Narrative (data-driven text)"
    add("Insight - Headline",
        'FORMAT([Satisfaction Rate], "0.0%") & " of the " & FORMAT([Total Passengers], "#,0") & " passengers in view are satisfied; "\n'
        '    & FORMAT([High Tier Rate], "0.0%") & " reach the High satisfaction tier and " & FORMAT([Low Tier Rate], "0.0%") & " fall in the Low tier."',
        None, f8)
    add("Insight - Class Gap",
        'VAR t = ADDCOLUMNS(VALUES(DimTravel[Class]), "@v", [Satisfaction Rate])\n'
        'VAR hi = MAXX(t, [@v])\nVAR lo = MINX(t, [@v])\n'
        'VAR topName = MINX(FILTER(t, [@v] = hi), DimTravel[Class])\n'
        'VAR botName = MINX(FILTER(t, [@v] = lo), DimTravel[Class])\n'
        'RETURN topName & " passengers are most satisfied (" & FORMAT(hi, "0%") & ") versus " & botName & " (" & FORMAT(lo, "0%") & ") - a " '
        '& FORMAT((hi - lo) * 100, "0") & "-point gap by travel class."', None, f8)
    add("Insight - Delay",
        '"Passengers arriving >15 min late are " & FORMAT([Satisfaction Rate - Delayed], "0%") & " satisfied vs " & FORMAT([Satisfaction Rate - On Time], "0%") '
        '& " when on time (" & FORMAT([Delay Satisfaction Penalty (pts)], "+0.0;-0.0") & " pts); " & FORMAT([Delayed Share], "0%") & " of passengers are delayed."',
        None, f8)
    add("Insight - Service Gap",
        '"Lowest-rated service: " & [Lowest Rated Attribute] & " (" & FORMAT([Lowest Attribute Rating], "0.00") & " / 5); best: " & [Highest Rated Attribute] '
        '& " (" & FORMAT([Highest Attribute Rating], "0.00") & " / 5)."', None, f8)
    add("Insight - Best Model",
        '[Best Model] & " leads on held-out Macro F1 (" & FORMAT([Best Macro F1], "0.0%") & ") with ROC-AUC " & FORMAT([Best ROC-AUC], "0.000") '
        '& " and accuracy " & FORMAT([Best Accuracy], "0.0%") & "."', None, f8)
    add("Insight - Stability",
        '"5-fold CV Macro F1 for " & [Best Model] & " = " & FORMAT([Best Model CV Mean], "0.0000") & " +/- " & FORMAT([Best Model CV Std], "0.0000") '
        '& " (std-dev across folds) - " & IF([Best Model CV Std] < 0.005, "performance is stable across folds.", "fold-to-fold variation is notable; review before deployment.")',
        None, f8)
    add("Insight - Fairness",
        'VAR bm = [Best Model]\n'
        'VAR t = ADDCOLUMNS(ALL(SubgroupPerformance[Group Label]), "@v", CALCULATE([Subgroup Recall], SubgroupPerformance[Model] = bm))\n'
        'VAR lo = MINX(t, [@v])\nVAR hi = MAXX(t, [@v])\n'
        'VAR lowGroup = MINX(FILTER(t, [@v] = lo), SubgroupPerformance[Group Label])\n'
        'RETURN "For " & bm & ", recall for the Satisfied class ranges from " & FORMAT(lo, "0.0%") & " (" & lowGroup & ") to " & FORMAT(hi, "0.0%") '
        '& ". This is a performance disparity to investigate (group size, class balance, threshold), not proof of discrimination."', None, f8)
    add("Insight - Explainability",
        '"Top global SHAP drivers: " & [Top 3 SHAP Features] & ". The top five features carry " & FORMAT([Top 5 Share of SHAP], "0%") & " of total mean |SHAP|."',
        None, f8)
    add("Insight - Action",
        '"Prioritise " & [Lowest Rated Attribute] & " (lowest rating) and " & [Top Feature (SHAP)] & " (largest model driver); recognise teams behind " & [Highest Rated Attribute] & "."',
        None, f8)
    add("Insight - Travel-type gap",
        'VAR t = ADDCOLUMNS(VALUES(DimTravel[Type of Travel]), "@v", [Satisfaction Rate])\n'
        'VAR hi = MAXX(t, [@v])\nVAR lo = MINX(t, [@v])\n'
        'VAR topName = MINX(FILTER(t, [@v] = hi), DimTravel[Type of Travel])\n'
        'VAR botName = MINX(FILTER(t, [@v] = lo), DimTravel[Type of Travel])\n'
        'RETURN IF(COUNTROWS(t) < 2, "Select more than one travel type to compare.", topName & " " & "travel types are " & FORMAT(hi, "0.0%") & " satisfied vs " & botName & " " & FORMAT(lo, "0.0%") & " (" & FORMAT((hi - lo) * 100, "0.0") & "-pt gap).")', None, f8)
    add("Insight - Customer-type gap",
        'VAR t = ADDCOLUMNS(VALUES(DimPassengerProfile[Customer Type]), "@v", [Satisfaction Rate])\n'
        'VAR hi = MAXX(t, [@v])\nVAR lo = MINX(t, [@v])\n'
        'VAR topName = MINX(FILTER(t, [@v] = hi), DimPassengerProfile[Customer Type])\n'
        'VAR botName = MINX(FILTER(t, [@v] = lo), DimPassengerProfile[Customer Type])\n'
        'RETURN IF(COUNTROWS(t) < 2, "Select more than one customer type to compare.", topName & " " & "customer types are " & FORMAT(hi, "0.0%") & " satisfied vs " & botName & " " & FORMAT(lo, "0.0%") & " (" & FORMAT((hi - lo) * 100, "0.0") & "-pt gap).")', None, f8)
    add("Insight - Gender gap",
        'VAR t = ADDCOLUMNS(VALUES(DimPassengerProfile[Gender]), "@v", [Satisfaction Rate])\n'
        'VAR hi = MAXX(t, [@v])\nVAR lo = MINX(t, [@v])\n'
        'VAR topName = MINX(FILTER(t, [@v] = hi), DimPassengerProfile[Gender])\n'
        'VAR botName = MINX(FILTER(t, [@v] = lo), DimPassengerProfile[Gender])\n'
        'RETURN IF(COUNTROWS(t) < 2, "Select more than one gender to compare.", topName & " " & "genders are " & FORMAT(hi, "0.0%") & " satisfied vs " & botName & " " & FORMAT(lo, "0.0%") & " (" & FORMAT((hi - lo) * 100, "0.0") & "-pt gap).")', None, f8)
    add("Insight - Fix first",
        '"Fix the weakest touch-points first: " & CONCATENATEX(TOPN(3, VALUES(DimServiceAttribute[Service Attribute]), [Average Service Rating], ASC), '
        'DimServiceAttribute[Service Attribute] & " (" & FORMAT([Average Service Rating], "0.00") & "/5)", ", ", [Average Service Rating], ASC) & "."', None, f8)
    add("Insight - Protect top driver",
        '"Protect " & [Top Feature (SHAP)] & " - the single largest model driver - and keep it consistent across airports; the strongest correlate in view is " & [Strongest Associated Feature] & " (" & FORMAT([Strongest Association Value], "0.00") & ")."', None, f8)
    add("Insight - Target segments",
        'VAR t = ADDCOLUMNS(VALUES(DimTravel[Class]), "@v", [Satisfaction Rate])\n'
        'VAR lo = MINX(t, [@v])\nVAR botName = MINX(FILTER(t, [@v] = lo), DimTravel[Class])\n'
        'RETURN "Target " & botName & " passengers (only " & FORMAT(lo, "0.0%") & " satisfied) with service recovery rather than blanket spend."', None, f8)
    add("Insight - Manage delays",
        '"Delayed arrivals (>15 min) are " & FORMAT([Delayed Share], "0%") & " of passengers and only " & FORMAT([Satisfaction Rate - Delayed], "0.0%") & " are satisfied vs " & FORMAT([Satisfaction Rate - On Time], "0.0%") & " on time - invest in delay communication and recovery."', None, f8)
    add("Insight - Recognise strengths",
        '"Recognise the teams behind " & [Highest Rated Attribute] & " (" & FORMAT([Highest Attribute Rating], "0.00") & "/5): they out-score the rest of the journey."', None, f8)
    add("Insight Text",
        'SWITCH(SELECTEDVALUE(Insights[Order]),\n    1, [Insight - Headline],\n    2, [Insight - Class Gap],\n    3, [Insight - Delay],\n'
        '    4, [Insight - Service Gap],\n    5, [Insight - Best Model],\n    6, [Insight - Stability],\n    7, [Insight - Fairness],\n'
        '    8, [Insight - Explainability],\n    9, [Insight - Action],\n    10, [Insight - Fix first],\n    11, [Insight - Protect top driver],\n    12, [Insight - Target segments],\n    13, [Insight - Manage delays],\n    14, [Insight - Recognise strengths],\n    15, [Insight - Travel-type gap],\n    16, [Insight - Customer-type gap],\n    17, [Insight - Gender gap])', None, f8, "Rendered by a table visual of Insights[Topic] x [Insight Text].")
    add("Title - Class Chart", '"Satisfaction by Travel Class  |  " & FORMAT([Total Passengers], "#,0") & " passengers in view"', None, f8)
    add("Title - Delay Chart", '"Satisfaction by Arrival Delay  |  on-time " & FORMAT([Satisfaction Rate - On Time], "0%") & " vs delayed " & FORMAT([Satisfaction Rate - Delayed], "0%")', None, f8)
    add("Title - Individual", '"Individual Passenger \u2014 SHAP Feature Contributions  |  " & [Selected Passenger]', None, f8)
    add("Title - Gemini", '"Gemini AI Explanation  |  " & [Selected Passenger]', None, f8)
    add("Title - Model Chart", '"Model comparison  |  best: " & [Best Model]', None, f8)
    return M


def relationships_tmdl():
    R = []

    def rel(many_t, many_c, one_t, one_c):
        R.append(relationship(f"rel_{many_t}_{many_c}_{one_t}".replace(" ", "_"),
                              f"{q(many_t)}.{q(many_c)}", f"{q(one_t)}.{q(one_c)}"))

    for fact in ("FactPassenger", "FactServiceRating"):
        rel(fact, "TravelKey", "DimTravel", "TravelKey")
        rel(fact, "ProfileKey", "DimPassengerProfile", "ProfileKey")
        rel(fact, "SatisfactionKey", "DimSatisfaction", "SatisfactionKey")
    rel("FactServiceRating", "Service Attribute", "DimServiceAttribute", "Service Attribute")
    for t in ("ModelComparison", "CVScores", "SubgroupPerformance"):
        rel(t, "Model", "DimModel", "Model")
    rel("ShapLocal", "Passenger Index", "GeminiInsights", "Passenger Index")
    rel("GeminiRecommendations", "Passenger Index", "GeminiInsights", "Passenger Index")
    # AI_Explainability.pbix tables: her original relationship + the link that lets her passenger slicer drive her cards/bars
    rel("shap_local_explanations", "feature", "shap_importance", "Feature")
    rel("shap_local_explanations", "row_index", "PassengerSelectorTable", "row_index")
    return "\n".join(R)


ALL_TABLE_NAMES = ["DimTravel", "DimPassengerProfile", "DimSatisfaction", "FactPassenger", "FactServiceRating",
                   "DimServiceAttribute", "DimModel", "ModelComparison", "CVScores", "SubgroupPerformance",
                   "MetricSelector", "ShapImportance", "ShapLocal", "GeminiInsights", "GeminiRecommendations",
                   "CorrelationRanking", "Insights", "shap_importance", "shap_local_explanations", "gemini_insights", "PassengerSelectorTable", "_Measures"]
