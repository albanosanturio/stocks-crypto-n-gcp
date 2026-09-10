"""
Loads the (trimmed) coingecko_history_qa.csv into a staging table
(market_data.prices_staging), overwriting it fresh each run.

Does NOT touch market_data.prices yet -- inspect the staging table in
the console first, and only once it looks correct, run the merge step
to copy it into prices.
"""

from google.cloud import bigquery

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
STAGING_TABLE_ID = "prices_staging"

CSV_FILE = "./scripts/history_fetch/coingecko/coingecko_history.csv"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    staging_ref = f"{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print(f"Loading {CSV_FILE} into staging table {staging_ref}...")

    with open(CSV_FILE, "rb") as f:
        load_job = client.load_table_from_file(f, staging_ref, job_config=job_config)

    load_job.result()

    staging_table = client.get_table(staging_ref)
    print(f"Done. Staging table now has {staging_table.num_rows} rows.")
    print(f"\nInspect it in the console: {staging_ref}")
    print("Once it looks correct, run the merge step to copy into market_data.prices.")


if __name__ == "__main__":
    main()