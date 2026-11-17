"""Report page layouts (1600 x 900 canvas)."""
import glob
import json
import os

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
    f["high_tier"] = (df["satisfaction_tier"] == "High").mean()
    f["low_tier"] = (df["satisfaction_tier"] == "Low").mean()
    mc = pd.read_csv(f"{root}/models/model_comparison.csv").set_index("Model")
    best = mc["Macro F1"].idxmax()
    f["best"], f["best_f1"], f["best_auc"], f["best_acc"] = best, mc.loc[best, "Macro F1"], mc.loc[best, "ROC-AUC"], mc.loc[best, "Accuracy"]
    f["best_cv_mean"], f["best_cv_std"] = mc.loc[best, "CV Macro F1 Mean"], mc.loc[best, "CV Macro F1 Std"]
    sg = pd.read_csv(f"{root}/models/subgroup_model_comparison.csv")
    sg = sg[sg.Model == best].copy()
    sg["label"] = sg.Attribute + ": " + sg.Group
    lo, hi = sg.loc[sg.Recall.idxmin()], sg.loc[sg.Recall.idxmax()]
    f["sg_lo"], f["sg_lo_r"], f["sg_hi"], f["sg_hi_r"] = lo.label, lo.Recall, hi.label, hi.Recall
    sh = pd.read_csv(f"{root}/explainability/shap_importance.csv").sort_values("Rank")
    f["shap_top3"] = ", ".join(sh.Feature[:3])
    f["shap_top1"] = sh.Feature.iloc[0]
    f["shap_top5_share"] = sh.MeanAbsoluteSHAP[:5].sum() / sh.MeanAbsoluteSHAP.sum()
    return f


def findings_box(p, x, y, w, h, title, items, size=10.5, label="findings"):
    paras = [[(title, 12, True, NAVY)]] + [[("\u2022  " + t, size, False, TEXT)] for t in items]
    paras.append([("Computed from the project CSV outputs when the report was generated (full data set, not affected by slicers).", 8, False, MUTED, True)])
    return p.textbox(x, y, w, h, paras, bg=WHITE, border=BORDER, radius=10, shadow=True, label=label)


def pct(x, d=0):
    return f"{x*100:.{d}f}%"


# ------------------------------------------------------------------------------------------------
NANDITA_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "nandita", "page", "visuals")


def load_nandita_page(p):
    """Copy every visual of AI_Explainability.pbix 'Page 1' unchanged (fields, filters, formatting, names), only re-positioning
    the 1920x1080 layout proportionally into the body area under the shared banner and scaling text-box font sizes to match."""
    s = (900 - 92 - 6) / 1080.0
    ox, oy = (1600 - 1920 * s) / 2.0, 92.0
    for f in sorted(glob.glob(os.path.join(NANDITA_PAGE, "*", "visual.json"))):
        d = json.load(open(f, encoding="utf-8"))
        pos = d["position"]
        pos["x"], pos["y"] = ox + pos["x"] * s, oy + pos["y"] * s
        pos["width"], pos["height"] = pos["width"] * s, pos["height"] * s
        pos["z"] += p.z
        pos["tabOrder"] += p.z
        if d["visual"]["visualType"] == "textbox":
            for para in d["visual"]["objects"]["general"][0]["properties"]["paragraphs"]:
                for run in para.get("textRuns", []):
                    fs = run.get("textStyle", {}).get("fontSize")
                    if fs and fs.endswith("pt"):
                        run["textStyle"]["fontSize"] = f"{round(float(fs[:-2]) * s, 1)}pt"
        p.visuals.append((d["name"], d))


class Ctx:
    def __init__(self, pages, bookmarks):
        self.pages = pages        # key -> Page
        self.bm = bookmarks       # name -> bookmark id


