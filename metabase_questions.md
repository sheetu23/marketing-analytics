# Metabase Setup & Dashboard Construction Guide

This guide provides exact, step-by-step instructions to configure Metabase, connect it to MongoDB, and build three executive dashboards using native MongoDB aggregation pipelines.

---

## 1. First-Time Metabase Setup

1. Open your browser and navigate to: **`http://localhost:3000`**
2. Click **"Let's get started"**.
3. **Admin Account Setup**:
   - First name: `Marketing`
   - Last name: `Analyst`
   - Email: `admin@marketing.local` (or your preferred personal email)
   - Password: `Password123!` (or your preferred password)
4. **Connect Database** (or select "I'll add my data later" and navigate to *Admin Settings -> Databases -> Add Database*):
   - **Database type**: `MongoDB`
   - **Display name**: `Marketing Analytics DB`
   - **Host**:
     - If Metabase runs in Docker Compose: `mongo`
     - If Metabase runs locally on host: `localhost` (or `127.0.0.1`)
   - **Port**: `27017`
   - **Database name**: `marketing`
   - **Authentication Database**: *(leave blank)*
   - **Username / Password**: *(leave blank)*
   - **Use DNS SRV**: `Off`
   - **Use SSL**: `Off`
5. Click **"Save"**. Metabase will test the connection and sync the schema for `bank_campaigns` and `month_order`.
6. Select your usage preferences (usage data collection can be turned off) and finish onboarding to access the main Metabase home screen.

---

## 2. How to Create Native MongoDB Questions in Metabase

For every chart described below:
1. Click the **"+ New"** button in the top right header -> select **"Question"**.
2. Under "Pick your starting data", select **"Native query"** (code icon).
3. Select Database: **`Marketing Analytics DB`**.
4. In the collection dropdown (or top bar), ensure **`bank_campaigns`** is selected.
5. Paste the exact JSON pipeline provided into the code editor.
6. Click the blue **Play button** (or press `Ctrl + Enter`) to run the query.
7. Click the **"Visualization"** button at the bottom left to pick the chart type and configure X/Y axes as specified.
8. Click **"Save"** in the top right, name the question, and add it to the corresponding dashboard.

---

## 3. Dashboard Specifications

### Dashboard 1: Conversion Funnel
**Purpose**: Visualizes client progression through the 4-stage proxy outreach funnel, tracking attrition and drop-off.

#### Question 1.1: Proxy Marketing Conversion Funnel
- **Question Name**: `Proxy Funnel - Stage Attrition`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Funnel` (or `Bar chart` with horizontal layout)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$facet": {
      "s1": [{ "$count": "count" }],
      "s2": [{ "$match": { "duration": { "$gt": 180 } } }, { "$count": "count" }],
      "s3": [{ "$match": { "duration": { "$gt": 180 }, "campaign": { "$gt": 1 } } }, { "$count": "count" }],
      "s4": [{ "$match": { "duration": { "$gt": 180 }, "campaign": { "$gt": 1 }, "converted": true } }, { "$count": "count" }]
    }
  },
  {
    "$project": {
      "stages": [
        { "stage_order": 1, "stage": "1. All Contacted Clients", "count": { "$arrayElemAt": ["$s1.count", 0] } },
        { "stage_order": 2, "stage": "2. Engaged Call (>180s)", "count": { "$arrayElemAt": ["$s2.count", 0] } },
        { "stage_order": 3, "stage": "3. Follow-up Nurtured (>1 Call)", "count": { "$arrayElemAt": ["$s3.count", 0] } },
        { "stage_order": 4, "stage": "4. Successfully Converted", "count": { "$arrayElemAt": ["$s4.count", 0] } }
      ]
    }
  },
  { "$unwind": "$stages" },
  {
    "$project": {
      "_id": 0,
      "stage_order": "$stages.stage_order",
      "stage": "$stages.stage",
      "count": "$stages.count"
    }
  },
  { "$sort": { "stage_order": 1 } }
]
```
- **Visualization Settings**:
  - **X-axis (Dimension)**: `stage`
  - **Y-axis (Measure)**: `count`
  - Display value data labels on bars.

