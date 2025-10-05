#!/usr/bin/env python3
"""
Download scores from GCS for local analysis.
"""

import os
from pathlib import Path
from google.cloud.storage import Client
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET = "buildai-dataset"
GCS_SCORES_PATH = "scores/scores.csv"
LOCAL_OUTPUT = Path("./output/scores.csv")


def download_scores():
    """Download scores CSV from GCS."""
    print(f"Downloading scores from gs://{GCS_BUCKET}/{GCS_SCORES_PATH}...")
    
    storage_client = Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_SCORES_PATH)
    
    try:
        # Ensure output directory exists
        LOCAL_OUTPUT.parent.mkdir(exist_ok=True)
        
        # Download
        blob.download_to_filename(str(LOCAL_OUTPUT))
        
        print(f"✓ Downloaded to: {LOCAL_OUTPUT}")
        
        # Show summary
        import pandas as pd
        df = pd.read_csv(LOCAL_OUTPUT)
        print(f"\nTotal scores: {len(df)}")
        print(f"Unique raters: {df['rater_id'].nunique()}")
        print(f"Unique videos: {df['video'].nunique()}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("  1. GCS credentials are configured")
        print("  2. Scores file exists at gs://buildai-dataset/scores/scores.csv")


if __name__ == "__main__":
    download_scores()
