"""
Two-stage load:
  1. stocks_staging.
  2. staging_to_main.py to copy it into stocks.

"""

from google.cloud import bigquery

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
STAGING_TABLE_ID = "stocks_staging"

CSV_FILE = "./scripts/history_fetch/alphavantage/alphavantage_history.csv"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    staging_ref = f"{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # skip the header row
        autodetect=True,      # staging table doesn't exist yet, let BQ infer schema
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # fresh each run
    )

    print(f"Loading {CSV_FILE} into staging table {staging_ref}...")

    with open(CSV_FILE, "rb") as f:
        load_job = client.load_table_from_file(f, staging_ref, job_config=job_config)

    load_job.result()  # waits for completion, raises on failure

    staging_table = client.get_table(staging_ref)
    print(f"Done. Staging table now has {staging_table.num_rows} rows.")
    print(f"\nInspect it in the console: {staging_ref}")
    print("Once it looks correct, run staging_to_main.py to copy into market_data.stocks.")


if __name__ == "__main__":
    main()