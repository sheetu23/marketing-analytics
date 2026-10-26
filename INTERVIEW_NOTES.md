# Technical Interview Preparation Guide: Marketing Analytics

This document is tailored for technical interviews (Data Engineering, Analytics Engineering, Python Developer roles). It details the architectural rationale for every project file and provides defensible, honest answers to 12 likely interview questions.

---

## 1. File-by-File Breakdown: "What It Does" & "How It Works"

### `clean.py`
- **What it does**: Audits dataset quality, preserves missing values via domain categories, converts the target to boolean, and creates demographic age buckets.
- **How it works**:
  1. Reads `bank-full.csv` using `pd.read_csv` with `sep=';'` and cleans column names using regex snake_case conversion.
  2. Maps the `'y'` target column to a native Python boolean `converted` (`True`/`False`) and retains `'unknown'` as valid categorical strings.
  3. Discretizes continuous customer age into 6 standardized cohorts (`18-25` to `65+`) using `pd.cut` and exports `get_clean_data()`.

### `load_to_mongo.py`
- **What it does**: Ingests cleaned DataFrame records into MongoDB using idempotent chunked batch insertion and creates analytical B-tree indexes.
- **How it works**:
  1. Pulls database credentials from `.env` and drops the existing `bank_campaigns` collection to enforce deterministic idempotency.
  2. Chunks 45,211 dictionaries into batches of 5,000 documents via `insert_many(ordered=True)` to maximize socket throughput.
  3. Builds single-field B-tree indexes on `job`, `contact`, `month`, `age_bucket`, and `converted`, then verifies data integrity with `assert count == 45211`.

### `queries.py`
- **What it does**: Executes production MongoDB aggregation pipelines for demographic rates, `$lookup` calendar joins, and `$facet` proxy funnels.
- **How it works**:
  1. Populates an auxiliary `month_order` collection with numerical month indices (1..12) and performs `$lookup` joins to sort months chronologically.
  2. Implements `$match -> $group -> $project -> $sort` pipelines to compute conversion rates rounded to 2 decimal places.
  3. Calculates median call duration (180s) in Python and passes it to a multi-branch `$facet` pipeline, exporting all results to `outputs/*.csv`.

### `docker-compose.yml`
- **What it does**: Declaratively provisions and networks MongoDB and Metabase services with persistent storage volumes.
- **How it works**:
  1. Pulls official images `mongo:latest` and `metabase/metabase:latest`, binding host ports 27017 and 3000.
  2. Creates an isolated bridge network (`marketing_net`) enabling Metabase to resolve MongoDB using the container service name `mongo`.
  3. Mounts named Docker volumes `mongo_data` (`/data/db`) and `metabase_data` (`/metabase-data`) so dashboards and databases persist across restarts.

### `requirements.txt`
- **What it does**: Locks the minimal external Python libraries required for data manipulation, database communication, and environment loading.
- **How it works**:
  1. Specifies `pandas>=2.0.0` for tabular data quality verification, type conversions, and demographic binning.
  2. Declares `pymongo>=4.6.0` to communicate with MongoDB and compile aggregation pipeline payloads.
  3. Includes `python-dotenv>=1.0.0` to parse configuration variables from `.env` files dynamically at runtime.

### `.env.example`
- **What it does**: Provides a version-controlled configuration template for connecting to MongoDB across different deployment environments.
- **How it works**:
  1. Documents required environment keys: `MONGO_URI`, `DB_NAME`, and `COLLECTION_NAME`.
  2. Follows 12-Factor App design by separating infrastructure connection strings from application logic.
  3. Demonstrates how hostnames differ when connecting from the host OS (`localhost:27017`) versus inside Docker (`mongo:27017`).

### `.gitignore`
- **What it does**: Restricts sensitive environment secrets, bulky datasets, virtual environments, and compiler caches from being committed to Git.
- **How it works**:
  1. Masks the `data/` directory to prevent large raw CSV files from bloating the Git history.
  2. Blocks active `.env` files to prevent database connection credentials from leaking into public repositories.
  3. Filters out `venv/`, Python bytecode (`__pycache__/`), and local standalone Metabase database artifacts.

### `metabase_questions.md`
- **What it does**: Provides complete setup steps and pre-tested native MongoDB aggregation JSON queries for 8 charts across 3 dashboards.
- **How it works**:
  1. Details initial Metabase admin creation and MongoDB database connection settings (host, port, auth).
  2. Outlines exact aggregation JSON arrays for the Conversion Funnel, Campaign Performance, and Segment KPI dashboards.
  3. Specifies visual chart mappings (X/Y axes, percentage formatting, metric cards) and lists target screenshot filenames.

