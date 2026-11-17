"""Report page layouts (1600 x 900 canvas)."""
import pandas as pd
from pbir import *  # noqa

MEAS = "_Measures"
PAGES_ORDER = ["overview", "eda", "service", "drivers", "model", "subgroup", "explain", "conclusion"]
TITLES = {"overview": "OVERVIEW", "eda": "EDA & PASSENGER ANALYSIS", "service": "SERVICE QUALITY",
          "drivers": "KEY DRIVERS", "model": "MODEL PERFORMANCE", "subgroup": "SUBGROUP PERFORMANCE",
          "explain": "AI EXPLAINABILITY", "conclusion": "CONCLUSION"}
QUESTIONS = {
    "overview": "What does our dataset tell us about airline passenger satisfaction?",
    "eda": "How do passenger profile, travel class, delay and service quality relate to satisfaction?",
    "service": "Which on-board and ground services delight - or disappoint - passengers?",
    "drivers": "Which factors are statistically associated with satisfaction, and does the model agree?",
    "model": "Which predictive model performs best, and how stable is its performance?",
    "subgroup": "Does the model perform equally well for every passenger group?",
    "explain": "Why does the selected model predict satisfaction or dissatisfaction?",
    "conclusion": "So what? The story in one page - and what the airline should do next.",
}
FOOT = ("Source: Kaggle Airline Passenger Satisfaction (cleaned, n = 129,487) | Models: Logistic Regression, Random Forest, XGBoost | "
        "Explainability: SHAP + Gemini | Team 11 - VDUI Mini Project")


def facts(root):
    df = pd.read_csv(f"{root}/airline_satisfaction_tiered.csv")
    f = {}
    df["sat"] = (df["Satisfaction"] == "Satisfied").astype(int)
    f["n"] = len(df)
    f["sat_rate"] = df.sat.mean()
    f["by_class"] = df.groupby("Class").sat.mean().to_dict()
    f["by_travel"] = df.groupby("Type of Travel").sat.mean().to_dict()
    f["by_cust"] = df.groupby("Customer Type").sat.mean().to_dict()
    f["by_gender"] = df.groupby("Gender").sat.mean().to_dict()
    late = df["Arrival Delay"] > 15
    f["late_share"] = late.mean()
    f["sat_late"] = df[late].sat.mean()
    f["sat_ontime"] = df[~late].sat.mean()
    ratings = ["Departure and Arrival Time Convenience", "Ease of Online Booking", "Check-in Service", "Online Boarding", "Gate Location",
               "On-board Service", "Seat Comfort", "Leg Room Service", "Cleanliness", "Food and Drink", "In-flight Service",
               "In-flight Wifi Service", "In-flight Entertainment", "Baggage Handling"]
    avg = {c: df.loc[df[c] > 0, c].mean() for c in ratings}
    f["avg_rating"] = dict(sorted(avg.items(), key=lambda kv: kv[1]))
    f["zero_share"] = {c: (df[c] == 0).mean() for c in ratings}
    f["ret_share"] = (df["Customer Type"] == "Returning").mean()
    f["business_share"] = (df["Type of Travel"] == "Business").mean()
    return f


def pct(x, d=0):
    return f"{x*100:.{d}f}%"


# ------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, pages, bookmarks):
        self.pages = pages        # key -> Page
        self.bm = bookmarks       # name -> bookmark id


