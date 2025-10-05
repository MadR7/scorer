# Deployment Guide: Factory Task Scoring App

Deploy the scoring app to Streamlit Cloud so raters can access it via a shareable URL.

## Prerequisites

1. Google Cloud Project with:
   - Cloud Storage API enabled
   - Service account with Storage Object Admin permissions
2. GitHub account
3. Streamlit Cloud account (free at https://share.streamlit.io)

## Step 1: Create GCP Service Account

```bash
# Set your project ID
export PROJECT_ID="data-470400"

# Create service account
gcloud iam service-accounts create streamlit-scorer \
    --display-name="Streamlit Scoring App" \
    --project=$PROJECT_ID

# Grant Storage Admin permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:streamlit-scorer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create and download key
gcloud iam service-accounts keys create ~/streamlit-key.json \
    --iam-account=streamlit-scorer@${PROJECT_ID}.iam.gserviceaccount.com
```

## Step 2: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Factory task scoring system"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo
4. Set:
   - **Main file path**: `scoring_app.py`
   - **Python version**: 3.11
5. Click "Advanced settings"
6. Add secrets (paste the contents of `~/streamlit-key.json`):

```toml
[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "streamlit-scorer@YOUR_PROJECT_ID.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

7. Click "Deploy"
8. Wait 2-3 minutes for deployment to complete
9. You'll get a URL like: `https://your-app-name.streamlit.app`

## Step 4: Upload Inference Run to Cloud

After running inference locally:

```bash
# Run inference with DNS fix
GRPC_DNS_RESOLVER=native python run_inference.py \
  --model1 7337562260660813824 \
  --model2 gemini-2.5-pro \
  --model1-name finetuned \
  --model2-name baseline \
  --model1-prompt numbered \
  --model2-prompt numbered \
  --gcs-path gs://buildai-dataset/finetune_dataset/test/

# Upload results to cloud
python upload_inference_to_gcs.py output/run_YYYYMMDD_HHMMSS
```

## Step 5: Share with Raters

Send raters:
1. The Streamlit app URL
2. Instructions to:
   - Select the latest run
   - Enter video path: `gs://buildai-dataset/finetune_dataset/test/`
   - Choose scoring mode (Binary recommended for speed)
   - Enter their name as Rater ID (e.g., "alice", "bob")
   - Score 3 videos

## Step 6: Download and Analyze Scores

```bash
# Download scores from cloud
gsutil cp gs://buildai-dataset/scores/scores.csv output/scores.csv

# Visualize results
python visualize_results.py
```

## Troubleshooting

### "No inference runs found"
- Make sure you ran `upload_inference_to_gcs.py` after inference
- Check GCS: `gsutil ls gs://buildai-dataset/inference_runs/`

### "GCS authentication failed"
- Verify secrets are correctly configured in Streamlit Cloud
- Check service account has Storage Object Admin role

### "Could not load video"
- Verify the GCS video path is correct
- Check videos exist: `gsutil ls gs://buildai-dataset/finetune_dataset/test/`

### App is slow
- This is normal - GCS downloads take time
- Videos are cached after first load

## Local Testing

Test the cloud-enabled app locally:

```bash
# Create local secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and paste your service account JSON

# Run locally
streamlit run scoring_app.py
```

## Cost Estimate

- Streamlit Cloud: **Free** (500 hours/month)
- GCS Storage: **~$0.02/GB/month** 
  - Videos: ~1GB = $0.02/month
  - Inference JSONs: ~10MB = $0.0002/month
  - Scores CSV: ~100KB = negligible
- GCS Operations: **~$0.004 per 10,000 reads**
  - Expected: ~100 reads/day = $0.012/month

**Total: < $1/month**