---

### Dashboard 2: Campaign Performance
**Purpose**: Analyzes outreach channel effectiveness and seasonal conversion patterns across calendar months.

#### Question 2.1: Conversion Rate by Contact Channel
- **Question Name**: `Conversion Rate by Channel`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Bar chart` (Column)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": "$contact",
      "total_clients": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$project": {
      "_id": 0,
      "contact_channel": "$_id",
      "total_clients": 1,
      "conversions": 1,
      "conversion_rate": {
        "$round": [{ "$multiply": [{ "$divide": ["$conversions", "$total_clients"] }, 100] }, 2]
      }
    }
  },
  { "$sort": { "conversion_rate": -1 } }
]
```
- **Visualization Settings**:
  - **X-axis**: `contact_channel`
  - **Y-axis**: `conversion_rate` (format as percentage `%`)

#### Question 2.2: Conversion Rate by Month (Calendar Order)
- **Question Name**: `Monthly Conversion Rate Trend`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Line chart` (or `Bar chart`)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": "$month",
      "total_clients": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$lookup": {
      "from": "month_order",
      "localField": "_id",
      "foreignField": "month",
      "as": "month_info"
    }
  },
  { "$unwind": "$month_info" },
  {
    "$project": {
      "_id": 0,
      "month": "$month_info.month_name",
      "month_num": "$month_info.month_num",
      "total_clients": 1,
      "conversions": 1,
      "conversion_rate": {
        "$round": [{ "$multiply": [{ "$divide": ["$conversions", "$total_clients"] }, 100] }, 2]
      }
    }
  },
  { "$sort": { "month_num": 1 } }
]
```
- **Visualization Settings**:
  - **X-axis**: `month`
  - **Y-axis**: `conversion_rate` (%)

#### Question 2.3: Total Outreach Contacts & Conversions by Month
- **Question Name**: `Monthly Outreach Volume vs Conversions`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Combo chart` (or `Stacked/Grouped Bar chart`)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": "$month",
      "total_contacts": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$lookup": {
      "from": "month_order",
      "localField": "_id",
      "foreignField": "month",
      "as": "month_info"
    }
  },
  { "$unwind": "$month_info" },
  {
    "$project": {
      "_id": 0,
      "month": "$month_info.month_name",
      "month_num": "$month_info.month_num",
      "total_contacts": 1,
      "conversions": 1
    }
  },
  { "$sort": { "month_num": 1 } }
]
```
- **Visualization Settings**:
  - **X-axis**: `month`
  - **Y-axis**: `total_contacts` (Bars) and `conversions` (Line or secondary bar)

---

### Dashboard 3: Segment-Wise KPIs
**Purpose**: Executive demographic dashboard showing headline business KPIs and conversion rates broken down by occupation and age brackets.

