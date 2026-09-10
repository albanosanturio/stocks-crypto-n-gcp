"""
Copies rows from market_data.prices_staging into market_data.prices
(append mode -- does not touch existing rows in prices).

Run this only after inspecting the staging table and confirming it
looks correct.
"""

from google.cloud import bigquery

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
STAGING_TABLE_ID = "prices_staging"
MAIN_TABLE_ID = "prices"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET_ID}.{MAIN_TABLE_ID}`
        SELECT symbol, price, source, fetched_at
        FROM `{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}`
    """

    print("Copying staging rows into main prices table...")
    query_job = client.query(query)
    query_job.result()

    main_table = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{MAIN_TABLE_ID}")
    print(f"Done. market_data.prices now has {main_table.num_rows} total rows.")
    print("\nIf everything looks correct, you can drop the staging table:")
    print(f"  DROP TABLE `{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}`")


if __name__ == "__main__":
    main()