def chrome(p, ctx, key, with_passenger_slicers=False, extra_slicers=None):
    """Dark header + navigator + title strip + footer (+ filter strip)."""
    nav_x = 440
    p.begin_group("Header", 0, 0, 1600, 68)
    p.textbox(0, 0, 1600, 64, [[(" ", 4, False, WHITE)]], bg=HEADER_DARK, label="header bg")
    p.textbox(0, 64, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="header accent")
    p.textbox(20, 6, 420, 54, [[("✈  BEYOND THE BOARDING PASS", 14, True, WHITE)],
                               [("Airline Passenger Satisfaction  |  Team 11", 9, False, "#9CC3F0")]], label="app title")
    p.page_navigator(nav_x, 12, 1590 - nav_x, 40)
    p.end_group()

    # title strip
    p.textbox(20, 76, 740 if (with_passenger_slicers or extra_slicers) else 1560, 52,
              [[(TITLES[key], 15, True, NAVY)], [(QUESTIONS[key], 9.5, False, MUTED, True)]], label="page title")
    if with_passenger_slicers:
        p.begin_group("Filters", 770, 72, 810, 56)
        specs = [(c("DimPassengerProfile", "Gender"), "Gender"), (c("DimTravel", "Class"), "Class"),
                 (c("DimPassengerProfile", "Customer Type"), "CustomerType"), (c("DimTravel", "Type of Travel"), "TypeOfTravel")]
        names = ["Gender", "Travel Class", "Customer Type", "Type of Travel"]
        for i, ((ref, sync), nm) in enumerate(zip(specs, names)):
            p.slicer(770 + i * 205, 72, 195, 56, ref, sync=sync, title=nm, label=f"slicer {nm}")
        p.end_group()
    if extra_slicers:
        p.begin_group("Filters", 770, 72, 810, 56)
        n = len(extra_slicers)
        w = int(800 / n) - 10
        for i, (ref, nm, kw) in enumerate(extra_slicers):
            p.slicer(780 + i * (w + 10), 72, w, 56, ref, title=nm, label=f"slicer {nm}", **kw)
        p.end_group()
    # footer
    p.textbox(20, 872, 1560, 22, [[(FOOT, 8, False, MUTED)]], label="footer")


def kpi_row(p, specs, y=134, h=96, color_cycle=(NAVY, BLUE, TEAL, AMBER, NAVY)):
    n = len(specs)
    gap = 10
    w = (1560 - gap * (n - 1)) / n
    p.begin_group("KPI strip", 20, y, 1560, h)
    for i, (meas, label, *rest) in enumerate(specs):
        size = rest[0] if rest else 26
        p.card(20 + i * (w + gap), y, w, h, meas, label, color=color_cycle[i % len(color_cycle)] if i % 2 == 0 else NAVY,
               size=size, accent=color_cycle[i % len(color_cycle)])
    p.end_group()


def insights_filter(topics):
    return [{"name": hid("insfilter", *topics), "field": Col("Insights", "Topic"), "type": "Categorical",
             "filter": {"Version": 2, "From": [{"Name": "s", "Entity": "Insights", "Type": 0}],
                        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": "Topic"}}],
                                                        "Values": [[{"Literal": {"Value": "'" + t + "'"}}] for t in topics]}}}]}}]


def insight_table(p, x, y, w, h, title, topics, size=11):
    return p.table(x, y, w, h, title, [c("Insights", "Topic"), m("Insight Text")], filters=insights_filter(topics), size=size,
                   sort=(c("Insights", "Order"), "Ascending"), label=f"insights {title}",
                   objects_extra={"columnHeaders": [{"properties": {"fontColor": colr(WHITE), "backColor": colr(NAVY), "fontSize": num(size),
                                                                    "bold": lit(True)}}]})


def sat_stack(p, x, y, w, h, title, cat, kind="hundredPercentStackedColumnChart", tooltip_page=None, title_measure=None,
              legend="Top", series=None, colors=None, label=None):
    series = series or c("DimSatisfaction", "Satisfaction")
    colors = colors or SAT_COLORS
    o = chart_objects(legend=legend, labels=True, label_color=WHITE, val_axis=False, gridlines=False,
                      datapoints=dp_colors(series[1], series[2], colors))
    return p.chart(kind, x, y, w, h, title, category=cat, series=series, values=[m("Satisfaction Mix %")], objects=o,
                   tooltip_page=tooltip_page, title_measure=title_measure, label=label or f"mix {title}")


