"""Helpers that emit PBIR (Power BI enhanced report format) JSON."""
import hashlib
import json
import os

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
S_VISUAL = f"{SCHEMA}/visualContainer/2.14.0/schema.json"
S_GROUP = f"{SCHEMA}/visualContainerGroup/1.0.0/schema.json"
S_PAGE = f"{SCHEMA}/page/2.1.0/schema.json"
S_PAGES = f"{SCHEMA}/pagesMetadata/1.1.0/schema.json"
S_BOOKMARK = f"{SCHEMA}/bookmark/2.1.0/schema.json"
S_BOOKMARKS = f"{SCHEMA}/bookmarksMetadata/1.0.0/schema.json"

# ---- palette (shared Team 11 design rules) ----
NAVY, BLUE, TEAL, AMBER = "#173D75", "#2389ED", "#65B7A3", "#E8A044"
BG, TEXT = "#F3F6FA", "#172334"
HEADER_DARK = "#0F2B57"
MUTED, BORDER, WHITE, GRID = "#5B6B82", "#D5DFEC", "#FFFFFF", "#E6EDF6"
SAT_COLORS = {"Satisfied": BLUE, "Neutral or Dissatisfied": AMBER}
TIER_COLORS = {"High": NAVY, "Average": TEAL, "Low": AMBER}
RATING_COLORS = {"Good": BLUE, "Average": TEAL, "Poor": AMBER, "Not Rated": "#B8C4D6"}
MODEL_COLORS = {"Logistic Regression": TEAL, "Random Forest": BLUE, "XGBoost": NAVY}
FONT = "Segoe UI"


def hid(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:20]


# ---- literals ----
def lit(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, str):
        s = "'" + v.replace("'", "''") + "'"
    elif isinstance(v, int):
        s = f"{v}L"
    else:
        s = f"{v}D"
    return {"expr": {"Literal": {"Value": s}}}


def num(v):
    return {"expr": {"Literal": {"Value": f"{float(v)}D"}}}


def colr(c):
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{c}'"}}}}}


