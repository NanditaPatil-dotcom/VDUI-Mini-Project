"""Report page layouts (1600 x 900 canvas)."""
import pandas as pd
from pbir import *  # noqa

MEAS = "_Measures"
PAGES_ORDER = ["overview", "eda", "model", "explain", "conclusion"]
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
    """Big blue banner (title + navigator) and an optional filter strip. No page-name strip, no footer."""
    p.dy = 16
    p.begin_group("Header", 0, 0, 1600, 88)
    p.textbox(0, 0, 1600, 84, [[(" ", 4, False, WHITE)]], bg=NAVY, label="banner")
    p.textbox(0, 84, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="banner accent")
    p.textbox(20, 10, 330, 64, [[("\u2708  BEYOND THE BOARDING PASS", 16, True, WHITE)],
                                [("Airline Passenger Satisfaction  |  Team 11", 9, False, "#BBD4F5")]], label="app title")
    p.page_navigator(350, 22, 1240, 44)
    p.end_group()
    if with_passenger_slicers:
        p.begin_group("Filters", 20, 94, 1560, 50)
        specs = [(c("DimPassengerProfile", "Gender"), "Gender", "Gender"), (c("DimTravel", "Class"), "Class", "Travel Class"),
                 (c("DimPassengerProfile", "Customer Type"), "CustomerType", "Customer Type"),
                 (c("DimTravel", "Type of Travel"), "TypeOfTravel", "Type of Travel")]
        for i, (ref, sync, nm) in enumerate(specs):
            p.slicer(20 + i * 390, 94, 380, 50, ref, sync=sync, title=nm, label=f"slicer {nm}")
        p.end_group()
    if extra_slicers:
        p.begin_group("Filters", 20, 94, 1560, 50)
        n = len(extra_slicers)
        w = min(500, int((1560 - 10 * (n - 1)) / n))
        for i, (ref, nm, kw) in enumerate(extra_slicers):
            p.slicer(20 + i * (w + 10), 94, w, 50, ref, title=nm, label=f"slicer {nm}", **kw)
        p.end_group()


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

    # ============================= 2 EDA & PASSENGER ANALYSIS (incl. service quality) =============================
    p = new("eda")
    chrome(p, ctx, "eda", with_passenger_slicers=True)
    kpi_row(p, [("Total Passengers", "PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"), ("Avg Arrival Delay", "AVG ARRIVAL DELAY (MIN)"),
                ("Average Service Rating", "AVG SERVICE RATING (1-5)"), ("Lowest Rated Attribute", "LOWEST-RATED SERVICE", 15)])
    sat_stack(p, 20, 242, 380, 280, "Satisfaction by Travel Class", c("DimTravel", "Class"), label="eda class")
    sat_stack(p, 410, 242, 380, 280, "", c("FactPassenger", "Delay Bucket"), title_measure="Title - Delay Chart", label="eda delay")
    sat_stack(p, 800, 242, 380, 280, "Satisfaction by Age Band", c("DimPassengerProfile", "Age Band"), label="eda age")
    sat_stack(p, 1190, 242, 390, 280, "Returning vs First-time Passengers", c("DimPassengerProfile", "Customer Type"),
              kind="hundredPercentStackedBarChart", label="eda customer")
    cat = c("FactServiceRating", "Rating Category")
    p.chart("hundredPercentStackedBarChart", 20, 534, 640, 332, "Satisfaction Survey: how passengers rated each service",
            category=c("DimServiceAttribute", "Service Attribute"), series=cat, values=[m("Rating Share")],
            objects=chart_objects(legend="Top", labels=True, label_color=WHITE, val_axis=False, gridlines=False, cat_size=8, label_size=8,
                                  datapoints=dp_colors("FactServiceRating", "Rating Category", RATING_COLORS)),
            subtitle="Poor 1-2 | Average 3 | Good 4-5 | Not rated 0", label="survey stacked")
    p.chart("clusteredBarChart", 670, 534, 470, 332, "Rating gap: satisfied minus neutral/dissatisfied",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Rating Gap (Satisfied - Not)")],
            sort=(m("Rating Gap (Satisfied - Not)"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8, label_size=8,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]), label="rating gap")
    insight_table(p, 1150, 534, 430, 332, "LIVE OBSERVATIONS", ["Who is happiest?", "Travel-type gap", "Customer-type gap", "Gender gap", "Delay effect", "Service gap"], size=9)

    # ============================= 3 MODEL PERFORMANCE (comparison + CV + subgroups + drivers) =============================
    p = new("model")
    chrome(p, ctx, "model", extra_slicers=[(c("DimModel", "Model"), "Model", {}), (c("SubgroupPerformance", "Attribute"), "Passenger attribute (subgroups)", {})])
    kpi_row(p, [("Best Model", "BEST PERFORMING MODEL", 20), ("Best Macro F1", "BEST MACRO F1"), ("Best Macro Recall", "BEST MACRO RECALL"),
                ("Best ROC-AUC", "BEST ROC-AUC"), ("Recall Gap (pts)", "SUBGROUP RECALL GAP (PTS)")])
    p.chart("clusteredBarChart", 20, 242, 440, 290, "", category=c("DimModel", "Model"),
            values=[m("Model Accuracy"), m("Model Macro F1"), m("Model Macro Recall")], title_measure="Title - Model Chart",
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", label_size=8,
                                  datapoints=dp_measures({"Model Accuracy": TEAL, "Model Macro F1": NAVY, "Model Macro Recall": BLUE})),
            label="model compare")
    p.chart("lineChart", 470, 242, 360, 290, "Cross-validation: Macro F1 per fold", category=c("CVScores", "Fold"),
            series=c("DimModel", "Model"), values=[m("Fold Macro F1")],
            objects=chart_objects(legend="Bottom", labels=False, val_axis=True, gridlines=True,
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv lines")
    p.chart("lineChart", 840, 242, 370, 290, "CV error bands: mean +/- 1 std-dev", category=c("DimModel", "Model"),
            values=[m("CV Upper Band"), m("CV Mean Macro F1"), m("CV Lower Band")],
            objects=chart_objects(legend="Top", labels=False, val_axis=True, gridlines=True,
                                  datapoints=dp_measures({"CV Upper Band": TEAL, "CV Mean Macro F1": NAVY, "CV Lower Band": AMBER}),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv error bands")
    p.matrix(1220, 242, 360, 290, "Confusion matrix counts (test set)", [c("DimModel", "Model")], [],
             [m("Confusion TN"), m("Confusion FP"), m("Confusion FN"), m("Confusion TP")], size=9, label="confusion matrix")
    p.chart("clusteredBarChart", 20, 544, 520, 322, "Recall by passenger group (use the attribute slicer)", category=c("SubgroupPerformance", "Group Label"),
            series=c("DimModel", "Model"), values=[m("Subgroup Recall")],
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8, label_size=8,
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS)), label="subgroup recall")
    p.chart("clusteredBarChart", 550, 544, 500, 322, "Association vs model importance: top SHAP features (hover for details)",
            category=c("ShapImportance", "Feature"), values=[m("Top 10 SHAP")], sort=(m("Top 10 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8, label_size=8,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]),
            tooltip_page=ctx_pages["tooltip"].id, label="shap top10")
    insight_table(p, 1060, 544, 520, 322, "EVALUATION CONCLUSION  |  calculated", ["Best model", "Stability", "Fairness check"], size=9)

    # ============================= 7 AI EXPLAINABILITY (replicates AI_Explainability.pbix) =============================
    p = new("explain")
    chrome(p, ctx, "explain")
    p.dy = 0
    X, Y0, YS = 1600 / 1920.0, 96.0, (900 - 96 - 8) / 1081.0
    R = lambda x, y, w, h: (x * X, Y0 + y * YS, w * X, h * YS)  # noqa: E731
    def head(x, y, w, h, text):
        p.textbox(*R(x, y, w, h), [{"runs": [(text, 13, True, NAVY)], "align": "center"}], label=f"head {text[:20]}")
    head(41, 8, 673, 60, "Top 5 Factors Influencing Satisfaction Predictions")
    p.chart("clusteredBarChart", *R(41, 76, 673, 325), "", category=c("ShapImportance", "Feature"), values=[m("Top 5 SHAP")],
            sort=(m("Top 5 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]),
            tooltip_page=ctx_pages["tooltip"].id, label="top5 shap explain")
    head(41, 418, 673, 49, "Gemini AI Explanation")
    p.table(*R(41, 467, 673, 197), "", [m("Gemini Explanation")], size=10, label="gemini text")
    head(751, 8, 809, 40, "Individual Passenger \u2014 SHAP Feature Contributions")
    p.chart("clusteredBarChart", *R(751, 47, 809, 617), "", category=c("ShapLocal", "Feature"), values=[m("Net SHAP Value")],
            sort=(m("Net SHAP Value"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, cat_size=9, label_size=8,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]),
            subtitle="Positive pushes toward Satisfied, negative toward Neutral/Dissatisfied", label="individual shap")
    p.card(*R(1575, 47, 331, 156), "Selected Prediction Confidence", "PREDICTED CLASS PROBABILITY", color=NAVY, size=24)
    p.slicer(*R(1575, 210, 331, 156), c("GeminiInsights", "Passenger Label"), title="Explained passenger", single=True,
             default=F["first_label"], label="passenger list")
    p.card(*R(1575, 373, 331, 138), "Selected Predicted Class", "PREDICTED CLASS", color=BLUE, size=15)
    p.card(*R(1575, 518, 331, 138), "Selected Actual Class", "ACTUAL CLASS", color=TEAL, size=15)
    p.table(*R(33, 683, 1887, 146), "Gemini service-improvement recommendations",
            [c("GeminiRecommendations", "Evidence Feature"), c("GeminiRecommendations", "Recommendation"), c("GeminiRecommendations", "Reason")],
            size=10, label="gemini recs")
    head(33, 836, 1852, 36, "KEY EXPLAINABILITY FINDINGS")
    left = [[("1. Dominant Features", 11, True, NAVY)],
            [("In-flight WiFi Service and Type of Travel are the two most influential features in the global SHAP analysis.", 10, False, TEXT)],
            [("2. Individual Prediction Behaviour", 11, True, NAVY)],
            [("SHAP values reveal how individual features contribute positively or negatively to a passenger's prediction.", 10, False, TEXT)]]
    right = [[("3. AI-Generated Interpretability", 11, True, NAVY)],
             [("Gemini converts SHAP evidence into human-readable explanations, making model predictions easier to understand.", 10, False, TEXT)],
             [("4. Actionable Insights", 11, True, NAVY)],
             [("Gemini generates service improvement recommendations based on influential features and their contribution to individual predictions.", 10, False, TEXT)]]
    p.textbox(*R(41, 872, 940, 205), left, bg=WHITE, border=BORDER, radius=8, label="findings left")
    p.textbox(*R(1000, 872, 920, 205), right, bg=WHITE, border=BORDER, radius=8, label="findings right")

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
    p.dy = 16
    p.begin_group("Header", 0, 0, 1600, 88)
    p.textbox(0, 0, 1600, 84, [[(" ", 4, False, WHITE)]], bg=NAVY, label="banner")
    p.textbox(0, 84, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="banner accent")
    p.textbox(100, 10, 900, 64, [[("PASSENGER SEGMENT DETAIL", 18, True, WHITE)],
                                 [("Drill-through page: right-click a Class / Satisfaction Tier anywhere in the report -> Drill through", 9, False, "#BBD4F5")]],
              label="segment title")
    p.button(20, 22, 60, 40, "\u2190", link_back(), fill="#24508F", hover=BLUE, size=16, label="back button")
    p.end_group()
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