# ================================================================================================
def build_pages(root, ctx_pages, F, bm):
    P = {}
    ctx = Ctx(ctx_pages, bm)

    def new(key, **kw):
        p = Page(key, TITLES.get(key, key), **kw)
        P[key] = p
        return p

    pid = lambda k: ctx_pages[k].id if k in ctx_pages else None  # noqa

    # ============================= 1 OVERVIEW =============================
    p = new("overview")
    chrome(p, ctx, "overview", with_passenger_slicers=True)
    kpi_row(p, [("Total Passengers", "TOTAL PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"),
                ("High Tier Rate", "HIGH-TIER RATE"), ("Average Service Rating", "AVG SERVICE RATING (1-5)"),
                ("Best Macro F1", "BEST MODEL MACRO F1")])
    p.donut(20, 242, 300, 300, "Passenger Satisfaction", c("DimSatisfaction", "Satisfaction"), m("Total Passengers"), SAT_COLORS)
    p.donut(330, 242, 300, 300, "Satisfaction Tier Mix", c("DimSatisfaction", "Satisfaction Tier"), m("Total Passengers"), TIER_COLORS)
    sat_stack(p, 640, 242, 480, 300, "", c("DimTravel", "Class"), tooltip_page=None, title_measure="Title - Class Chart", label="class mix")
    p.chart("clusteredBarChart", 1130, 242, 450, 300, "Top 5 Satisfaction Drivers (SHAP)", category=c("ShapImportance", "Feature"),
            values=[m("Top 5 SHAP")], sort=(m("Top 5 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd",
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]),
            tooltip_page=ctx_pages["tooltip"].id, label="top5 shap overview")
    insight_table(p, 20, 554, 760, 312, "KEY FINDINGS  |  recalculated with every filter",
                  ["Headline", "Who is happiest?", "Delay effect", "Service gap"], size=11)
    p.matrix(790, 554, 480, 312, "Model Performance Summary (held-out test)", [c("DimModel", "Model")], [],
             [m("Model Accuracy"), m("Model Macro F1"), m("Model ROC-AUC"), m("CV Mean Macro F1")], size=10,
             label="model summary matrix")
    # story panel
    p.begin_group("Story chapters", 1280, 554, 300, 312)
    p.textbox(1280, 554, 300, 312, [[(" ", 4, False, WHITE)]], bg=WHITE, border=BORDER, radius=10, shadow=True, label="story panel bg")
    p.textbox(1292, 560, 276, 30, [[("FOLLOW THE STORY", 11, True, NAVY)]], label="story title")
    chapters = [("1  HOOK  -  the passenger picture", "bm_hook", NAVY), ("2  BUILD-UP  -  what shapes satisfaction", "bm_build", BLUE),
                ("3  INSIGHT  -  why the model decides", "bm_insight", TEAL), ("4  CONCLUSION  -  what we do next", "bm_conclusion", AMBER)]
    for i, (t, bm, colr_) in enumerate(chapters):
        p.button(1292, 596 + i * 66, 276, 56, t, link_bookmark(ctx.bm[bm]) if ctx.bm else None, fill=colr_, hover=NAVY, size=10, align="Left",
                 label=f"story {bm}")
    p.end_group()

    # ============================= 2 EDA =============================
    p = new("eda")
    chrome(p, ctx, "eda", with_passenger_slicers=True)
    kpi_row(p, [("Total Passengers", "PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"), ("Avg Departure Delay", "AVG DEPARTURE DELAY (MIN)"),
                ("Avg Arrival Delay", "AVG ARRIVAL DELAY (MIN)"), ("Avg Flight Distance", "AVG FLIGHT DISTANCE (MI)")])
    sat_stack(p, 20, 242, 380, 300, "Satisfaction by Travel Class", c("DimTravel", "Class"), label="eda class")
    sat_stack(p, 410, 242, 400, 300, "", c("FactPassenger", "Delay Bucket"), title_measure="Title - Delay Chart", label="eda delay")
    sat_stack(p, 820, 242, 380, 300, "Satisfaction by Age Band", c("DimPassengerProfile", "Age Band"), label="eda age")
    sat_stack(p, 1210, 242, 370, 300, "Satisfaction by Distance Band", c("FactPassenger", "Distance Band"), label="eda dist")
    p.chart("clusteredBarChart", 20, 554, 560, 312, "Average Rating by Service Attribute (1-5, zeros excluded)",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Average Service Rating")],
            sort=(m("Average Service Rating"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]), label="eda avg rating")
    sat_stack(p, 590, 554, 330, 312, "Returning Passenger Profile", c("DimPassengerProfile", "Customer Type"), kind="hundredPercentStackedBarChart",
              label="eda customer")
    sat_stack(p, 930, 554, 320, 312, "Reason for Travelling", c("DimTravel", "Type of Travel"), kind="hundredPercentStackedBarChart", label="eda travel")
    insight_table(p, 1260, 554, 320, 312, "LIVE OBSERVATIONS", ["Who is happiest?", "Travel-type gap", "Customer-type gap", "Gender gap", "Delay effect"], size=9)

    # ============================= 3 SERVICE QUALITY =============================
    p = new("service")
    chrome(p, ctx, "service", with_passenger_slicers=True)
    kpi_row(p, [("Average Service Rating", "AVG SERVICE RATING (1-5)"), ("Good Rating Share", "GOOD RATINGS (4-5)"),
                ("Poor Rating Share", "POOR RATINGS (1-2)"), ("Lowest Rated Attribute", "LOWEST-RATED SERVICE", 15),
                ("Highest Rated Attribute", "HIGHEST-RATED SERVICE", 15)])
    cat = c("FactServiceRating", "Rating Category")
    p.chart("hundredPercentStackedBarChart", 20, 242, 780, 624, "Satisfaction Survey: how passengers rated each service",
            category=c("DimServiceAttribute", "Service Attribute"), series=cat, values=[m("Rating Share")],
            objects=chart_objects(legend="Top", labels=True, label_color=WHITE, val_axis=False, gridlines=False, cat_size=9,
                                  datapoints=dp_colors("FactServiceRating", "Rating Category", RATING_COLORS)),
            subtitle="Poor = 1-2, Average = 3, Good = 4-5, Not Rated = 0 (not applicable)", label="survey stacked")
    p.chart("clusteredColumnChart", 810, 242, 770, 300, "Average Rating by Service Group: satisfied vs neutral/dissatisfied",
            category=c("DimServiceAttribute", "Service Group"), values=[m("Avg Rating - Satisfied"), m("Avg Rating - Neutral or Dissatisfied")],
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd",
                                  datapoints=dp_measures({"Avg Rating - Satisfied": BLUE, "Avg Rating - Neutral or Dissatisfied": AMBER})),
            label="service group compare")
    p.chart("clusteredBarChart", 810, 554, 770, 312, "Rating Gap by Attribute (satisfied minus neutral/dissatisfied)",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Rating Gap (Satisfied - Not)")],
            sort=(m("Rating Gap (Satisfied - Not)"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]),
            subtitle="Bigger gap = service that separates happy from unhappy passengers", label="rating gap")

    # ============================= 4 KEY DRIVERS =============================
    p = new("drivers")
    chrome(p, ctx, "drivers", extra_slicers=[(c("CorrelationRanking", "Method"), "Association method", {})])
    kpi_row(p, [("Strongest Associated Feature", "STRONGEST ASSOCIATION", 16), ("Strongest Association Value", "EFFECT SIZE (MAX |r|)"),
                ("Significant Features", "SIGNIFICANT FEATURES (adj p<0.05)"), ("Top Feature (SHAP)", "TOP MODEL DRIVER (SHAP)", 16),
                ("Top 5 Share of SHAP", "TOP-5 SHARE OF |SHAP|")])
    p.chart("clusteredBarChart", 20, 242, 780, 624, "Association with Satisfaction (Spearman / Point-biserial / Cramer's V)",
            category=c("CorrelationRanking", "Feature"), series=c("CorrelationRanking", "Method"), values=[m("Effect Value")],
            sort=(m("Absolute Effect"), "Descending"),
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, cat_size=9, label_pos="OutsideEnd",
                                  datapoints=dp_colors("CorrelationRanking", "Method", {"Spearman": BLUE, "Point-Biserial": TEAL, "Cramer's V": AMBER})),
            subtitle="Methods have different interpretations - compare within a method, not across", label="corr bars")
    p.chart("clusteredBarChart", 810, 242, 770, 300, "Global Model Importance (mean |SHAP|, top 10)",
            category=c("ShapImportance", "Feature"), values=[m("Top 10 SHAP")], sort=(m("Top 10 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]),
            tooltip_page=ctx_pages["tooltip"].id, label="shap top10")
    p.table(810, 554, 480, 312, "Association table", [c("CorrelationRanking", "Feature"), c("CorrelationRanking", "Method"),
                                                       m("Effect Value"), c("CorrelationRanking", "Adjusted P-value")],
            sort=(m("Absolute Effect"), "Descending"), size=9, label="corr table")
    guide = [
        [("HOW TO READ THIS PAGE", 11, True, NAVY)],
        [("• Correlation shows how a feature moves with satisfaction on its own.", 9, False, TEXT)],
        [("• SHAP shows how much the trained model relies on a feature after accounting for the others.", 9, False, TEXT)],
        [("• Agreement (Online Boarding, Wi-Fi, Entertainment) = a robust driver. Disagreement = overlap between features or non-linear effects.", 9, False, TEXT)],
        [("• Association is not causation.", 9, False, TEXT, True)],
    ]
    p.textbox(1300, 554, 280, 312, guide, bg=WHITE, border=BORDER, radius=10, shadow=True, label="reading guide")

    # ============================= 5 MODEL PERFORMANCE =============================
    p = new("model")
    chrome(p, ctx, "model", extra_slicers=[(c("DimModel", "Model"), "Model", {}), (c("MetricSelector", "Metric"), "Metric explorer", {})])
    kpi_row(p, [("Best Model", "BEST PERFORMING MODEL", 20), ("Best Macro F1", "BEST MACRO F1"), ("Best Macro Recall", "BEST MACRO RECALL"),
                ("Best ROC-AUC", "BEST ROC-AUC"), ("Best Model CV Std", "CV STD-DEV (BEST MODEL)")])
    p.chart("clusteredBarChart", 20, 242, 520, 300, "", category=c("DimModel", "Model"),
            values=[m("Model Accuracy"), m("Model Macro F1"), m("Model Macro Recall")], title_measure="Title - Model Chart",
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd",
                                  datapoints=dp_measures({"Model Accuracy": TEAL, "Model Macro F1": NAVY, "Model Macro Recall": BLUE})),
            label="model compare")
    p.chart("clusteredColumnChart", 550, 242, 300, 300, "Metric explorer (use the slicer)", category=c("DimModel", "Model"),
            values=[m("Selected Model Metric")],
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd",
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS)), label="metric explorer")
    p.chart("lineChart", 860, 242, 350, 300, "Cross-Validation Stability (Macro F1 per fold)", category=c("CVScores", "Fold"),
            series=c("DimModel", "Model"), values=[m("Fold Macro F1")],
            objects=chart_objects(legend="Bottom", labels=False, val_axis=True, gridlines=True,
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv lines")
    p.matrix(1220, 242, 360, 300, "CV Mean +/- Std-Dev", [c("DimModel", "Model")], [],
             [m("CV Mean Macro F1"), m("CV Std Dev"), m("CV Min Macro F1"), m("CV Max Macro F1")], size=9, label="cv matrix")
    p.chart("lineChart", 20, 554, 540, 312, "CV error bands: mean Macro F1 with +/- 1 std-dev across folds", category=c("DimModel", "Model"),
            values=[m("CV Upper Band"), m("CV Mean Macro F1"), m("CV Lower Band")],
            objects=chart_objects(legend="Top", labels=True, val_axis=True, gridlines=True,
                                  datapoints=dp_measures({"CV Upper Band": TEAL, "CV Mean Macro F1": NAVY, "CV Lower Band": AMBER}),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv error bands")
    p.matrix(570, 554, 300, 312, "Confusion matrix counts (test set)", [c("DimModel", "Model")], [],
             [m("Confusion TN"), m("Confusion FP"), m("Confusion FN"), m("Confusion TP")], size=9, label="confusion matrix")
    insight_table(p, 880, 554, 700, 312, "MODEL EVALUATION CONCLUSION  |  calculated, not typed", ["Best model", "Stability", "Fairness check"], size=10)

    # ============================= 6 SUBGROUP PERFORMANCE =============================
    p = new("subgroup")
    chrome(p, ctx, "subgroup", extra_slicers=[(c("DimModel", "Model"), "Model", {}), (c("SubgroupPerformance", "Attribute"), "Passenger attribute", {})])
    kpi_row(p, [("Recall Gap (pts)", "RECALL GAP (MAX-MIN, PTS)", 26), ("Lowest Recall Group", "LOWEST-RECALL GROUP", 14),
                ("Lowest Group Recall", "LOWEST GROUP RECALL"), ("FPR Gap (pts)", "FALSE-POSITIVE-RATE GAP (PTS)"),
                ("Disparity Flag", "DISPARITY CHECK", 12)])
    grp = c("SubgroupPerformance", "Group Label")
    ser = c("DimModel", "Model")
    for i, (meas, ttl) in enumerate([("Subgroup Recall", "Recall by Passenger Group"), ("Subgroup FPR", "False-Positive Rate by Group"),
                                     ("Subgroup Macro F1", "Macro F1 by Group")]):
        p.chart("clusteredBarChart", 20 + i * 530, 242, 520 if i < 2 else 500, 330, ttl, category=grp, series=ser, values=[m(meas)],
                objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8, label_size=8,
                                      datapoints=dp_colors("DimModel", "Model", MODEL_COLORS)), label=f"sub {meas}")
    p.table(20, 584, 1000, 282, "Subgroup detail (held-out test set)",
            [grp, ser, m("Subgroup Passengers"), m("Subgroup Precision"), m("Subgroup Recall"), m("Subgroup FPR"), m("Subgroup Macro F1")],
            sort=(grp, "Ascending"), size=9, label="subgroup table")
    note = [
        [("HOW TO INTERPRET", 11, True, NAVY)],
        [("• Recall = share of truly satisfied passengers the model finds. A low value means the model under-predicts satisfaction for that group.", 9, False, TEXT)],
        [("• Differences may come from group size, class balance (e.g. Personal travellers are mostly dissatisfied), missing values or the decision threshold.", 9, False, TEXT)],
        [("• This is performance investigation - NOT proof of discrimination. Check group sample sizes before drawing conclusions.", 9, False, TEXT, True)],
    ]
    p.textbox(1030, 584, 550, 282, note, bg=WHITE, border=BORDER, radius=10, shadow=True, label="interpretation")

    # ============================= 7 AI EXPLAINABILITY =============================
    p = new("explain")
    chrome(p, ctx, "explain", extra_slicers=[(c("GeminiInsights", "Passenger Label"), "Explained passenger", {"single": True, "default": F["first_label"]})])
    kpi_row(p, [("Selected Predicted Class", "PREDICTED CLASS", 14), ("Selected P(Satisfied)", "P(SATISFIED)"),
                ("Selected Prediction Confidence", "MODEL CONFIDENCE"), ("Selected Prediction Correct", "PREDICTION CORRECT?", 18),
                ("Top Contributor (Selected Passenger)", "TOP CONTRIBUTOR", 14)])
    p.chart("clusteredBarChart", 20, 242, 400, 300, "Top 5 Factors Influencing Satisfaction Predictions", category=c("ShapImportance", "Feature"),
            values=[m("Top 5 SHAP")], sort=(m("Top 5 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]),
            tooltip_page=ctx_pages["tooltip"].id, subtitle="hover a bar for the SHAP tooltip", label="top5 shap explain")
    p.chart("clusteredBarChart", 430, 242, 370, 300, "Direction of influence (signed mean SHAP, top 10)", category=c("ShapImportance", "Feature"),
            values=[m("Signed SHAP Top 10")], sort=(m("Top 10 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, cat_size=8, label_size=8,
                                  datapoints=[{"properties": {"fill": colr(TEAL)}}]),
            subtitle="+ pushes toward Satisfied, - toward Neutral/Dissatisfied", tooltip_page=ctx_pages["tooltip"].id, label="signed shap")
    p.chart("stackedBarChart", 810, 242, 770, 300, "Why this prediction? Top-10 SHAP contributions for the selected passenger",
            category=c("ShapLocal", "Feature"), values=[m("SHAP toward Satisfied"), m("SHAP toward Neutral or Dissatisfied")],
            sort=(m("Net SHAP Value"), "Descending"),
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, cat_size=9,
                                  datapoints=dp_measures({"SHAP toward Satisfied": BLUE, "SHAP toward Neutral or Dissatisfied": AMBER})),
            subtitle="Blue pushes toward Satisfied, amber toward Neutral/Dissatisfied", label="local shap")
    p.table(20, 554, 700, 150, "GEMINI EXPLANATION (grounded in the SHAP values)", [m("Gemini Explanation")], size=10, label="gemini text")
    p.table(20, 712, 700, 154, "GEMINI SERVICE-IMPROVEMENT SUGGESTIONS",
            [c("GeminiRecommendations", "Evidence Feature"), c("GeminiRecommendations", "Recommendation"), c("GeminiRecommendations", "Reason")],
            size=9, label="gemini recs")
    p.table(730, 554, 380, 312, "Feature contributions (selected passenger)",
            [c("ShapLocal", "Feature"), c("ShapLocal", "Feature Value"), c("ShapLocal", "SHAP Value"), c("ShapLocal", "Direction")],
            sort=(c("ShapLocal", "Contribution Rank"), "Ascending"), size=9, label="shap detail table")
    insight_table(p, 1120, 554, 460, 160, "KEY EXPLAINABILITY FINDING", ["Explainability"], size=10)
    insight_table(p, 1120, 722, 460, 144, "SERVICE AREA TO INVESTIGATE", ["Where to act"], size=10)

    # ============================= 8 CONCLUSION =============================
    p = new("conclusion")
    chrome(p, ctx, "conclusion")
    kpi_row(p, [("Total Passengers", "PASSENGERS ANALYSED"), ("Satisfaction Rate", "SATISFACTION RATE"), ("Best Model", "BEST MODEL", 20),
                ("Best Macro F1", "BEST MACRO F1"), ("Recall Gap (pts)", "WIDEST SUBGROUP RECALL GAP (PTS)")])
    insight_table(p, 20, 242, 900, 420, "WHAT THE DATA SAYS  |  every sentence is a DAX measure",
                  ["Headline", "Who is happiest?", "Delay effect", "Service gap", "Best model", "Stability", "Fairness check", "Explainability", "Where to act"], size=11)
    insight_table(p, 930, 242, 650, 420, "RECOMMENDATIONS  |  computed from the data in view",
                  ["Fix first", "Protect the top driver", "Target segments", "Manage delays", "Recognise strengths"], size=10)
    lim = [
        [("LIMITATIONS & NEXT STEPS", 12, True, NAVY)],
        [("• No flight-date or route fields exist, so no time trend or map is shown.   • Zero ratings are treated as 'not applicable'.", 9.5, False, TEXT)],
        [("• Subgroup gaps are performance diagnostics; re-check with threshold tuning and class-balanced training.", 9.5, False, TEXT)],
        [("• Next: A/B test the Wi-Fi and online-boarding fixes; refresh the model each quarter; re-run SHAP after retraining.", 9.5, False, TEXT)],
    ]
    p.textbox(20, 674, 900, 192, lim, bg=WHITE, border=BORDER, radius=10, shadow=True, label="limitations")
    p.begin_group("Story controls", 930, 674, 650, 192)
    p.textbox(930, 674, 650, 192, [[(" ", 4, False, WHITE)]], bg=WHITE, border=BORDER, radius=10, shadow=True, label="story ctrl bg")
    p.textbox(942, 680, 620, 28, [[("CONTINUE EXPLORING", 11, True, NAVY)]], label="story ctrl title")
    p.button(942, 716, 300, 50, "↺  Restart the story (Hook)", link_bookmark(ctx.bm["bm_hook"]) if ctx.bm else None, fill=NAVY, hover=BLUE, size=10, label="restart")
    p.button(1252, 716, 316, 50, "Segment detail (drill-through page)", link_page(ctx_pages["segment"].id), fill=BLUE, hover=NAVY, size=10, label="to segment")
    p.button(942, 776, 300, 50, "Model performance", link_page(ctx_pages["model"].id), fill=TEAL, hover=NAVY, size=10, label="to model")
    p.button(1252, 776, 316, 50, "AI explainability", link_page(ctx_pages["explain"].id), fill=AMBER, hover=NAVY, size=10, label="to explain")
    p.end_group()

    # ============================= Drill-through: Passenger Segment Detail =============================
    p = ctx_pages["segment"]
    P["segment"] = p
    p.begin_group("Header", 0, 0, 1600, 68)
    p.textbox(0, 0, 1600, 64, [[(" ", 4, False, WHITE)]], bg=HEADER_DARK, label="header bg")
    p.textbox(0, 64, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="header accent")
    p.textbox(90, 6, 900, 54, [[("PASSENGER SEGMENT DETAIL", 14, True, WHITE)],
                               [("Drill-through page: right-click a Class / Satisfaction Tier in the report -> Drill through", 9, False, "#9CC3F0")]],
              label="segment title")
    p.button(20, 14, 56, 36, "←", link_back(), fill="#24508F", hover=BLUE, size=14, label="back button")
    p.end_group()
    p.textbox(20, 76, 1560, 52, [[("Segment profile", 15, True, NAVY)], [("Filtered by the drilled Class / Satisfaction Tier plus any slicer selections on the other pages.", 9.5, False, MUTED, True)]],
              label="page title")
    kpi_row(p, [("Total Passengers", "PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"), ("High Tier Rate", "HIGH-TIER RATE"),
                ("Average Service Rating", "AVG SERVICE RATING"), ("Avg Arrival Delay", "AVG ARRIVAL DELAY (MIN)")])
    p.table(20, 242, 900, 624, "Segment breakdown",
            [c("DimTravel", "Class"), c("DimTravel", "Type of Travel"), c("DimPassengerProfile", "Customer Type"), m("Total Passengers"),
             m("Satisfaction Rate"), m("High Tier Rate"), m("Avg Departure Delay"), m("Avg Arrival Delay"), m("Avg Flight Distance"),
             m("Average Service Rating")], sort=(m("Total Passengers"), "Descending"), size=9, label="segment table")
    p.chart("clusteredBarChart", 930, 242, 650, 624, "Average rating by service attribute (this segment)",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Average Service Rating")],
            sort=(m("Average Service Rating"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]), label="segment ratings")
    p.textbox(20, 872, 1560, 22, [[(FOOT, 8, False, MUTED)]], label="footer")

    # ============================= Tooltip: TT - SHAP Feature =============================
    p = ctx_pages["tooltip"]
    P["tooltip"] = p
    p.textbox(0, 0, 360, 330, [[(" ", 4, False, WHITE)]], bg=WHITE, border=BORDER, radius=8, label="tt bg")
    p.card(8, 8, 344, 64, "Tooltip Feature", "FEATURE", color=NAVY, size=16)
    p.card(8, 80, 112, 70, "Mean Abs SHAP", "MEAN |SHAP|", color=BLUE, size=16)
    p.card(124, 80, 112, 70, "Feature Rank", "SHAP RANK", color=TEAL, size=16)
    p.card(240, 80, 112, 70, "Feature Correlation (tooltip)", "CORRELATION", color=AMBER, size=16)
    p.card(8, 158, 170, 62, "Feature Corr Method (tooltip)", "METHOD", color=NAVY, size=12)
    p.card(182, 158, 170, 62, "Feature Avg Rating (tooltip)", "AVG SERVICE RATING", color=NAVY, size=16)
    p.table(8, 226, 344, 98, "Gemini note", [m("Feature Gemini Note (tooltip)")], size=9, label="tt gemini")
    return P
