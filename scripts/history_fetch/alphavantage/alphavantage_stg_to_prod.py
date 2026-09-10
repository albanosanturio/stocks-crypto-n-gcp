"""
Appends rows from market_data.stocks_staging into market_data.stocks
"""

from google.cloud import bigquery

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
STAGING_TABLE_ID = "stocks_staging"
MAIN_TABLE_ID = "stocks"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET_ID}.{MAIN_TABLE_ID}`
        SELECT symbol, price, source, fetched_at
        FROM `{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}`
    """

    print("Copying staging rows into main stocks table...")
    query_job = client.query(query)
    query_job.result()  # waits for completion, raises on failure

    main_table = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{MAIN_TABLE_ID}")
    print(f"Done. market_data.stocks now has {main_table.num_rows} total rows.")
    print("\nIf everything looks correct, you can drop the staging table:")
    print(f"  DROP TABLE `{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}`")


if __name__ == "__main__":
    main()