def chrome(p, ctx, key, with_passenger_slicers=False, extra_slicers=None, slicer_style="column"):
    """Navy title bar (three centred white lines, as in the project title block) + optional filter slicers."""
    p.dy = 0
    p.begin_group("Header", 0, 0, 1600, 84)
    p.textbox(0, 0, 1600, 80, [[(" ", 4, False, WHITE)]], bg=NAVY, label="title bar")
    p.textbox(0, 80, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="title bar accent")
    p.textbox(0, 3, 1600, 76, [
        {"runs": [("BEYOND THE BOARDING PASS", 17, True, WHITE)], "align": "center"},
        {"runs": [("Uncovering the Key Drivers of Airline Passenger Satisfaction", 11, False, WHITE)], "align": "center"},
        {"runs": [("TEAM 11  |  PASSENGER EXPERIENCE ANALYTICS", 11, False, WHITE)], "align": "center"}], label="report title")
    p.end_group()
    if with_passenger_slicers:
        specs = [(c("DimPassengerProfile", "Gender"), "Gender", "Gender"), (c("DimTravel", "Class"), "Class", "Travel Class"),
                 (c("DimPassengerProfile", "Customer Type"), "CustomerType", "Customer Type"),
                 (c("DimTravel", "Type of Travel"), "TypeOfTravel", "Type of Travel")]
        if slicer_style == "strip":      # dropdown row under the title bar
            p.begin_group("Filters", 20, 90, 1560, 50)
            for i, (ref, sync, nm) in enumerate(specs):
                p.slicer(20 + i * 390, 90, 380, 50, ref, sync=sync, title=nm, label=f"slicer {nm}")
            p.end_group()
        else:                            # list slicers in a right-hand column
            p.begin_group("Filters", 1290, 90, 290, 476)
            for (ref, sync, nm), (yy, hh) in zip(specs, [(90, 104), (204, 134), (348, 104), (462, 104)]):
                p.slicer(1290, yy, 290, hh, ref, sync=sync, title=nm, label=f"slicer {nm}", mode="Basic")
            p.end_group()
    if extra_slicers:
        p.begin_group("Filters", 20, 90, 1560, 50)
        n = len(extra_slicers)
        w = min(500, int((1560 - 10 * (n - 1)) / n))
        for i, (ref, nm, kw) in enumerate(extra_slicers):
            p.slicer(20 + i * (w + 10), 90, w, 50, ref, title=nm, label=f"slicer {nm}", **kw)
        p.end_group()


def kpi_row(p, specs, y=148, h=88, color_cycle=(NAVY, BLUE, TEAL, AMBER, NAVY), x0=20, total_w=1560):
    n = len(specs)
    gap = 10
    w = (total_w - gap * (n - 1)) / n
    p.begin_group("KPI strip", x0, y, total_w, h)
    for i, (meas, label, *rest) in enumerate(specs):
        size = rest[0] if rest else 26
        p.card(x0 + i * (w + gap), y, w, h, meas, label, color=color_cycle[i % len(color_cycle)] if i % 2 == 0 else NAVY,
               size=size, accent=color_cycle[i % len(color_cycle)])
    p.end_group()


def insights_filter(topics):
    return [{"name": hid("insfilter", *topics), "field": Col("Insights", "Topic"), "type": "Categorical",
             "filter": {"Version": 2, "From": [{"Name": "s", "Entity": "Insights", "Type": 0}],
                        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": "Topic"}}],
                                                        "Values": [[{"Literal": {"Value": "'" + t + "'"}}] for t in topics]}}}]}}]


