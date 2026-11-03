# Beyond the Boarding Pass: Uncovering the Key Drivers of Airline Passenger Satisfaction

**An Explainable AI-powered Airline Passenger Satisfaction Analytics and Decision-Support System**

## Overview

Airlines collect extensive passenger feedback about service quality, flight experience, operational efficiency and customer preferences. However, identifying which specific factors contribute most significantly to overall passenger satisfaction remains a challenge.

**Beyond the Boarding Pass** aims to analyze airline passenger satisfaction data, identify the key drivers influencing customer experience, and communicate meaningful insights through Explainable AI, Generative AI and interactive data visualization.

The project integrates **SHAP (SHapley Additive exPlanations)** for feature contribution analysis, **Google Gemini API** for generating human-readable explanations, and **Microsoft Power BI** for developing an interactive analytical dashboard.

Our goal is to bridge the gap between machine learning outputs and actionable business insights, helping airlines make informed, data-driven decisions to improve passenger experiences.

---

## Problem Statement

Airlines collect large volumes of passenger feedback on various service attributes, including seat comfort, in-flight entertainment, Wi-Fi connectivity, food quality and flight delays.

However, understanding which factors have the greatest influence on passenger satisfaction and translating these findings into actionable improvements can be challenging.

This project addresses this problem by analyzing passenger satisfaction data, identifying influential features, explaining their contributions using Explainable AI, and presenting the findings through an interactive dashboard.

---

## Project Objectives

- Analyze airline passenger satisfaction data to discover meaningful patterns.
- Identify and rank the primary features influencing passenger satisfaction.
- Categorize passenger satisfaction into three levels: **Low, Average and High**.
- Apply SHAP to interpret feature contributions and explain model predictions.
- Integrate the Google Gemini API to convert technical SHAP outputs into understandable natural-language explanations.
- Develop an interactive Power BI dashboard for exploring passenger satisfaction patterns.
- Provide data-driven insights that can support airline service improvement decisions.

---

## Dataset

**Dataset:** Airline Passenger Satisfaction

**Source:** Kaggle

**Format:** CSV

**Dataset link:** https://www.kaggle.com/datasets/mysarahmadbhat/airline-passenger-satisfaction

### Dataset Statistics

| Attribute | Details |
|---|---|
| Total records | 129,880 |
| Training records | 103,904 |
| Testing records | 25,976 |
| Target variable | Satisfaction |
| Data format | CSV |

### Important Features

The dataset contains passenger demographics, flight information and service quality ratings.

**1. Passenger Attributes**
- Gender
- Age
- Customer Type

**2. Flight Attributes**
- Flight Class
- Type of Travel
- Flight Distance

**3. Operational Attributes**
- Departure Delay
- Arrival Delay

**4. Service Quality Attributes**
- Inflight Wi-Fi Service
- Online Boarding
- Seat Comfort
- Food and Drink
- Inflight Entertainment
- Leg Room Service
- Baggage Handling
- Check-in Service
- On-board Service
- Cleanliness

**Target Variable:** Satisfaction

The project proposes categorizing passenger experiences into three levels:

- Low Satisfaction
- Average Satisfaction
- High Satisfaction

---

## 🏗️ Proposed System Architecture

The project follows a sequential analytical pipeline:

```text
       Airline Passenger Dataset
               (Kaggle CSV)
                    |
                    v
           Data Preprocessing
          (Python, Pandas, NumPy)
                    |
                    v
        Satisfaction Categorization
             Low / Average / High
                    |
                    v
       Feature Identification & ML
       Identify Important Features
                    |
                    v
          Explainable AI (SHAP)
        Feature Contribution Analysis
                    |
                    v
              Gemini API
       Natural Language Explanations
                    |
                    v
          Power BI Dashboard
       Interactive Data Visualization
                    |
                    v
          Actionable Business Insights
```

---

## ⚙️ Methodology

### 1. Data Preprocessing

The airline passenger dataset is processed using Python.

Planned preprocessing operations include:

- Handling missing values.
- Identifying and handling duplicate records.
- Encoding categorical variables.
- Preparing numerical features.
- Preparing training and testing datasets.

**Libraries:** Pandas, NumPy and Scikit-learn.

### 2. Satisfaction Categorization

Passenger satisfaction is categorized into three levels:

- Low
- Average
- High

The categorization is based on passenger service-rating scores.

This provides a more granular perspective on passenger experiences compared with a simple binary satisfaction classification.

### 3. Feature Identification and Machine Learning

Machine learning techniques are used to analyze passenger satisfaction and identify influential features.