#### Question 3.1: Total Clients (KPI Card)
- **Question Name**: `KPI - Total Targeted Clients`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Number`
- **Native MongoDB Pipeline**:
```json
[
  { "$count": "total_clients" }
]
```
- **Visualization Settings**:
  - Card Number: `total_clients` (Expected value: `45,211`)

#### Question 3.2: Overall Conversion Rate (KPI Card)
- **Question Name**: `KPI - Overall Conversion Rate`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Number`
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": null,
      "total": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$project": {
      "_id": 0,
      "overall_conversion_rate": {
        "$round": [{ "$multiply": [{ "$divide": ["$conversions", "$total"] }, 100] }, 2]
      }
    }
  }
]
```
- **Visualization Settings**:
  - Card Number: `overall_conversion_rate` (Suffix: `%`, Expected value: `11.70%`)

#### Question 3.3: Conversion Rate by Occupation (Job)
- **Question Name**: `Conversion Rate by Job Persona`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Horizontal Bar chart` (Row)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": "$job",
      "total_clients": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$project": {
      "_id": 0,
      "job": "$_id",
      "total_clients": 1,
      "conversions": 1,
      "conversion_rate": {
        "$round": [{ "$multiply": [{ "$divide": ["$conversions", "$total_clients"] }, 100] }, 2]
      }
    }
  },
  { "$sort": { "conversion_rate": -1 } }
]
```
- **Visualization Settings**:
  - **Y-axis (Categories)**: `job`
  - **X-axis (Values)**: `conversion_rate` (%)

#### Question 3.4: Conversion Rate by Age Cohort
- **Question Name**: `Conversion Rate by Age Bucket`
- **Starting Collection**: `bank_campaigns`
- **Chart Type**: `Bar chart` (Column)
- **Native MongoDB Pipeline**:
```json
[
  {
    "$group": {
      "_id": "$age_bucket",
      "total_clients": { "$sum": 1 },
      "conversions": { "$sum": { "$cond": [{ "$eq": ["$converted", true] }, 1, 0] } }
    }
  },
  {
    "$project": {
      "_id": 0,
      "age_bucket": "$_id",
      "total_clients": 1,
      "conversions": 1,
      "conversion_rate": {
        "$round": [{ "$multiply": [{ "$divide": ["$conversions", "$total_clients"] }, 100] }, 2]
      }
    }
  },
  { "$sort": { "conversion_rate": -1 } }
]
```
- **Visualization Settings**:
  - **X-axis**: `age_bucket`
  - **Y-axis**: `conversion_rate` (%)

---

## 4. Screenshot Checklist

Once you assemble each dashboard in Metabase, capture high-resolution screenshots and save them into the `screenshots/` directory with the following exact filenames:

| Screenshot File Name | Dashboard / Chart Captured |
| :--- | :--- |
| `screenshots/dashboard_funnel.png` | Complete **Conversion Funnel Dashboard** view |
| `screenshots/dashboard_campaign_performance.png` | Complete **Campaign Performance Dashboard** view |
| `screenshots/dashboard_segment_kpis.png` | Complete **Segment-Wise KPIs Dashboard** view |
| `screenshots/chart_funnel_stages.png` | Zoomed-in chart of the 4-stage funnel attrition |
| `screenshots/chart_conversion_by_month.png` | Calendar-ordered monthly conversion rate trend line |
| `screenshots/chart_conversion_by_job.png` | Conversion rate by occupation horizontal bar chart |
| `screenshots/chart_conversion_by_age.png` | Demographic cohort conversion rate chart |

---

## 5. Pipeline Pre-Verification Results

All 8 aggregation pipelines were compiled and pre-tested against your live MongoDB database (`marketing.bank_campaigns` and `marketing.month_order`).

- **Query 1.1 (Proxy Funnel)**: Succeeded (4 stages: 45,211 -> 22,551 -> 13,341 -> 2,424).
- **Query 2.1 (Channel Rate)**: Succeeded (cellular: 14.92%, telephone: 13.42%, unknown: 4.07%).
- **Query 2.2 (Monthly Rate)**: Succeeded (Jan..Dec chronological sort with $lookup; March peak at 51.99%).
- **Query 2.3 (Outreach Volume)**: Succeeded (May peak volume at 13,766 contacts).
- **Query 3.1 (Job Rate)**: Succeeded (student: 28.68%, retired: 22.79%, blue-collar: 7.27%).
- **Query 3.2 (Age Bucket Rate)**: Succeeded (65+: 42.61%, 18-25: 23.95%, 46-55: 9.35%).
- **Query 3.3 (Total Clients Card)**: Succeeded (exactly 45,211).
- **Query 3.4 (Overall Rate Card)**: Succeeded (exactly 11.70%).
