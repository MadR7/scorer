#!/usr/bin/env python3
"""
Upload local inference outputs to GCS for cloud scoring app access.
"""

import os
import sys
import json
from pathlib import Path
from google.cloud.storage import Client
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET = "buildai-dataset"
GCS_BASE_PATH = "inference_runs"


def upload_run_to_gcs(local_run_dir: Path):
    """Upload inference run directory to GCS."""
    if not local_run_dir.exists():
        print(f"Error: {local_run_dir} does not exist")
        sys.exit(1)
    
    run_name = local_run_dir.name
    gcs_path = f"{GCS_BASE_PATH}/{run_name}"
    
    print(f"Uploading {local_run_dir} to gs://{GCS_BUCKET}/{gcs_path}/...")
    
    storage_client = Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # Upload JSON files
    json_dir = local_run_dir / "json"
    if not json_dir.exists():
        print(f"Error: {json_dir} does not exist")
        sys.exit(1)
    
    json_files = list(json_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to upload")
    
    for json_file in json_files:
        blob_path = f"{gcs_path}/json/{json_file.name}"
        blob = bucket.blob(blob_path)
        
        blob.upload_from_filename(str(json_file))
        print(f"  ✓ Uploaded {json_file.name}")
    
    print(f"\n✓ Upload complete!")
    print(f"  GCS path: gs://{GCS_BUCKET}/{gcs_path}/")
    print(f"  Run name for scoring app: {run_name}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_inference_to_gcs.py <run_directory>")
        print("Example: python upload_inference_to_gcs.py output/run_20251004_135336")
        sys.exit(1)
    
    local_run_dir = Path(sys.argv[1])
    upload_run_to_gcs(local_run_dir)


if __name__ == "__main__":
    main()