### `README.md`
- **What it does**: Serves as the executive summary, architecture guide, and analytical findings report for the entire project.
- **How it works**:
  1. Details the business problem statement and outlines the ASCII data pipeline architecture from CSV to Metabase.
  2. Summarizes verified findings (e.g., Senior 42.61% conversion, March 51.99% peak) taken strictly from real outputs.
  3. Transparently documents technical limitations (proxy funnel, duration leakage, NoSQL vs. SQL engineering trade-offs).

---

## 2. 12 High-Yield Interview Questions & Honest Answers

### Q1: Why did you use MongoDB instead of a relational SQL database for tabular data?
> **Honest Answer**:  
> "In a strict production environment, **PostgreSQL or Snowflake would be the primary choice** because tabular campaign data has a fixed schema and naturally benefits from relational joins and window functions.  
> However, I chose MongoDB specifically to master the **MongoDB Aggregation Framework** (`$group`, `$lookup`, `$facet`, `$project`). It allowed me to demonstrate how complex analytical queries, schema transformations, and cross-collection joins are performed in document databases when organizations use MongoDB as an operational data store."

### Q2: Why did you keep 'unknown' as its own category instead of dropping or imputing rows?
> **Answer**:  
> "In data cleaning, missing values often convey distinct domain information—referred to as **informative missingness**.  
> In this dataset, over **81.75% of `poutcome` (previous campaign outcome)** and **28.80% of `contact` (communication channel)** are `'unknown'`. Dropping rows containing `'unknown'` would have eliminated over 80% of the dataset, destroying statistical power and introducing severe survivorship bias. Imputing with the mode would have artificially skewed data distributions. Retaining `'unknown'` as an explicit category revealed a crucial business insight: prospects with unknown channels converted at only 4.07% vs. 14.92% for cellular."

### Q3: What is a "proxy funnel" and why was it necessary?
> **Answer**:  
> "A true marketing funnel tracks sequential micro-events in real time (e.g., *Impression → Ad Click → Landing Page View → Form Fill → Won*).  
> The UCI dataset is a retrospective tabular snapshot without session-level event tracking. To analyze pipeline drop-off, I constructed an operational **proxy funnel** modeling customer engagement:  
> 1. *All Contacted* (45,211) →  
> 2. *Engaged Call* (> median duration 180s: 22,551) →  
> 3. *Follow-up Nurtured* (engaged + campaign contacts > 1: 13,341) →  
> 4. *Converted* (2,424).  
> It reveals that the biggest friction point is the opening call hook: **50.12% drop off before reaching the median call duration**."

### Q4: How does `$lookup` work in your monthly query and what are its trade-offs?
> **Answer**:  
> "In the raw dataset, months are stored as lowercase strings (`'jan'`, `'may'`, `'dec'`). A standard `$sort` orders them alphabetically, which breaks time-series dashboards.  
> To solve this, I created an auxiliary collection `month_order` containing `{ month: 'jan', month_num: 1 }`. In `queries.py`, after grouping by month, I added a `$lookup` stage that acts as a left outer join on `_id == month_order.month`, followed by `$unwind` to flatten the array, and `$sort: { 'month_info.month_num': 1 }`.  
> **Trade-off**: `$lookup` requires MongoDB to scan or index another collection. In large-scale NoSQL, joins are computationally expensive; if this were high-frequency production, I would embed `month_num` directly into the document during ingestion."

### Q5: How did you make the ingestion pipeline idempotent and why does idempotency matter?
> **Answer**:  
> "Idempotency means that executing a pipeline multiple times produces the identical end state without duplicating data or creating side effects.  
> In `load_to_mongo.py`, before inserting records, I call `collection.drop()`. If a network glitch occurs or an engineer re-runs the loader, the collection is wiped and rebuilt cleanly. Furthermore, I assert that `collection.count_documents({}) == 45211`. Without idempotency, rerunning the script would insert duplicate records, corrupting all conversion metrics."

