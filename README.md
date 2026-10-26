# Marketing Analytics: Bank Campaign Conversion Engine

An end-to-end marketing analytics engineering project analyzing **45,211 customer interactions** from the UCI Bank Marketing direct telemarketing campaigns. Built to demonstrate production-grade data cleaning, idempotent NoSQL database ingestion, complex multi-stage MongoDB aggregation pipelines, and interactive Metabase BI dashboards for marketing budget and channel optimization.

---

## 1. Problem Statement

Retail banking institutions incur massive customer acquisition costs (CAC) executing outbound telemarketing campaigns for long-term deposits. Without quantitative audience segmentation, marketing teams blindly blanket prospects across ineffective communication channels, saturated months, and low-converting demographic groups.

**Objective**:
Build an automated data analytics pipeline that ingests raw telemarketing records, enforces data quality standards, models sales progression through a 4-stage conversion funnel, and computes dimensional conversion rates to guide executive budget allocation and channel strategy.

---

## 2. Dataset Overview

- **Source**: UCI Machine Learning Repository — Bank Marketing Dataset (`bank-full.csv`)
- **Institution**: Portuguese retail bank (direct telephone marketing campaigns)
- **Scale**: 45,211 rows × 17 features
- **Delimiter**: Semicolon (`;`) standard European CSV format
- **Target Variable**: `y` — Has the client subscribed to a term deposit? (`"yes"` / `"no"`)
- **Target Distribution**:
  - Converted (`yes`): **5,289 (11.70%)**
  - Non-Converted (`no`): **39,922 (88.30%)**

---

## 3. Architecture & Data Flow

```text
+-----------------------+
|  data/bank-full.csv   |  <-- Raw UCI Dataset (45,211 rows, sep=';')
+-----------------------+
            |
            v  [clean.py]
+-----------------------+
|    Pandas Pipeline    |  <-- Quality audit, snake_case normalization,
|                       |      boolean conversion, age cohort binning
+-----------------------+
            |
            v  [load_to_mongo.py]
+-----------------------+
|  MongoDB (port 27017) |  <-- Idempotent drop & batch reload (5,000 docs/batch)
|                       |      B-tree indexing: job, contact, month, age_bucket
+-----------------------+
            |
            v  [queries.py]
+-----------------------+
| Aggregation Pipelines |  <-- $match, $group, $project, $facet (funnel),
|   & month_order Join  |      $lookup (calendar month ordering)
+-----------------------+
            |
            +-----------------------------+
            |                             |
            v                             v
+-----------------------+     +-----------------------+
|  outputs/*.csv Files  |     |  Metabase Dashboards  | (port 3000)
| (Reproducible Tables) |     | (Executive BI Charts) |
+-----------------------+     +-----------------------+
```

---

## 4. How to Run the Project

### Prerequisites
- Python 3.10+
- MongoDB (running locally on port 27017 or via Docker Compose)
- Metabase (running locally or via Docker Compose)

### Step 1: Clone Repository & Setup Environment
```bash
git clone <your-repo-url>
cd marketing-analytics

# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows (or: source venv/bin/activate on Linux/macOS)

# Install required dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

### Step 2: Start Infrastructure (Docker or Local)
If using Docker Compose:
```bash
docker compose up -d
```
*Note: If Docker is not installed, verify MongoDB is running locally on port 27017 and launch Metabase via Java (`java -jar metabase.jar`).*

### Step 3: Run the Data Pipeline in Order
```bash
# 1. Clean data, validate quality, and engineer age buckets
python clean.py

# 2. Ingest cleaned records idempotently into MongoDB with B-tree indexes
python load_to_mongo.py

# 3. Execute MongoDB aggregation pipelines, generate CSVs, and output insights
python queries.py
```

### Step 4: Open Metabase Dashboards
Navigate to **`http://localhost:3000`** in your browser. Follow the step-by-step instructions in [`metabase_questions.md`](metabase_questions.md) to connect MongoDB and assemble the 3 dashboards.

---

## 5. Key Findings & Real Analytical Outputs

All figures below are extracted directly from the verified pipeline outputs in [`outputs/`](outputs/):

### A. Demographic Conversion Disparities (Age & Occupation)
- **Senior Cohort (65+)**: Delivers the highest conversion rate across all demographics at **42.61%** (320 conversions / 751 clients).
- **Youth Cohort (18-25)**: Delivers the second highest conversion rate at **23.95%** (320 conversions / 1,336 clients).
- **Prime Working Age (46-55)**: Converts at merely **9.35%** (893 conversions / 9,548 clients).
- **Occupational Efficiency**:
  - **Students (28.68%)** and **Retirees (22.79%)** show over 3x higher conversion efficiency than **Blue-collar workers (7.27%)**.
  - **CAC Leak**: The bank directed its single largest outreach volume (9,732 contacts) toward blue-collar workers, yielding the lowest return.

### B. Channel Effectiveness
- **Cellular**: **14.92%** conversion rate (4,369 conversions / 29,285 contacts).
- **Telephone (Landline)**: **13.42%** conversion rate (390 conversions / 2,906 contacts).
- **Unknown Channel**: **4.07%** conversion rate (530 conversions / 13,020 contacts).
- *Actionable Takeaway*: Unknown channels represent ~29% of outreach but produce less than one-third the conversion rate of mobile contacts.