# ---- field references ----
def Col(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def Mea(c, t="_Measures"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def fld(ref):
    """ref: ('c', table, name) | ('m', name) | ('h', table, hierarchy, level)"""
    if ref[0] == "h":
        return {"HierarchyLevel": {"Expression": {"Hierarchy": {"Expression": {"SourceRef": {"Entity": ref[1]}}, "Hierarchy": ref[2]}}, "Level": ref[3]}}
    return Col(ref[1], ref[2]) if ref[0] == "c" else Mea(ref[1])


def proj(ref, display=None, active=True):
    f = fld(ref)
    if ref[0] == "h":
        qr = f"{ref[1]}.{ref[2]}.{ref[3]}"
        nq = ref[3]
    elif ref[0] == "c":
        qr = f"{ref[1]}.{ref[2]}"
        nq = ref[2]
    else:
        qr = f"_Measures.{ref[1]}"
        nq = ref[1]
    d = {"field": f, "queryRef": qr, "nativeQueryRef": nq}
    if ref[0] in ("c", "h") and active:
        d["active"] = True
    if display:
        d["displayName"] = display
    return d


def qref(ref):
    if ref[0] == "h":
        return f"{ref[1]}.{ref[2]}.{ref[3]}"
    return f"{ref[1]}.{ref[2]}" if ref[0] == "c" else f"_Measures.{ref[1]}"


def c(t, n):
    return ("c", t, n)


def m(n):
    return ("m", n)


def query(buckets, sort=None):
    qs = {}
    for k, v in buckets.items():
        if not v:
            continue
        pl = [proj(r) if not isinstance(r, dict) else r for r in v]
        for i, r in enumerate(v):
            if i > 0 and not isinstance(r, dict) and r[0] == "h":
                pl[i].pop("active", None)   # only the top hierarchy level is active; the rest are drill levels
        qs[k] = {"projections": pl}
    q = {"queryState": qs}
    if sort:
        ref, direction = sort
        q["sortDefinition"] = {"sort": [{"field": fld(ref), "direction": direction}], "isDefaultSort": True}
    return q


# ---- container formatting ----
def vco(title=None, title_color=NAVY, title_size=12, title_align="left", bg=WHITE, border=BORDER, radius=10,
        shadow=True, bg_transparency=0, link=None, tooltip_page=None, title_measure=None, subtitle=None):
    o = {}
    if title or title_measure:
        tp = {"show": lit(True), "fontColor": colr(title_color), "fontSize": num(title_size), "bold": lit(True),
              "alignment": lit(title_align), "fontFamily": lit("Segoe UI Semibold")}
        if title_measure:
            tp["text"] = {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": title_measure}}}
        else:
            tp["text"] = lit(title)
        o["title"] = [{"properties": tp}]
    else:
        o["title"] = [{"properties": {"show": lit(False)}}]
    if subtitle:
        o["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitle), "fontColor": colr(MUTED), "fontSize": num(9)}}]
    if bg is None:
        o["background"] = [{"properties": {"show": lit(False)}}]
    else:
        o["background"] = [{"properties": {"show": lit(True), "color": colr(bg), "transparency": num(bg_transparency)}}]
    if border:
        o["border"] = [{"properties": {"show": lit(True), "color": colr(border), "radius": num(radius)}}]
    else:
        o["border"] = [{"properties": {"show": lit(False)}}]
    o["dropShadow"] = [{"properties": {"show": lit(bool(shadow))}}]
    if link:
        o["visualLink"] = [{"properties": link}]
    if tooltip_page:
        o["visualTooltip"] = [{"properties": {"show": lit(True), "type": lit("ReportPage"), "section": lit(tooltip_page)}}]
    return o


def link_page(page_id):
    return {"show": lit(True), "type": lit("PageNavigation"), "navigationSection": lit(page_id)}


def link_bookmark(bm):
    return {"show": lit(True), "type": lit("Bookmark"), "bookmark": lit(bm)}


def link_back():
    return {"show": lit(True), "type": lit("Back")}


# ---- data-point colours ----
def dp_colors(table, column, mapping):
    out = []
    for val, color in mapping.items():
        out.append({"properties": {"fill": colr(color)},
                    "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0,
                                  "Left": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}},
                                  "Right": {"Literal": {"Value": "'" + val.replace("'", "''") + "'"}}}}}]}})
    return out


def dp_measures(mapping):
    """colour series that are measures: mapping measure-name -> colour"""
    return [{"properties": {"fill": colr(color)}, "selector": {"metadata": f"_Measures.{n}"}} for n, color in mapping.items()]


# ---- chart objects ----
def chart_objects(legend=None, labels=True, label_color=TEXT, label_size=9, cat_size=9, val_axis=True, val_size=9,
                  datapoints=None, label_fmt=None, legend_size=9, cat_title=None, val_title=None, extra=None,
                  gridlines=True, label_pos=None):
    o = {}
    if legend:
        o["legend"] = [{"properties": {"show": lit(True), "position": lit(legend), "fontSize": num(legend_size),
                                       "labelColor": colr(TEXT)}}]
    else:
        o["legend"] = [{"properties": {"show": lit(False)}}]
    cp = {"fontSize": num(cat_size), "labelColor": colr(TEXT), "showAxisTitle": lit(bool(cat_title))}
    if cat_title:
        cp["titleText"] = lit(cat_title)
        cp["titleFontSize"] = num(9)
        cp["titleColor"] = colr(MUTED)
    o["categoryAxis"] = [{"properties": cp}]
    vp = {"show": lit(val_axis), "fontSize": num(val_size), "labelColor": colr(MUTED), "showAxisTitle": lit(bool(val_title)),
          "gridlineShow": lit(gridlines), "gridlineColor": colr(GRID)}
    if val_title:
        vp["titleText"] = lit(val_title)
        vp["titleFontSize"] = num(9)
        vp["titleColor"] = colr(MUTED)
    o["valueAxis"] = [{"properties": vp}]
    lp = {"show": lit(bool(labels)), "fontSize": num(label_size), "color": colr(label_color)}
    if label_pos:
        lp["labelPosition"] = lit(label_pos)
    if label_fmt:
        lp["labelStyle"] = lit(label_fmt)
    o["labels"] = [{"properties": lp}]
    if datapoints:
        o["dataPoint"] = datapoints
    if extra:
        o.update(extra)
    return o