### Q6: How would you write these aggregation queries in standard SQL?
> **Answer**:  
> "In SQL, the conversion rate by age bucket and monthly calendar order would look like this:"
```sql
-- Conversion Rate by Demographic Age Bucket
SELECT 
    age_bucket,
    COUNT(*) AS total_clients,
    SUM(CASE WHEN converted THEN 1 ELSE 0 END) AS conversions,
    ROUND(SUM(CASE WHEN converted THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS conversion_rate
FROM bank_campaigns
GROUP BY age_bucket
ORDER BY conversion_rate DESC;

-- Monthly Conversion Rate in Calendar Order
SELECT 
    m.month_num,
    m.month_name,
    COUNT(c.client_id) AS total_clients,
    SUM(CASE WHEN c.converted THEN 1 ELSE 0 END) AS conversions,
    ROUND(SUM(CASE WHEN c.converted THEN 1.0 ELSE 0.0 END) / COUNT(c.client_id) * 100, 2) AS conversion_rate
FROM bank_campaigns c
JOIN month_order m ON c.month = m.month
GROUP BY m.month_num, m.month_name
ORDER BY m.month_num ASC;
```

### Q7: What is the single biggest business insight you uncovered?
> **Answer**:  
> "**Severe resource misallocation between campaign volume and conversion receptivity.**  
> - **Seasonally**: May was flooded with the largest outreach volume (**13,766 contacts**, 30.4% of all calls), yet achieved a dismal **6.72% conversion rate**. In contrast, March yielded a **51.99% conversion rate** (248/477), and October yielded **43.77%** (323/738).  
> - **Demographically**: The bank targeted blue-collar workers most heavily (9,732 contacts), yet they had the lowest conversion rate of any job (7.27%). Meanwhile, retirees (22.79%) and students (28.68%) had 3x higher conversion rates.  
> **Recommendation**: Reallocate outreach budget from May to Q1/Q4, and pivot sales capacity toward wealth-preservation segments."

### Q8: Why can't the `duration` column be used for predictive modeling?
> **Answer**:  
> "Because of **target leakage** (data leakage).  
> The duration of a call is unknown before the call begins. A client who says 'yes' to a term deposit naturally spends 10 to 20 minutes discussing terms, signing paperwork, and confirming bank details, whereas an uninterested client hangs up in 15 seconds. High duration is a *symptom* of conversion, not a predictive cause. If an ML model trained on `duration`, it would have near-perfect accuracy in validation but would fail completely in real-time scoring before dialing."

### Q9: How did you handle batching during insertion and why 5,000 documents per batch?
> **Answer**:  
> "Inserting 45,211 documents individually via `insert_one` would require 45,211 TCP network round trips, which takes upwards of 30–60 seconds.  
> Conversely, attempting to insert all 45,211 documents in a single payload could risk exceeding MongoDB's 16MB BSON wire protocol message limit and spikes RAM usage. Chunks of **5,000 documents** balance TCP packet sizes, memory consumption, and network efficiency, loading all records in under **2.5 seconds**."

### Q10: Why did you create indexes after insertion rather than before?
> **Answer**:  
> "When documents are inserted into an indexed collection, the database engine must recalculate and update the B-tree index structures on disk for *every single document inserted*.  
> By inserting data into an unindexed collection first, MongoDB performs pure append writes. Once the data is completely loaded, calling `create_index` builds the entire B-tree in a single optimized bulk operation. In production ETL pipelines, dropping indexes before bulk load and rebuilding them post-load is a standard performance optimization."

### Q11: What are the key limitations of this dataset and analysis?
> **Answer**:  
> "1. **Lack of Economic Indicators**: The dataset does not include macroeconomic variables (interest rate shifts, GDP growth, inflation) that strongly influence term deposit attractiveness.  
> 2. **Historical Telemarketing Bias**: The data reflects outbound phone campaigns from the 2008–2010 era. Modern customers rarely answer unsolicited cold calls, so findings must be translated into multi-channel digital campaigns (email, SMS, app push).  
> 3. **Non-Granular Funnel**: We had to construct a proxy funnel using duration and contact frequency rather than true timestamped event logs."

### Q12: If you had another sprint, what would you improve or build next?
> **Answer**:  
> "1. **Real-Time Streaming / Change Streams**: Implement MongoDB Change Streams (`watch()`) to push real-time campaign conversions to a dashboard without batch reloads.  
> 2. **Propensity Scoring ML Service**: Build a scikit-learn classifier (Random Forest / XGBoost) trained strictly on pre-call features (`age`, `job`, `balance`, `housing`, `poutcome`) to generate lead propensity scores before call dispatch.  
> 3. **Automated Docker Healthchecks**: Add healthcheck probes and migration scripts in `docker-compose.yml` so Metabase automatically waits for MongoDB's ready state before initializing."
