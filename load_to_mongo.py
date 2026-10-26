"""
Marketing Analytics - MongoDB Ingestion Pipeline (load_to_mongo.py)
-------------------------------------------------------------------
Purpose:
    Extracts cleaned campaign data from `clean.py`, connects to MongoDB using
    environment configuration, loads records using chunked batch insertions,
    builds compound/single-field B-tree indexes for analytical performance,
    and reconciles document counts to guarantee zero data loss.

Why this design matters for Interviews:
    1. Idempotency: `collection.drop()` ensures running the script multiple times
       yields identical, deterministic state with no duplicate records.
    2. Batching (5,000 docs/batch): Avoids 45,211 individual network round trips
       while staying well within MongoDB's 16MB BSON wire protocol message limit.
    3. Post-Insert Indexing: Bulk insertion before index building is significantly
       faster than updating B-trees concurrently on every write.
    4. Index Selection: Indexes on `job`, `contact`, `month`, `age_bucket`, and
       `converted` directly optimize the downstream aggregation pipelines ($group, $match).
    5. Reconciliation Assertions: Verifies count == 45,211 to catch silent ingestion errors.
"""

import os
import time
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient, ASCENDING
from clean import get_clean_data


def get_mongo_collection():
    """
    Establishes a MongoClient connection using variables loaded from .env.
    
    Why: Keeps secrets and environment-specific endpoints out of source code.
    Defaults allow seamless fallback for local development.
    """
    # Load environment variables from .env file in project root
    load_dotenv()

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("DB_NAME", "marketing")
    collection_name = os.getenv("COLLECTION_NAME", "bank_campaigns")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    collection = db[collection_name]
    return client, db, collection


def load_data_to_mongo(batch_size: int = 5000):
    """
    Executes the idempotent ingestion pipeline:
      1. Loads clean DataFrame from clean.py
      2. Connects to MongoDB
      3. Drops previous collection (idempotency)
      4. Inserts records in batches of `batch_size`
      5. Creates analytical B-tree indexes
      6. Verifies record count via assertion
    """
    print("=" * 70)
    print(" MARKETING ANALYTICS - MONGODB DATA INGESTION")
    print("=" * 70)

    # 1. Fetch Cleaned DataFrame
    start_time = time.time()
    print("[1] Fetching preprocessed DataFrame from clean.py...")
    df = get_clean_data()
    total_records = len(df)
    print(f"    -> Successfully received {total_records:,} cleaned rows.")

    # Convert DataFrame records to Python dictionaries
    # Why: pymongo expects native Python dicts that it maps directly to BSON documents.
    records = df.to_dict(orient="records")

    # 2. Connect to MongoDB
    print("\n[2] Connecting to MongoDB via environment configuration...")
    client, db, collection = get_mongo_collection()
    # Ping the server to fail fast if MongoDB is unreachable
    client.admin.command("ping")
    print(f"    -> Connected to Database: '{db.name}', Collection: '{collection.name}'")

    # 3. Ensure Idempotency (Drop Collection)
    # Why: If the script is re-run after a pipeline crash or code modification,
    # dropping the collection prevents duplicate entries or stale data.
    print(f"\n[3] Enforcing idempotency: Dropping '{collection.name}' if it exists...")
    collection.drop()
    print("    -> Collection dropped. Clean slate ready.")

    # 4. Batch Insertion
    # Why 5,000 per batch:
    # 45,211 individual `insert_one` calls would require 45,211 network round-trips (~30-60s).
    # Inserting all 45,211 in a single call could exceed socket buffer limits.
    # Batches of 5,000 optimize TCP throughput and RAM usage, completing in < 1 second.
    print(f"\n[4] Ingesting documents in batches of {batch_size:,}...")
    inserted_so_far = 0
    for i in range(0, total_records, batch_size):
        chunk = records[i : i + batch_size]
        result = collection.insert_many(chunk, ordered=True)
        inserted_so_far += len(result.inserted_ids)
        print(f"    - Inserted batch {i // batch_size + 1}: {len(result.inserted_ids):,} docs "
              f"({inserted_so_far:,} / {total_records:,})")

    # 5. Build Analytical Indexes
    # Why after insertion: Building indexes on an existing populated collection is faster
    # because MongoDB creates the B-trees in a single bulk operation, rather than rebalancing
    # the tree on every individual insert.
    # Why these specific fields:
    # - `job`, `contact`, `month`, `age_bucket`: Used as $group / $match grouping keys in aggregation pipelines.
    # - `converted`: Used in target outcome filtering and conditional KPI calculations.
    print("\n[5] Creating B-tree indexes for analytical query acceleration...")
    indexes_to_create = [
        ("job", ASCENDING),
        ("contact", ASCENDING),
        ("month", ASCENDING),
        ("age_bucket", ASCENDING),
        ("converted", ASCENDING),
    ]

    for field, direction in indexes_to_create:
        idx_name = collection.create_index([(field, direction)])
        print(f"    -> Created index on '{field}' (Index Name: {idx_name})")

    # 6. Verification & Reconciliation Assertion
    final_count = collection.count_documents({})
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(" INGESTION RECONCILIATION & INTEGRITY CHECK")
    print("=" * 70)
    print(f"Source DataFrame Records:     {total_records:,}")
    print(f"MongoDB Final Document Count: {final_count:,}")
    print(f"Total Execution Time:         {elapsed:.2f} seconds")

    # Strict interview requirement: Assert document count equals exactly 45,211
    assert final_count == 45211, (
        f"Data reconciliation failed! Expected 45,211 documents, but found {final_count}."
    )
    print("SUCCESS: Count reconciliation assertion PASSED (exactly 45,211 documents).")
    print("=" * 70)

    # Print a sample document from MongoDB to inspect stored schema
    sample_doc = collection.find_one({}, {"_id": 0})
    print("\nSample Ingested Document:")
    for k, v in sample_doc.items():
        print(f"  {k:<15}: {v} ({type(v).__name__})")


if __name__ == "__main__":
    load_data_to_mongo()