The analysis focuses on understanding the relationship between passenger attributes, service quality and satisfaction levels.

### 4. Explainable AI using SHAP

SHAP is integrated to understand how individual features contribute to model predictions.

It helps identify:

- Features with significant contributions.
- Positive and negative feature contributions.
- Relative importance of passenger experience attributes.
- How individual features influence specific predictions.

The objective is to make machine learning predictions more transparent and interpretable.

### 5. Gemini API Integration

The Google Gemini API is used to convert technical SHAP outputs into understandable natural-language explanations.

For example, instead of presenting only numerical feature contributions, the system aims to generate explanations describing how seat comfort, Wi-Fi service or flight delays influence the model's satisfaction predictions.

This makes analytical findings more accessible to non-technical users and decision-makers.

### 6. Interactive Power BI Dashboard

Microsoft Power BI is used to develop an interactive dashboard for exploring passenger satisfaction.

The proposed dashboard will incorporate:

- Key Performance Indicators (KPIs).
- Satisfaction distribution visualizations.
- Feature importance analysis.
- Comparisons across passenger segments.
- Service quality analysis.
- Interactive filters and visual exploration.

The dashboard aims to transform analytical results into meaningful visual insights.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Data processing and machine learning |
| Pandas | Data manipulation |
| NumPy | Numerical computations |
| Scikit-learn | Machine learning and preprocessing |
| SHAP | Explainable AI and feature attribution |
| Google Gemini API | Natural-language explanation generation |
| Microsoft Power BI | Interactive dashboards and visual analytics |
| Kaggle | Dataset source |

---

## 🔍 Research Background

The project is supported by research in four major areas:

**1. Predictive Models with XAI: A Comparative Study of Enhancing Airline Customer Satisfaction (2023)**

Authors: Cloë C. E. van Geest, Yong Wan Yit, Zaur T. Gouliev and Keith Quille.

This research compares Blackbox and Glassbox machine learning models and explores LIME and SHAP for explaining airline passenger satisfaction predictions.

DOI: https://doi.org/10.1145/3633083.3633189

**2. Data Visualization Analysis Based on Airline Passenger Satisfaction Experience (2025)**

Authors: Xiucui Wang and Menchita Falcutila Dumlao.

Explores visualization techniques for analyzing passenger satisfaction patterns.

DOI: https://doi.org/10.1145/3746709.3746970

**3. Task-Based Effectiveness of Basic Visualizations (2019)**

Authors: Bahador Saket, Alex Endert and Çağatay Demiralp.

Provides insights into the effectiveness of different visualization techniques for analytical tasks.

DOI: https://doi.org/10.1109/TVCG.2018.2829750

**4. Narrative Visualization: Telling Stories with Data (2010)**

Authors: Edward Segel and Jeffrey Heer.

Explores how data visualization, storytelling, annotations and layout can communicate analytical findings effectively.

Link: https://ieeexplore.ieee.org/document/5613452/

---

## Expected Outcomes

The project aims to deliver:

- Identification of the most influential passenger satisfaction factors.
- Three-level passenger satisfaction analysis.
- Explainable machine learning predictions using SHAP.
- AI-generated natural-language explanations using Gemini.
- An interactive Power BI dashboard.
- Data-driven insights to support airline service improvement decisions.

---

## Future Scope

Potential extensions include:

- Incorporating additional passenger feedback and sentiment analysis.
- Exploring advanced machine learning and ensemble techniques.
- Integrating real-time passenger feedback.
- Developing personalized passenger experience recommendations.
- Extending the dashboard with more detailed passenger segmentation.
- Exploring predictive service improvement strategies.

---

## Project Team

**Team 11 — VDUI Mini Project**

| Team Member | University ID |
|---|---|
| Nandita N. Patil | PES2UG24CS304 |
| Nandika Gupta | PES2UG24CS303 |
| B. Anusha | PES2UG24CS676 |
| Nisarga Goudar | PES2UG24CS643 |

**Institution:** PES University

**Course:** Data Visualization, Understanding and Interpretation (VDUI)

---

## Project Status

Currently under development.

The proposed implementation includes data preprocessing, satisfaction categorization, machine learning, SHAP-based explainability, Gemini API integration and Power BI dashboard development.

---

## Key Idea

**From passenger data to explainable insights.**

By combining Explainable AI, Generative AI and interactive data visualization, Beyond the Boarding Pass aims to help airlines move beyond simply measuring passenger satisfaction towards understanding the factors that shape it and making more informed service improvement decisions.