### C. Seasonal Outreach Misalignment
- **Peak Receptivity Months**:
  - **March**: **51.99%** conversion rate (248 conversions / 477 contacts).
  - **December**: **46.73%** conversion rate (100 conversions / 214 contacts).
  - **September**: **46.46%** conversion rate (269 conversions / 579 contacts).
  - **October**: **43.77%** conversion rate (323 conversions / 738 contacts).
- **Volume vs. Performance Inversion**:
  - **May** experienced massive campaign flooding with **13,766 contacts** (30.4% of total annual outreach), yet resulted in the lowest conversion rate of any high-volume month at **6.72%**.

### D. Proxy Outreach Funnel (Median Duration = 180 seconds)
| Stage Order | Funnel Stage Name | Client Count | % of Initial | Step Retention % | Step Drop-off % |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | All Contacted Clients | **45,211** | 100.00% | 100.00% | 0.00% |
| **2** | Engaged Call (>180s Duration) | **22,551** | 49.88% | 49.88% | **50.12%** |
| **3** | Follow-up Nurtured (Campaign > 1) | **13,341** | 29.51% | 59.16% | **40.84%** |
| **4** | Successfully Converted | **2,424** | 5.36% | 18.17% | **81.83%** |

*Insight*: The largest friction point occurs immediately at Stage 2: **50.12%** of prospects hang up before 3 minutes.

---

## 6. Analytical Limitations & Caveats

1. **Target Leakage Risk in `duration`**:
   The call duration attribute is only known *after* a phone call concludes. It cannot be used as a forward-looking predictive feature in production machine learning because longer duration is a consequence of customer interest, not a prior cause. We restrict its use strictly to retrospective proxy funnel segmentation.
2. **Proxy Funnel Nature**:
   The dataset does not track digital session events (page impressions, cart adds, clicks). Our funnel is an operational sales outreach proxy modeling call duration and multiple contact touches.
3. **Informative Missingness in 'Unknown'**:
   Over 81.75% of previous campaign outcomes (`poutcome`) and 28.80% of contact channels (`contact`) are marked `"unknown"`. Dropping these rows would destroy 80%+ of the dataset and introduce fatal selection bias. They are retained as valid categorical buckets.

---

## 7. Engineering Trade-off: MongoDB vs. SQL in Production

> **Honest Architectural Note**:
> For strictly structured tabular data like `bank-full.csv` with relational dependencies (e.g., calendar lookups), **a relational SQL database (PostgreSQL / Snowflake / BigQuery) is the industry standard choice**. SQL handles joins, window functions, and columnar aggregations natively and efficiently.
>
> In this project, **MongoDB was chosen deliberately to master advanced NoSQL aggregation frameworks**:
> - Multi-stage pipelining (`$match`, `$group`, `$project`, `$sort`)
> - Inter-collection joins via `$lookup` and `$unwind`
> - Multi-branch pipeline processing via `$facet`
> - Document-level B-tree indexing strategies

---

## 8. Metabase Dashboards & Screenshots

Once constructed per [`metabase_questions.md`](metabase_questions.md), dashboards are saved in [`screenshots/`](screenshots/):

| Dashboard | Visual Purpose | Screenshot Reference |
| :--- | :--- | :--- |
| **Conversion Funnel** | Stage-by-stage outreach progression & drop-off | `screenshots/dashboard_funnel.png` |
| **Campaign Performance** | Channel conversion & calendar-ordered monthly trends | `screenshots/dashboard_campaign_performance.png` |
| **Segment-Wise KPIs** | Job persona & age cohort conversion rates | `screenshots/dashboard_segment_kpis.png` |

---

## 9. Project Structure

```text
marketing-analytics/
  ├── data/
  │   └── bank-full.csv            # Cleaned UCI dataset (45,211 rows, uncommitted)
  ├── outputs/
  │   ├── conversion_by_age_bucket.csv
  │   ├── conversion_by_contact.csv
  │   ├── conversion_by_contact_month.csv
  │   ├── conversion_by_job.csv
  │   ├── conversion_by_month.csv
  │   └── funnel.csv
  ├── screenshots/                 # Exported Metabase dashboard visual artifacts
  ├── docker-compose.yml           # Multi-container orchestration (Mongo + Metabase)
  ├── requirements.txt             # Python dependencies (pandas, pymongo, python-dotenv)
  ├── .env.example                 # Environment configuration template
  ├── .gitignore                   # Ignores venv, .env, data/, and caches
  ├── clean.py                     # Data cleaning, quality audit, and feature engineering
  ├── load_to_mongo.py             # Idempotent batch loader with indexing & reconciliation
  ├── queries.py                   # MongoDB aggregation engine & insight generator
  ├── metabase_questions.md        # Exact SQL/MQL queries and BI dashboard setup guide
  ├── README.md                    # Project documentation & business executive report
  └── INTERVIEW_NOTES.md           # Technical interview guide & system design defense
```
