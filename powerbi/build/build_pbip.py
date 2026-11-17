#!/usr/bin/env python3
"""Generate the Team 11 Power BI project (PBIP: TMDL semantic model + PBIR report).

Run:   python powerbi/build/build_pbip.py
Output: powerbi/Team11_Final.pbip, powerbi/Team11_Final.SemanticModel/, powerbi/Team11_Final.Report/
"""
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import model_def as MD  # noqa: E402
import pages as PG  # noqa: E402
import prepare_data  # noqa: E402
from pbir import *  # noqa: E402,F401
from pbir import hid, write_json, Page, Col, colr  # noqa: E402
import tmdl  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "powerbi")
NAME = "Team11_Final"
SM = os.path.join(OUT, f"{NAME}.SemanticModel")
RP = os.path.join(OUT, f"{NAME}.Report")

THEME_NAME = "AirlineBlue.json"
BASE_THEME_SRC = os.path.join(HERE, "assets", "Fluent2-CY26SU08.json")
IMAGES = {  # registered resource name -> source
    "shap_beeswarm.png": "explainability/shap_beeswarm.png",
    "shap_waterfall.png": "explainability/shap_waterfall.png",
    "model_error_bands.png": "models/model_error_bands.png",
    "xgboost_confusion_matrix.png": "models/confusion_matrices/xgboost_confusion_matrix.png",
    "correlation_heatmap.png": "correlation/correlation_heatmap.png",
}


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ----------------------------------------------------------------------------------------------
def build_semantic_model():
    shutil.rmtree(SM, ignore_errors=True)
    write_json(os.path.join(SM, "definition.pbism"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}})
    d = os.path.join(SM, "definition")
    w(os.path.join(d, "database.tmdl"), "database\n\tcompatibilityLevel: 1601\n")
    refs = "\n".join(f"ref table {tmdl.q(t)}" for t in MD.ALL_TABLE_NAMES)
    w(os.path.join(d, "model.tmdl"),
      "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n\n"
      + refs + "\n\nref expression RepoRoot\nref expression stgPassenger\n\nref cultureInfo en-US\n")
    w(os.path.join(d, "cultures", "en-US.tmdl"), "cultureInfo en-US\n")
    w(os.path.join(d, "expressions.tmdl"), MD.expressions_tmdl())
    w(os.path.join(d, "relationships.tmdl"), MD.relationships_tmdl())
    for t in MD.tables():
        name = next(l for l in t.split("\n") if l.startswith("table ")).replace("table ", "").strip("'")
        w(os.path.join(d, "tables", f"{name}.tmdl"), t)
    meas = MD.measure_list()
    w(os.path.join(d, "tables", "_Measures.tmdl"), tmdl.table(
        "_Measures",
        [tmdl.column("Placeholder", "string", hidden=True)],
        '''let
    Source = #table(type table [Placeholder = text], {{""}})
in
    Source''', measures=meas, desc="Home for every DAX measure in the model."))
    return meas


def dax_export(meas):
    """Plain-text copy of every measure (for pasting / review)."""
    lines = ["// Team 11 - DAX measures (generated from powerbi/build/model_def.py)\n"]
    for m in meas:
        lines.append(m)
    w(os.path.join(OUT, "dax", "measures.tmdl.txt"), "\n".join(lines))


# ----------------------------------------------------------------------------------------------
def theme():
    return {
        "name": "Airline Blue", "dataColors": [BLUE, NAVY, TEAL, AMBER, "#6FB1F2", "#4A6FA5", "#9AD0C2", "#F2C27B", "#8FA8C8", "#B8C4D6"],
        "background": "#FFFFFF", "foreground": TEXT, "tableAccent": NAVY, "good": TEAL, "neutral": AMBER, "bad": "#D9534F",
        "maximum": NAVY, "center": "#9CC3F0", "minimum": "#EAF3FD", "firstLevelElements": TEXT, "secondaryElements": MUTED,
        "primaryBackground": "#FFFFFF", "secondaryBackground": BG, "hyperlink": BLUE,
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": NAVY},
            "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": TEXT},
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 26, "color": NAVY},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 10, "color": NAVY},
        },
    }


