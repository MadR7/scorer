# How to Share the Scoring App with Raters

## Quick Start

1. **Deploy to Streamlit Cloud** (if not done yet):
   - Go to https://share.streamlit.io/
   - Connect your GitHub repo
   - Add the secrets (see DEPLOY.md for details)
   - Deploy!

2. **Get your app URL** (something like `https://your-app.streamlit.app`)

3. **Send this to your raters:**

---

### Email Template

**Subject:** Help Us Improve AI for Factory Tasks (~5 minutes)

Hi [Name],

I need your help evaluating AI-generated descriptions of factory tasks. It should take about 5 minutes.

**What you'll do:**
- Watch 3 short videos
- Compare two AI descriptions for each
- Pick which one is better

**Link:** [YOUR_STREAMLIT_APP_URL_HERE]

**Instructions:** See attached `INSTRUCTIONS_FOR_RATERS.md` or the instructions in the app itself.

Thanks so much for helping!

[Your name]

---

## What Raters Will See

1. **Welcome screen** - explains the task in simple terms
2. **Identifier input** - they enter their name/email
3. **Video 1/3** - watch video, read RED and YELLOW text, pick better one
4. **Video 2/3** - same process
5. **Video 3/3** - same process
6. **Completion** - thank you message with confetti!

## Behind the Scenes

- Each rater gets 3 **random** videos (seeded by their ID for consistency)
- Colors (RED/YELLOW) are **randomized per video** to prevent bias
- Scores are saved to GCS automatically: `gs://buildai-dataset/scores/scores.csv`
- Model names are **hidden** - raters only see colors

## Collecting Results

After raters complete their evaluations:

```bash
# Download scores from cloud
python download_scores.py

# Analyze results
python visualize_results.py

# View raw data
cat output/scores.csv
```

## Troubleshooting

**Raters report the app won't load:**
- Check if your Streamlit Cloud app is running
- Verify secrets are configured correctly
- Make sure inference run is uploaded to GCS

**Videos won't play:**
- Verify the GCS video path is correct
- Check that videos exist at: `gs://buildai-dataset/finetune_dataset/test/`

**Scores not saving:**
- Check GCS permissions in your service account
- Verify bucket name is correct in `scoring_app.py`

## Tips for Best Results

✅ **Send to 5-10 people** for statistical significance
✅ **Include people with different backgrounds** for diverse perspectives
✅ **Don't tell them which model is which** - keep it blind!
✅ **Follow up** if someone doesn't complete within 24 hours

## Next Steps

After collecting scores:
1. Download results: `python download_scores.py`
2. Visualize: `python visualize_results.py`
3. Analyze statistical significance (p-values, win rates)
4. Decide if fine-tuning improved the model
5. Iterate on training data if needed

Happy evaluating! 🚀