def insight_table(p, x, y, w, h, title, topics, size=11):
    return p.table(x, y, w, h, title, [c("Insights", "Topic"), m("Insight Text")], filters=insights_filter(topics), size=size,
                   label=f"insights {title}",
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

    # ============================= 1 OVERVIEW (detailed version) =============================
    p = new("overview")
    chrome(p, ctx, "overview", with_passenger_slicers=True, slicer_style="strip")
    kpi_row(p, [("Total Passengers", "TOTAL PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"),
                ("High Tier Rate", "HIGH-TIER RATE"), ("Average Service Rating", "AVG SERVICE RATING (1-5)"),
                ("Best Macro F1", "BEST MODEL MACRO F1")], y=148, h=88)
    p.donut(20, 246, 375, 300, "Passenger Satisfaction", c("DimSatisfaction", "Satisfaction"), m("Total Passengers"), SAT_COLORS)
    p.donut(405, 246, 375, 300, "Satisfaction Tier Mix", c("DimSatisfaction", "Satisfaction Tier"), m("Total Passengers"), TIER_COLORS)
    sat_stack(p, 790, 246, 400, 300, "", c("DimTravel", "Class"), title_measure="Title - Class Chart", label="class mix")
    p.chart("clusteredBarChart", 1200, 246, 380, 300, "Top 5 Satisfaction Drivers (SHAP)", category=c("ShapImportance", "Feature"),
            values=[m("Top 5 SHAP")], sort=(m("Top 5 SHAP"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]), label="top5 shap overview")
    findings_box(p, 20, 558, 900, 322, "KEY FINDINGS", [
        f"{pct(F['sat_rate'], 1)} of {F['n']:,} passengers are satisfied; {pct(F['high_tier'], 1)} reach the High satisfaction tier and {pct(F['low_tier'], 1)} fall in the Low tier.",
        f"Business class passengers are {pct(F['by_class']['Business'])} satisfied versus {pct(F['by_class']['Economy'])} in Economy.",
        f"Passengers arriving more than 15 minutes late are {pct(F['sat_late'])} satisfied versus {pct(F['sat_ontime'])} when on time ({pct(F['late_share'])} of passengers are delayed).",
        f"Lowest-rated service: {list(F['avg_rating'])[0]} ({list(F['avg_rating'].values())[0]:.2f}/5); best: {list(F['avg_rating'])[-1]} ({list(F['avg_rating'].values())[-1]:.2f}/5).",
    ], size=12, label="key findings")
    p.matrix(930, 558, 650, 322, "Model Performance Summary (held-out test)", [c("DimModel", "Model")], [],
             [m("Model Accuracy"), m("Model Macro F1"), m("Model ROC-AUC"), m("CV Mean Macro F1")], size=10, label="model summary matrix")

    # ============================= 2 EDA & PASSENGER ANALYSIS (incl. service quality) =============================
    p = new("eda")
    chrome(p, ctx, "eda", with_passenger_slicers=True, slicer_style="column")
    kpi_row(p, [("Total Passengers", "PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"), ("Avg Arrival Delay", "AVG ARRIVAL DELAY (MIN)"),
                ("Average Service Rating", "AVG SERVICE RATING (1-5)")], y=90, h=104, x0=20, total_w=1250)
    sat_stack(p, 20, 206, 620, 324, "Satisfaction by Travel Class",
              [("h", "DimTravel", "Travel Hierarchy", "Class"), ("h", "DimTravel", "Travel Hierarchy", "Type of Travel")], label="eda class drill")
    sat_stack(p, 650, 206, 620, 324, "", c("FactPassenger", "Delay Bucket"), title_measure="Title - Delay Chart", label="eda delay")
    cat = c("FactServiceRating", "Rating Category")
    p.chart("hundredPercentStackedBarChart", 20, 542, 760, 338, "Satisfaction Survey: how passengers rated each service",
            category=c("DimServiceAttribute", "Service Attribute"), series=cat, values=[m("Rating Share")],
            objects=chart_objects(legend="Top", labels=True, label_color=WHITE, val_axis=False, gridlines=False, cat_size=8, label_size=8,
                                  datapoints=dp_colors("FactServiceRating", "Rating Category", RATING_COLORS)),
            subtitle="Poor 1-2 | Average 3 | Good 4-5 | Not rated 0", label="survey stacked")
    p.chart("clusteredBarChart", 790, 542, 480, 338, "Rating gap: satisfied minus neutral/dissatisfied",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Rating Gap (Satisfied - Not)")],
            sort=(m("Rating Gap (Satisfied - Not)"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=8, label_size=8,
                                  datapoints=[{"properties": {"fill": colr(NAVY)}}]), label="rating gap")

    # ============================= 3 MODEL PERFORMANCE =============================
    p = new("model")
    chrome(p, ctx, "model", extra_slicers=[(c("DimModel", "Model"), "Model", {}), (c("SubgroupPerformance", "Attribute"), "Passenger attribute (subgroups)", {})])
    kpi_row(p, [("Best Model", "BEST PERFORMING MODEL", 20), ("Best Macro F1", "BEST MACRO F1"), ("Best Macro Recall", "BEST MACRO RECALL"),
                ("Best ROC-AUC", "BEST ROC-AUC"), ("Recall Gap (pts)", "SUBGROUP RECALL GAP (PTS)")])
    p.chart("clusteredBarChart", 20, 242, 560, 300, "", category=c("DimModel", "Model"),
            values=[m("Model Accuracy"), m("Model Macro F1"), m("Model Macro Recall")], title_measure="Title - Model Chart",
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", label_size=8,
                                  datapoints=dp_measures({"Model Accuracy": TEAL, "Model Macro F1": NAVY, "Model Macro Recall": BLUE})),
            label="model compare")
    p.chart("lineChart", 590, 242, 490, 300, "Five-fold cross-validation: Macro F1 per fold", category=c("CVScores", "Fold"),
            series=c("DimModel", "Model"), values=[m("Fold Macro F1")],
            objects=chart_objects(legend="Bottom", labels=False, val_axis=True, gridlines=True,
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv lines")
    p.chart("lineChart", 1090, 242, 490, 300, "Error bands: mean Macro F1 +/- 1 std-dev", category=c("DimModel", "Model"),
            values=[m("CV Upper Band"), m("CV Mean Macro F1"), m("CV Lower Band")],
            objects=chart_objects(legend="Top", labels=False, val_axis=True, gridlines=True,
                                  datapoints=dp_measures({"CV Upper Band": TEAL, "CV Mean Macro F1": NAVY, "CV Lower Band": AMBER}),
                                  extra={"markers": [{"properties": {"show": lit(True)}}]}), label="cv error bands")
    p.matrix(20, 554, 560, 312, "Confusion matrix counts (held-out test set)", [c("DimModel", "Model")], [],
             [m("Confusion TN"), m("Confusion FP"), m("Confusion FN"), m("Confusion TP")], size=10, label="confusion matrix")
    p.chart("clusteredBarChart", 590, 554, 990, 312, "Subgroup performance: recall by passenger group (use the attribute slicer)",
            category=c("SubgroupPerformance", "Group Label"), series=c("DimModel", "Model"), values=[m("Subgroup Recall")],
            objects=chart_objects(legend="Top", labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9, label_size=8,
                                  datapoints=dp_colors("DimModel", "Model", MODEL_COLORS)), label="subgroup recall")

    # ============================= 4 AI EXPLAINABILITY: Nandita's page, copied verbatim =============================
    p = new("explain")
    chrome(p, ctx, "explain")
    p.dy = 0
    load_nandita_page(p)

    # ============================= 8 CONCLUSION =============================
    p = new("conclusion")
    chrome(p, ctx, "conclusion")
    kpi_row(p, [("Total Passengers", "PASSENGERS ANALYSED"), ("Satisfaction Rate", "SATISFACTION RATE"), ("Best Model", "BEST MODEL", 20),
                ("Best Macro F1", "BEST MACRO F1"), ("Recall Gap (pts)", "WIDEST SUBGROUP RECALL GAP (PTS)")])
    lw = list(F["avg_rating"].items())
    findings_box(p, 20, 242, 900, 420, "WHAT THE DATA SAYS", [
        f"{pct(F['sat_rate'], 1)} of {F['n']:,} passengers are satisfied; {pct(F['high_tier'], 1)} reach the High tier and {pct(F['low_tier'], 1)} the Low tier.",
        f"Business class is {pct(F['by_class']['Business'])} satisfied versus {pct(F['by_class']['Economy'])} for Economy and {pct(F['by_class']['Economy Plus'])} for Economy Plus.",
        f"Arrivals more than 15 minutes late are {pct(F['sat_late'])} satisfied versus {pct(F['sat_ontime'])} on time.",
        f"Lowest-rated service: {lw[0][0]} ({lw[0][1]:.2f}/5); highest: {lw[-1][0]} ({lw[-1][1]:.2f}/5).",
        f"{F['best']} leads on held-out Macro F1 ({pct(F['best_f1'], 1)}), ROC-AUC {F['best_auc']:.3f} and accuracy {pct(F['best_acc'], 1)}.",
        f"Five-fold CV Macro F1 for {F['best']}: {F['best_cv_mean']:.4f} +/- {F['best_cv_std']:.4f} (std-dev across folds) - stable.",
        f"For {F['best']}, recall of the Satisfied class ranges from {pct(F['sg_lo_r'], 1)} ({F['sg_lo']}) to {pct(F['sg_hi_r'], 1)} ({F['sg_hi']}): a performance disparity to investigate, not proof of discrimination.",
        f"Top SHAP drivers: {F['shap_top3']}; the top five carry {pct(F['shap_top5_share'])} of total mean |SHAP|.",
    ], size=11, label="conclusion findings")
    findings_box(p, 930, 242, 650, 420, "RECOMMENDATIONS", [
        f"Fix the weakest touch-points first: {lw[0][0]} ({lw[0][1]:.2f}/5), {lw[1][0]} ({lw[1][1]:.2f}/5) and {lw[2][0]} ({lw[2][1]:.2f}/5).",
        f"Protect {F['shap_top1']} - the single largest model driver - and keep it consistent across airports.",
        f"Target Economy and personal-travel passengers ({pct(F['by_class']['Economy'])} and {pct(F['by_travel']['Personal'])} satisfied) with service recovery rather than blanket spend.",
        f"Manage delays: delayed arrivals are only {pct(F['sat_late'])} satisfied versus {pct(F['sat_ontime'])} on time - invest in delay communication and recovery.",
        f"Recognise the teams behind {lw[-1][0]} ({lw[-1][1]:.2f}/5): they out-score the rest of the journey.",
    ], size=11, label="conclusion recommendations")
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
    p.button(942, 716, 300, 50, "↺  Restart the story (Hook)", link_page(ctx_pages["overview"].id), fill=NAVY, hover=BLUE, size=10, label="restart")
    p.button(1252, 716, 316, 50, "Segment detail (drill-through page)", link_page(ctx_pages["segment"].id), fill=BLUE, hover=NAVY, size=10, label="to segment")
    p.button(942, 776, 300, 50, "Model performance", link_page(ctx_pages["model"].id), fill=TEAL, hover=NAVY, size=10, label="to model")
    p.button(1252, 776, 316, 50, "AI explainability", link_page(ctx_pages["explain"].id), fill=AMBER, hover=NAVY, size=10, label="to explain")
    p.end_group()

    # ============================= Drill-through: Passenger Segment Detail =============================
    p = ctx_pages["segment"]
    P["segment"] = p
    p.dy = 0
    p.begin_group("Header", 0, 0, 1600, 84)
    p.textbox(0, 0, 1600, 80, [[(" ", 4, False, WHITE)]], bg=NAVY, label="title bar")
    p.textbox(0, 80, 1600, 4, [[(" ", 2, False, AMBER)]], bg=AMBER, label="title bar accent")
    p.textbox(0, 3, 1600, 76, [
        {"runs": [("BEYOND THE BOARDING PASS", 17, True, WHITE)], "align": "center"},
        {"runs": [("Uncovering the Key Drivers of Airline Passenger Satisfaction", 11, False, WHITE)], "align": "center"},
        {"runs": [("TEAM 11  |  PASSENGER EXPERIENCE ANALYTICS", 11, False, WHITE)], "align": "center"}], label="report title")
    p.button(20, 18, 120, 44, "\u2190  BACK", link_back(), fill=AMBER, color=NAVY, hover=WHITE, size=14, label="back button")
    p.end_group()
    p.textbox(20, 90, 1560, 50, [[("Passenger Segment Detail", 15, True, NAVY)], [("Drill-through page. Use the BACK button (top left) to return with your filters kept.", 9.5, False, MUTED, True)]], label="segment heading")
    kpi_row(p, [("Total Passengers", "PASSENGERS"), ("Satisfaction Rate", "SATISFACTION RATE"), ("High Tier Rate", "HIGH-TIER RATE"),
                ("Average Service Rating", "AVG SERVICE RATING"), ("Avg Arrival Delay", "AVG ARRIVAL DELAY (MIN)")])
    p.matrix(20, 242, 900, 638, "Segment breakdown", [c("DimTravel", "Class"), c("DimTravel", "Type of Travel"), c("DimPassengerProfile", "Customer Type")], [],
             [m("Total Passengers"), m("Satisfaction Rate"), m("High Tier Rate"), m("Avg Departure Delay"), m("Avg Arrival Delay"),
              m("Avg Flight Distance"), m("Average Service Rating")], size=10, label="segment matrix")
    p.chart("clusteredBarChart", 930, 242, 650, 638, "Average rating by service attribute (this segment)",
            category=c("DimServiceAttribute", "Service Attribute"), values=[m("Average Service Rating")],
            sort=(m("Average Service Rating"), "Descending"),
            objects=chart_objects(labels=True, val_axis=False, gridlines=False, label_pos="OutsideEnd", cat_size=9,
                                  datapoints=[{"properties": {"fill": colr(BLUE)}}]), label="segment ratings")

    return P