def build_report():
    shutil.rmtree(RP, ignore_errors=True)
    defn = os.path.join(RP, "definition")
    write_json(os.path.join(OUT, f"{NAME}.pbip"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}})
    write_json(os.path.join(RP, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})

    # ---- pages (segment + tooltip first so overview can link to them) ----
    F = PG.facts(ROOT)
    F["first_label"] = prepare_data.first_label(ROOT)
    reg = {}
    for k in PG.PAGES_ORDER:
        reg[k] = Page(k, PG.TITLES[k])
    seg = Page("segment", "Passenger Segment Detail", hidden=True)
    seg.filters = [
        {"name": hid("seg", "class"), "field": Col("DimTravel", "Class"), "type": "Categorical", "howCreated": "Drillthrough"},
        {"name": hid("seg", "tier"), "field": Col("DimSatisfaction", "Satisfaction Tier"), "type": "Categorical", "howCreated": "Drillthrough"}]
    seg.binding = {"name": hid("seg", "binding"), "type": "Drillthrough", "parameters": [
        {"name": hid("seg", "p1"), "boundFilter": seg.filters[0]["name"], "fieldExpr": Col("DimTravel", "Class")},
        {"name": hid("seg", "p2"), "boundFilter": seg.filters[1]["name"], "fieldExpr": Col("DimSatisfaction", "Satisfaction Tier")}]}
    tt = Page("tooltip", "TT - SHAP Feature", w=360, h=330, hidden=True, kind="tooltip", bg=WHITE)
    tt.filters = [{"name": hid("tt", "feature"), "field": Col("ShapImportance", "Feature"), "type": "Categorical", "howCreated": "Drillthrough"}]
    tt.binding = {"name": hid("tt", "binding"), "type": "Tooltip", "parameters": [
        {"name": hid("tt", "p1"), "boundFilter": tt.filters[0]["name"], "fieldExpr": Col("ShapImportance", "Feature")}]}
    reg["segment"], reg["tooltip"] = seg, tt

    bm_ids = {n: hid("bookmark", n) for n in ("bm_hook", "bm_build", "bm_insight", "bm_conclusion")}
    built = PG.build_pages(ROOT, reg, F, bm_ids)

    order = [built[k].id for k in PG.PAGES_ORDER] + [built["segment"].id, built["tooltip"].id]
    write_json(os.path.join(defn, "pages", "pages.json"), {"$schema": S_PAGES, "pageOrder": order, "activePageName": built["overview"].id})
    for key, pg in built.items():
        base = os.path.join(defn, "pages", pg.id)
        write_json(os.path.join(base, "page.json"), pg.page_json())
        for name, obj in pg.visuals:
            write_json(os.path.join(base, "visuals", name, "visual.json"), obj)

    # ---- bookmarks (story) ----
    story = [("bm_hook", "1 Hook", "overview"), ("bm_build", "2 Build-up", "eda"), ("bm_insight", "3 Insight", "explain"),
             ("bm_conclusion", "4 Conclusion", "conclusion")]
    write_json(os.path.join(defn, "bookmarks", "bookmarks.json"), {"$schema": S_BOOKMARKS, "items": [{"name": bm_ids[n]} for n, _, _ in story]})
    for n, label, page_key in story:
        pid = built[page_key].id
        write_json(os.path.join(defn, "bookmarks", f"{bm_ids[n]}.bookmark.json"), {
            "$schema": S_BOOKMARK, "displayName": label, "name": bm_ids[n],
            "explorationState": {"version": "1.3", "activeSection": pid, "sections": {pid: {"visualContainers": {}}}}})

    # ---- report.json, theme, resources ----
    base = json.load(open("/dev/null")) if False else None
    ver = {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"}
    items = [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}] + \
            [{"name": n, "path": n, "type": "Image"} for n in IMAGES]
    write_json(os.path.join(defn, "report.json"), {
        "$schema": f"{SCHEMA}/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU08", "reportVersionAtImport": ver, "type": "SharedResources"},
                            "customTheme": {"name": THEME_NAME, "reportVersionAtImport": ver, "type": "RegisteredResources"}},
        "objects": {"section": [{"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}],
                    "outspacePane": [{"properties": {"expanded": {"expr": {"Literal": {"Value": "false"}}}}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "Fluent2-CY26SU08", "path": "BaseThemes/Fluent2-CY26SU08.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": items}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    write_json(os.path.join(defn, "version.json"), {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    sr = os.path.join(RP, "StaticResources")
    os.makedirs(os.path.join(sr, "SharedResources", "BaseThemes"), exist_ok=True)
    shutil.copy(BASE_THEME_SRC, os.path.join(sr, "SharedResources", "BaseThemes", "Fluent2-CY26SU08.json"))
    write_json(os.path.join(sr, "RegisteredResources", THEME_NAME), theme())
    for n, src in IMAGES.items():
        shutil.copy(os.path.join(ROOT, src), os.path.join(sr, "RegisteredResources", n))
    return built


def zip_project():
    z = os.path.join(OUT, f"{NAME}_pbip.zip")
    if os.path.exists(z):
        os.remove(z)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for base in (f"{NAME}.pbip", f"{NAME}.SemanticModel", f"{NAME}.Report"):
            p = os.path.join(OUT, base)
            if os.path.isfile(p):
                zf.write(p, base)
            else:
                for dp, _, fs in os.walk(p):
                    for f in fs:
                        full = os.path.join(dp, f)
                        zf.write(full, os.path.relpath(full, OUT))
    return z


if __name__ == "__main__":
    prepare_data.run(ROOT)
    meas = build_semantic_model()
    dax_export(meas)
    built = build_report()
    z = zip_project()
    nvis = sum(len(p.visuals) for p in built.values())
    print(f"pages={len(built)} visual-containers={nvis} measures={len(meas)} zip={z}")
