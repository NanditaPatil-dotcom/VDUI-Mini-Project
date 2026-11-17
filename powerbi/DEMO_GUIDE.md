# Demo guide – drill-down, drill-up, drill-through and Back (Team11_Final)

Open `Team11_Final.pbix` in Power BI Desktop. Use the **page tabs at the bottom** to change pages.
In Desktop, report buttons (including Back) work with **Ctrl + Click**; in the Power BI Service or Reading view a plain click is enough.
**I could not run Power BI Desktop, so rehearse this once before the demo.** If a step behaves differently, send me the step number.

## A. Drill-down and drill-up (inside one chart)
Page: **EDA & PASSENGER ANALYSIS** (second tab). Chart: top-left, titled *"Satisfaction by Travel Class | DRILL DOWN: Class > Type of Travel"*.
1. Point at the chart. A row of small icons appears above its top-right corner. From the left they are:
   **Drill up (↑)**, **Drill down mode (single ↓)**, **Go to the next level (double ↓)**, **Expand all down one level (forked ↓)**.
2. Click the single **↓ (Drill down mode)**. It turns dark = ON.
3. Click the **Business** column. The chart now shows only Business split by **Type of Travel** (Business travel / Personal travel).
4. **Drill up:** click the **↑ (Drill up)** icon, top-left of that icon row. The chart returns to the original Class level (Business, Economy, Economy Plus).
5. Optional one-click version: click **Go to the next level (double ↓)** – all classes split by Type of Travel at once; click **↑** to return.
6. Turn drill mode OFF by clicking the single ↓ again (needed before step B2, so a click selects a bar instead of drilling).

## B. Drill-through to Passenger Segment Detail, then Back (filters preserved)
Start on **EDA & PASSENGER ANALYSIS**, chart at the Class level (finish step A.4 first).
1. In the right-hand **Gender** list click **Female**. The cards and charts update (this proves the filter is carried across).
2. **Right-click the "Economy" column** in the Satisfaction-by-Travel-Class chart.
3. In the menu choose **Drill through → Passenger Segment Detail**.
4. The page **Passenger Segment Detail** opens (navy title bar; amber **← BACK** button at the far left of the title bar). The KPI cards, the table and the rating chart are now filtered to **Economy + Female**.
5. Click the amber **← BACK** button (Ctrl + Click in Desktop). You return to **EDA & PASSENGER ANALYSIS** with Female still selected and the chart as you left it.
6. Repeat from a different bar (e.g. Business) to show the page re-filters. After drilling down (A.3) you can also right-click a *Type of Travel* column and drill through the same way.
Note: in Desktop the drill-through page shows a crossed-eye icon in its tab = it is a hidden page; viewers of the published report do not see that tab.

## C. AI Explainability – changing `row_index`
Page: **AI EXPLAINABILITY**. In the `row_index` list (right column) click:
* **2884** → predicted *Neutral or Dissatisfied*, probability 99.88 %, one recommendation row, matching Gemini text and SHAP bars.
* **76523** → predicted *Satisfied*, probability 99.95 %, two recommendation rows.
The individual SHAP bars, probability card, predicted / actual class, Gemini explanation and recommendations all follow the selection.

## D. Overview check
Page **OVERVIEW**: with no slicer selected, **Total Passengers = 129,487** (also confirmed in `validation_report.md`). Click Gender / Class / Customer Type / Type of Travel in the right column: cards and the donut change; the Top-5 SHAP chart does not (it is model-level data).