# ---- page object ----
class Page:
    def __init__(self, key, title, w=1600, h=900, hidden=False, kind=None, bg=BG):
        self.key, self.title, self.w, self.h = key, title, w, h
        self.id = hid("page", key)
        self.hidden, self.kind, self.bg = hidden, kind, bg
        self.visuals = []      # (name, json)
        self.z = 0
        self.filters = None
        self.binding = None
        self.group = None
        self.dy = 0

    # -- low level --
    def _pos(self, x, y, w, h):
        if y >= 130:
            y += self.dy
        self.z += 1000
        return {"x": float(x), "y": float(y), "z": self.z, "height": float(h), "width": float(w), "tabOrder": self.z}

    def add(self, vtype, x, y, w, h, q=None, objects=None, container=None, filters=None, sync=None, label=None, extra=None):
        name = hid(self.key, label or vtype, len(self.visuals))
        v = {"visualType": vtype}
        if q:
            v["query"] = q
        if objects:
            v["objects"] = objects
        if container is not None:
            v["visualContainerObjects"] = container
        v["drillFilterOtherVisuals"] = True
        d = {"$schema": S_VISUAL, "name": name, "position": self._pos(x, y, w, h), "visual": v}
        if self.group:
            d["parentGroupName"] = self.group
        if sync:
            v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
        if filters:
            d["filterConfig"] = {"filters": filters}
        if extra:
            d.update(extra)
        self.visuals.append((name, d))
        return name

    def begin_group(self, label, x, y, w, h):
        gid = hid(self.key, "group", label)
        if y >= 130:
            y += self.dy
        self.z += 1000
        d = {"$schema": S_VISUAL, "name": gid,
             "position": {"x": float(x), "y": float(y), "z": self.z, "height": float(h), "width": float(w), "tabOrder": self.z},
             "visualGroup": {"displayName": label, "groupMode": "ScaleMode"}}
        self.visuals.append((gid, d))
        self.group = gid
        return gid

    def end_group(self):
        self.group = None

    # -- primitives --
    def textbox(self, x, y, w, h, paras, bg=None, border=None, radius=0, label="text", shadow=False, link=None, valign=None):
        """paras: list of paragraphs; paragraph = list of runs (text, size, bold, color) or dict with align."""
        ps = []
        for p in paras:
            align = "left"
            runs = p
            if isinstance(p, dict):
                align = p.get("align", "left")
                runs = p["runs"]
            tr = []
            for r in runs:
                txt, size, bold, color = r[:4]
                ts = {"fontSize": f"{size}pt", "color": color, "fontFamily": FONT}
                if bold:
                    ts["fontWeight"] = "bold"
                if len(r) > 4 and r[4]:
                    ts["fontStyle"] = "italic"
                tr.append({"value": txt, "textStyle": ts})
            ps.append({"textRuns": tr, "horizontalTextAlignment": align})
        cont = vco(bg=bg, border=border, radius=radius, shadow=shadow, link=link)
        return self.add("textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": ps}}]}, container=cont, label=label)

    def button(self, x, y, w, h, text, link, fill=NAVY, color=WHITE, hover=BLUE, size=11, bold=True, label=None, align="Center", radius=8,
               outline=None):
        o = {
            "icon": [{"properties": {"shapeType": lit("blank")}, "selector": {"id": "default"}}],
            "text": [{"properties": {"show": lit(True), "text": lit(text), "fontColor": colr(color), "fontSize": num(size),
                                     "bold": lit(bold), "horizontalAlignment": lit(align), "fontFamily": lit(FONT)},
                      "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": lit(True), "fillColor": colr(fill), "transparency": num(0)}, "selector": {"id": "default"}},
                     {"properties": {"show": lit(True), "fillColor": colr(hover), "transparency": num(0)}, "selector": {"id": "hover"}}],
            "outline": [{"properties": {"show": lit(bool(outline)), "lineColor": colr(outline or fill)}, "selector": {"id": "default"}}],
            "shape": [{"properties": {"roundEdge": num(radius)}}],
        }
        cont = vco(bg=None, border=None, shadow=False, link=link)
        return self.add("actionButton", x, y, w, h, objects=o, container=cont, label=label or f"btn {text}")

    def card(self, x, y, w, h, measure, label, color=NAVY, size=26, fmt_lbl=True, accent=None, tooltip_page=None):
        acc = accent or color
        self.textbox(x, y, w, 5, [[(" ", 2, False, acc)]], bg=acc, label=f"accent {label}", border=None)
        o = {"labels": [{"properties": {"color": colr(color), "fontSize": num(size), "fontFamily": lit("Segoe UI Semibold"),
                                        "labelDisplayUnits": num(0)}}],
             "categoryLabels": [{"properties": {"show": lit(True), "color": colr(MUTED), "fontSize": num(10), "fontFamily": lit(FONT)}}]}
        q = query({"Values": [m(measure)]})
        q["queryState"]["Values"]["projections"][0]["displayName"] = label
        return self.add("card", x, y, w, h, q=q, objects=o, container=vco(bg=WHITE, border=BORDER, radius=8),
                        label=f"kpi {label}")

    def slicer(self, x, y, w, h, ref, sync=None, title=None, single=False, default=None, multi_dropdown=True, label=None):
        o = {"data": [{"properties": {"mode": lit("Dropdown")}}],
             "header": [{"properties": {"show": lit(True), "fontColor": colr(NAVY), "textSize": num(9), "bold": lit(True),
                                        "fontFamily": lit(FONT)}}],
             "items": [{"properties": {"fontColor": colr(TEXT), "textSize": num(10), "fontFamily": lit(FONT)}}],
             "selection": [{"properties": {"singleSelect": lit(bool(single)), "selectAllCheckboxEnabled": lit(not single)}}]}
        filt = None
        if default:
            tname, cname = ref[1], ref[2]
            filt = [{"name": hid(self.key, "slicerfilter", label or cname), "field": Col(tname, cname), "type": "Categorical",
                     "filter": {"Version": 2, "From": [{"Name": "s", "Entity": tname, "Type": 0}],
                                "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": cname}}],
                                                                "Values": [[{"Literal": {"Value": "'" + default.replace("'", "''") + "'"}}]]}}}]}}]
        cont = vco(title=title, title_size=9, title_color=NAVY, bg=WHITE, border=BORDER, radius=8, shadow=False)
        if not title:
            cont["title"] = [{"properties": {"show": lit(False)}}]
        return self.add("slicer", x, y, w, h, q=query({"Values": [ref]}), objects=o, container=cont, sync=sync, filters=filt,
                        label=label or f"slicer {ref[-1]}")

    def chart(self, vtype, x, y, w, h, title, category=None, series=None, values=(), sort=None, objects=None, filters=None,
              title_measure=None, tooltip_page=None, subtitle=None, label=None):
        cats = list(category) if isinstance(category, list) else ([category] if category else [])
        b = {"Category": cats, "Series": [series] if series else [], "Y": list(values)}
        return self.add(vtype, x, y, w, h, q=query(b, sort), objects=objects,
                        container=vco(title=title, title_measure=title_measure, tooltip_page=tooltip_page, subtitle=subtitle),
                        filters=filters, label=label or f"{vtype} {title}")

    def donut(self, x, y, w, h, title, category, value, colors=None, label=None):
        o = {"legend": [{"properties": {"show": lit(True), "position": lit("Bottom"), "fontSize": num(9), "labelColor": colr(TEXT)}}],
             "labels": [{"properties": {"show": lit(True), "fontSize": num(10), "color": colr(TEXT), "labelStyle": lit("Percent of total")}}],
             "slices": [{"properties": {"innerRadiusRatio": num(60)}}]}
        if colors:
            o["dataPoint"] = dp_colors(category[1], category[2], colors)
        return self.add("donutChart", x, y, w, h, q=query({"Category": [category], "Y": [value]}), objects=o,
                        container=vco(title=title), label=label or f"donut {title}")

    def table(self, x, y, w, h, title, cols, sort=None, filters=None, objects_extra=None, label=None, size=10, subtitle=None, title_measure=None):
        o = {"columnHeaders": [{"properties": {"fontColor": colr(WHITE), "backColor": colr(NAVY), "fontSize": num(size),
                                               "bold": lit(True), "fontFamily": lit(FONT)}}],
             "values": [{"properties": {"fontSize": num(size), "fontColor": colr(TEXT), "backColorPrimary": colr(WHITE),
                                        "backColorSecondary": colr("#F3F7FC"), "fontFamily": lit(FONT)}}],
             "grid": [{"properties": {"outlineColor": colr(GRID), "gridVertical": lit(False), "rowPadding": num(4)}}]}
        if objects_extra:
            o.update(objects_extra)
        return self.add("tableEx", x, y, w, h, q=query({"Values": cols}, sort), objects=o,
                        container=vco(title=title, subtitle=subtitle, title_measure=title_measure), filters=filters, label=label or f"table {title}")

    def matrix(self, x, y, w, h, title, rows, columns, values, sort=None, label=None, size=10, objects_extra=None):
        o = {"columnHeaders": [{"properties": {"fontColor": colr(WHITE), "backColor": colr(NAVY), "fontSize": num(size),
                                               "bold": lit(True), "fontFamily": lit(FONT)}}],
             "rowHeaders": [{"properties": {"fontColor": colr(TEXT), "fontSize": num(size), "fontFamily": lit(FONT)}}],
             "values": [{"properties": {"fontSize": num(size), "fontColor": colr(TEXT), "backColorPrimary": colr(WHITE),
                                        "backColorSecondary": colr("#F3F7FC"), "fontFamily": lit(FONT)}}],
             "grid": [{"properties": {"outlineColor": colr(GRID), "rowPadding": num(4)}}]}
        if objects_extra:
            o.update(objects_extra)
        return self.add("pivotTable", x, y, w, h, q=query({"Rows": rows, "Columns": columns, "Values": values}, sort), objects=o,
                        container=vco(title=title), label=label or f"matrix {title}")

    def image(self, x, y, w, h, title, resource, label=None):
        o = {"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                                                         "ItemName": resource}}}}}],
             "imageScaling": [{"properties": {"imageScalingType": lit("Fit")}}]}
        return self.add("image", x, y, w, h, objects=o, container=vco(title=title), label=label or f"image {resource}")

    def page_navigator(self, x, y, w, h):
        def st(sel, fill, fc=WHITE, bold=False):
            return sel, fill, fc, bold
        states = [("default", HEADER_DARK, "#C9D9F0"), ("hover", "#24508F", WHITE), ("selected", BLUE, WHITE)]
        o = {
            "text": [{"properties": {"fontColor": colr(fc), "fontSize": num(9), "bold": lit(sel == "selected"), "fontFamily": lit(FONT)},
                      "selector": {"id": sel}} for sel, _, fc in states],
            "fill": [{"properties": {"show": lit(True), "fillColor": colr(f), "transparency": num(0)}, "selector": {"id": sel}}
                     for sel, f, _ in states],
            "outline": [{"properties": {"show": lit(False)}, "selector": {"id": sel}} for sel, _, _ in states],
            "shape": [{"properties": {"roundEdge": num(6)}}],
        }
        return self.add("pageNavigator", x, y, w, h, objects=o, container=vco(bg=None, border=None, shadow=False), label="page navigator")

    # -- serialisation --
    def page_json(self):
        d = {"$schema": S_PAGE, "name": self.id, "displayName": self.title,
             "displayOption": "ActualSize" if self.kind == "tooltip" else "FitToPage",
             "height": self.h, "width": self.w,
             "objects": {"background": [{"properties": {"color": colr(self.bg), "transparency": num(0)}}]}}
        if self.kind == "tooltip":
            d["type"] = "Tooltip"
        if self.hidden:
            d["visibility"] = "HiddenInViewMode"
        if self.filters:
            d["filterConfig"] = {"filters": self.filters}
        if self.binding:
            d["pageBinding"] = self.binding
        return d


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
