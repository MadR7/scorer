<!-- 858f14cb-937b-4eeb-971d-4a4d2d8b4460 4aa35671-1327-46df-982e-79c1fa57603c -->
# Deploy Factory Task Scoring System to Cloud

## Goal

Get the scoring app deployed to Streamlit Cloud with cloud storage so you can share a URL with raters and get more data for statistical significance.

## Architecture

- **App hosting**: Streamlit Cloud (free, zero setup)
- **Video storage**: Existing GCS bucket (no changes needed)
- **Score storage**: GCS bucket (CSV file at `gs://buildai-dataset/scores/scores.csv`)
- **Inference outputs**: GCS bucket (upload JSON files after local inference)
- **Authentication**: None (open URL, tracked by rater ID)

## Implementation Steps

### 1. Modify Scoring App for Cloud Storage

**File**: `scoring_app.py`

Changes needed:

- Replace local CSV writes with GCS writes
- Add function to read/write scores from `gs://buildai-dataset/scores/scores.csv`
- Add GCS authentication via Streamlit secrets
- Keep video downloading from GCS (already works)
- Modify to load inference JSONs from GCS path instead of local `output/` directory

Key functions to add:

```python
def load_scores_from_gcs():
    """Load existing scores from GCS"""
    
def save_score_to_gcs(data):
    """Append score to GCS CSV"""
```

### 2. Upload Inference Outputs to GCS

**Script**: Create `upload_inference_to_gcs.py`

Purpose: After running local inference, upload the JSON outputs to GCS so the cloud app can access them.

Upload to: `gs://buildai-dataset/inference_runs/run_YYYYMMDD_HHMMSS/`

### 3. Configure Streamlit for Deployment

**Files to create**:

- `.streamlit/config.toml` - Basic Streamlit config
- `.streamlit/secrets.toml.example` - Template for GCP credentials (git-ignored)
- `.gitignore` - Ignore secrets and local files

### 4. Update Requirements

**File**: `requirements.txt`

Ensure only necessary packages:

- streamlit
- pandas
- google-cloud-storage
- No matplotlib/scipy/vertexai needed for scoring app

### 5. Create Deployment Documentation

**File**: `DEPLOY.md`

Instructions for:

1. Creating GCP service account with GCS read/write permissions
2. Setting up Streamlit Cloud secrets
3. Connecting GitHub repo
4. Deploying app

### 6. Deploy to Streamlit Cloud

Manual steps (not code):

1. Push code to GitHub
2. Go to share.streamlit.io
3. Connect repo
4. Add GCP service account JSON as secret
5. Deploy → Get shareable URL

## Workflow After Deployment

**For new inference runs:**

1. Run inference locally: `GRPC_DNS_RESOLVER=native python run_inference.py ...`
2. Upload results: `python upload_inference_to_gcs.py output/run_XXXXXX`
3. Raters access: `https://your-app.streamlit.app`
4. Select the new run from dropdown, score videos
5. Scores auto-save to GCS
6. Download scores: `gsutil cp gs://buildai-dataset/scores/scores.csv output/`
7. Analyze: `python visualize_results.py`

## Time Estimate

- Code changes: 10 minutes
- Streamlit Cloud setup: 5 minutes
- **Total: 15 minutes to live deployment**

## No Changes Needed

- Local inference scripts (keep as-is)
- Video files (already in GCS)
- Visualization script (runs locally on downloaded scores)