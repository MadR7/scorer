# Factory Task Scoring System

AI model comparison for factory task understanding using human evaluation.

## Quick Start

### 1. Run Inference (Local)
```bash
GRPC_DNS_RESOLVER=native python run_inference.py \
  --model1 7337562260660813824 \
  --model2 gemini-2.5-pro \
  --model1-name finetuned \
  --model2-name baseline \
  --model1-prompt numbered \
  --model2-prompt numbered \
  --gcs-path gs://buildai-dataset/finetune_dataset/test/
```

### 2. Upload to Cloud
```bash
python upload_inference_to_gcs.py output/run_YYYYMMDD_HHMMSS
```

### 3. Deploy Scoring App
See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions.

Or test locally:
```bash
streamlit run scoring_app.py
```

### 4. Collect Scores
Share the app URL with raters. They'll:
- Select the inference run
- Choose scoring mode (Binary/Detailed)
- Score 3 random videos
- Scores auto-save to cloud

### 5. Analyze Results
```bash
python download_scores.py
python visualize_results.py
```

## Project Structure

```
.
├── run_inference.py          # Run model inference on videos
├── upload_inference_to_gcs.py # Upload results to cloud
├── generate_color_mapping.py  # Generate blind evaluation colors
├── scoring_app.py             # Streamlit scoring interface (cloud-enabled)
├── download_scores.py         # Download scores from cloud
├── visualize_results.py       # Generate results visualization
├── DEPLOY.md                  # Deployment guide
├── requirements.txt           # Python dependencies
└── .streamlit/
    ├── config.toml            # Streamlit configuration
    └── secrets.toml.example   # GCP credentials template

```

## Current Status

Based on latest scoring results:
- **Finetuned Model: 72.2% win rate** (19/27)
- **Baseline Model: 27.8% win rate** (7/27)
- **Effect Size: +44.4%**
- **p-value: 0.052** (need 2-3 more raters for significance)

## Workflow

**Local (You):**
1. Run inference → Get JSON outputs
2. Upload to GCS → Cloud storage
3. Deploy app → Get shareable URL

**Cloud (Raters):**
1. Open app URL
2. Select run & mode
3. Score 3 videos
4. Done! (scores auto-save)

**Analysis (You):**
1. Download scores from GCS
2. Visualize results
3. Statistical analysis

## Notes

- Each rater scores 3 randomly selected videos
- Colors (red/yellow) are randomized per video for blind evaluation
- Scores stored at: `gs://buildai-dataset/scores/scores.csv`
- Inference runs stored at: `gs://buildai-dataset/inference_runs/`