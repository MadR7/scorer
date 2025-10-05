#!/usr/bin/env python3
"""
Streamlit app for scoring AI model outputs on factory task videos.
Cloud-enabled version with GCS storage.
"""

import streamlit as st
import pandas as pd
import json
import random
import os
import tempfile
from pathlib import Path
from datetime import datetime
from google.cloud.storage import Client
from google.oauth2 import service_account
from io import StringIO

# Configuration
GCS_BUCKET = "buildai-dataset"
GCS_INFERENCE_PATH = "inference_runs"
GCS_SCORES_PATH = "scores/scores.csv"

# Scoring rubric (5 categories)
RUBRIC = [
    {"key": "coverage", "name": "How many steps are missing? 5 for each missing step"},
    {"key": "order", "name": "Does the order of steps make sense? 4 for each step out of order"},
    {"key": "verb", "name": "Are the verbs correct? 3 for each verb that is wrong"},
    {"key": "specificity", "name": "Are the objects/hands/tools correct? 3 for each object/hand/tool that is wrong or missing"},
    {"key": "hallucination", "name": "Are there any made up steps? 10 for each made up step"}
]


def get_gcs_client():
    """Get authenticated GCS client."""
    # Try Streamlit Cloud secrets first (only if secrets exist)
    try:
        # Check if secrets are configured (this may throw if no secrets.toml exists)
        if 'gcp_service_account' in st.secrets:
            from google.oauth2.credentials import Credentials as UserCredentials
            
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # Handle both authorized_user and service_account types
            if creds_dict.get('type') == 'authorized_user':
                credentials = UserCredentials(
                    token=None,
                    refresh_token=creds_dict.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=creds_dict.get('client_id'),
                    client_secret=creds_dict.get('client_secret'),
                    quota_project_id=creds_dict.get('quota_project_id')
                )
            else:
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
            
            return Client(credentials=credentials, project=creds_dict.get('quota_project_id'))
    except (FileNotFoundError, KeyError, AttributeError):
        pass  # No secrets configured, fall through to local credentials
    
    # Fall back to local application default credentials
    try:
        return Client()
    except Exception as e:
        st.error(f"❌ GCS authentication failed: {e}")
        st.info("💡 Make sure you've run: `gcloud auth application-default login`")
        st.stop()


@st.cache_resource
def get_storage_client():
    """Cached GCS client."""
    return get_gcs_client()


def init_session():
    """Initialize session state variables."""
    if 'selected_run' not in st.session_state:
        st.session_state.selected_run = None
    if 'gcs_video_path' not in st.session_state:
        st.session_state.gcs_video_path = None
    if 'rater_id' not in st.session_state:
        st.session_state.rater_id = ""
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    if 'videos' not in st.session_state:
        st.session_state.videos = []
    if 'mode' not in st.session_state:
        st.session_state.mode = 'binary'  # Default to binary mode


def list_available_runs():
    """List available inference runs from GCS."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # List all run directories
    blobs = bucket.list_blobs(prefix=f"{GCS_INFERENCE_PATH}/run_")
    
    runs = set()
    for blob in blobs:
        # Extract run name from path like "inference_runs/run_20251004_135336/json/file.json"
        parts = blob.name.split('/')
        if len(parts) >= 2 and parts[1].startswith('run_'):
            runs.add(parts[1])
    
    return sorted(runs, reverse=True)


def get_videos_from_gcs(run_name, rater_id):
    """Get list of videos with their model outputs from GCS."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    json_prefix = f"{GCS_INFERENCE_PATH}/{run_name}/json/"
    
    # List all JSON files
    blobs = list(bucket.list_blobs(prefix=json_prefix))
    
    # Group JSON files by video name
    video_dict = {}
    color_map = {}
    
    for blob in blobs:
        filename = blob.name.split('/')[-1]
        
        if filename == "color_mapping.json":
            # Load color mapping
            content = blob.download_as_text()
            color_map = json.loads(content)
            continue
        
        if not filename.endswith('.json'):
            continue
        
        parts = filename.rsplit('.', 1)[0].rsplit('_', 1)
        if len(parts) == 2:
            video_name, model_name = parts
            if video_name not in video_dict:
                video_dict[video_name] = {}
            
            # Download and parse JSON
            content = blob.download_as_text()
            data = json.loads(content)
            
            if 'format' in data and data['format'] == 'numbered_list':
                video_dict[video_name][model_name] = data['steps']
    
    # Build video list
    videos = []
    for video_name, models in video_dict.items():
        if len(models) == 2:
            model_names = list(models.keys())
            video_colors = color_map.get(video_name, {})
            videos.append({
                'name': video_name,
                'model1': model_names[0],
                'model2': model_names[1],
                'text1': models[model_names[0]],
                'text2': models[model_names[1]],
                'color1': video_colors.get(model_names[0], 'yellow'),
                'color2': video_colors.get(model_names[1], 'red')
            })
    
    # Randomize and sample 3 videos per rater
    random.seed(rater_id)
    random.shuffle(videos)
    return videos[:3]  # Only return 3 random videos


def download_video(video_name, gcs_path):
    """Download video from GCS to temp location."""
    temp_dir = Path(tempfile.gettempdir()) / "scoring_videos"
    temp_dir.mkdir(exist_ok=True)
    local_path = temp_dir / f"{video_name}.mp4"
    
    if local_path.exists():
        return local_path
    
    # Parse GCS path
    if gcs_path.startswith('gs://'):
        gcs_path = gcs_path[5:]
    parts = gcs_path.split('/', 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    if prefix and not prefix.endswith('/'):
        prefix += '/'
    
    # Find and download video
    storage_client = get_storage_client()
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    for blob in blobs:
        filename = blob.name.split('/')[-1]
        name_no_ext = filename.rsplit('.', 1)[0].lower()
        if name_no_ext == video_name.lower() and filename.lower().endswith(('.mp4', '.mov', '.avi')):
            blob.download_to_filename(str(local_path))
            return local_path
    
    return None


def load_scores_from_gcs():
    """Load existing scores from GCS."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_SCORES_PATH)
    
    try:
        content = blob.download_as_text()
        return pd.read_csv(StringIO(content))
    except:
        # File doesn't exist yet, return empty DataFrame
        return pd.DataFrame(columns=[
            'timestamp', 'rater_id', 'video', 'color', 'model', 'mode',
            'coverage', 'order', 'verb', 'specificity', 'hallucination', 'score', 'notes'
        ])


def save_score_to_gcs(video_name, rater_id, color, model, deductions, score, notes, mode='detailed'):
    """Save a single score to GCS CSV."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_SCORES_PATH)
    
    # Load existing scores
    existing_df = load_scores_from_gcs()
    
    # Create new row
    if mode == 'binary':
        data = {
            'timestamp': datetime.now().isoformat(),
            'rater_id': rater_id,
            'video': video_name,
            'color': color,
            'model': model,
            'mode': 'binary',
            'coverage': 'binary',
            'order': score,  # Binary score goes in order column
            'verb': '',
            'specificity': '',
            'hallucination': '',
            'score': '',
            'notes': notes
        }
    else:
        data = {
            'timestamp': datetime.now().isoformat(),
            'rater_id': rater_id,
            'video': video_name,
            'color': color,
            'model': model,
            'mode': 'detailed',
            'coverage': deductions.get('coverage', 0),
            'order': deductions.get('order', 0),
            'verb': deductions.get('verb', 0),
            'specificity': deductions.get('specificity', 0),
            'hallucination': deductions.get('hallucination', 0),
            'score': score,
            'notes': notes
        }
    
    # Append to DataFrame
    new_df = pd.concat([existing_df, pd.DataFrame([data])], ignore_index=True)
    
    # Upload to GCS
    csv_string = new_df.to_csv(index=False)
    blob.upload_from_string(csv_string, content_type='text/csv')


def format_steps(text):
    """Format numbered list text for display."""
    import re
    lines = re.split(r'(\d+\.)', text)
    formatted = []
    for i in range(1, len(lines), 2):
        if i < len(lines):
            formatted.append(f"{lines[i]} {lines[i+1].strip()}")
    return "<br><br>".join(formatted)


def main():
    init_session()
    
    st.set_page_config(page_title="Video Description Scoring", layout="wide")
    
    # Custom CSS for black background and mobile-friendly layout
    st.markdown("""
        <style>
        .stApp {
            background-color: #000000;
            color: #FFFFFF;
        }
        .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
            color: #FFFFFF !important;
        }
        .stRadio label {
            color: #FFFFFF !important;
        }
        .stTextArea label {
            color: #FFFFFF !important;
        }
        div[data-baseweb="select"] {
            color: #FFFFFF;
        }
        
        /* Mobile-friendly: compact everything */
        .stVideo {
            max-height: 250px !important;
        }
        
        /* Description boxes (full height, no scroll) */
        .description-box {
            padding: 12px;
            border: 2px solid #444;
            border-radius: 8px;
            margin-bottom: 12px;
            font-size: 14px;
            line-height: 1.5;
            background-color: #111;
        }
        
        /* Compact radio buttons */
        .stRadio > div {
            gap: 0.3rem !important;
        }
        
        .stRadio label {
            font-size: 16px !important;
            padding: 4px 0 !important;
        }
        
        /* Compact headers */
        h3 {
            margin-top: 10px !important;
            margin-bottom: 10px !important;
            font-size: 1.3rem !important;
        }
        
        h4 {
            margin-top: 8px !important;
            margin-bottom: 6px !important;
            font-size: 1.1rem !important;
        }
        
        /* Compact progress */
        .stProgress {
            margin-bottom: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Show welcome screen only once
    if 'welcome_seen' not in st.session_state:
        st.session_state.welcome_seen = False
    
    if not st.session_state.welcome_seen:
        st.markdown("""
        # 👋 Welcome!
        
        ## What you'll do:
        
        ### 1. Watch 3 short videos
        Each is 1-2 minutes long
        
        ### 2. Compare two descriptions
        You'll see RED and YELLOW text for each video
        
        ### 3. Pick the better one
        Choose which description lets you perfectly replicate the task
        
        ### 4. That's it!
        Takes about 5 minutes total
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Let's Start", type="primary", use_container_width=True):
            st.session_state.welcome_seen = True
            st.rerun()
        return
    
    # Compact header for scoring screens
    st.markdown("## Video Description Scoring")
    
    # Step 1: Setup (simplified for end users)
    if st.session_state.selected_run is None:
        with st.spinner("Loading..."):
            runs = list_available_runs()
        
        if not runs:
            st.error("No videos available. Please contact the administrator.")
            return
        
        # Auto-select latest run
        selected = runs[0]
        
        # Silently set the GCS path and move on
        st.session_state.selected_run = selected
        st.session_state.gcs_video_path = "gs://buildai-dataset/finetune_dataset/test/"
        st.rerun()
        return
    
    
    # Mode selection (binary is default, but allow override)
    if st.session_state.get('show_mode_override'):
        st.subheader("2. Change Scoring Mode")
        mode_choice = st.radio(
            "Select mode:",
            ["Binary (Quick - just pick which is better) ⭐ RECOMMENDED", "Detailed (Thorough - deduct points per category)"],
            index=0,
            help="Binary is faster and easier, Detailed provides more granular feedback"
        )
        
        if st.button("Continue"):
            st.session_state.mode = 'binary' if 'Binary' in mode_choice else 'detailed'
            st.session_state.show_mode_override = False
            st.rerun()
        return
    
    # Step 2: Auto-start with random videos
    if not st.session_state.rater_id:
        st.markdown("### Ready?")
        if st.button("Start", type="primary", use_container_width=True):
            # Generate a unique random rater ID and seed
            import time
            random.seed(int(time.time() * 1000) % 2**32)
            st.session_state.rater_id = f"rater_{random.randint(1000, 9999)}"
            with st.spinner("Loading..."):
                st.session_state.videos = get_videos_from_gcs(
                    st.session_state.selected_run,
                    st.session_state.rater_id
                )
            st.rerun()
        return
    
    # Load videos if not loaded
    if not st.session_state.videos:
        with st.spinner("Loading videos..."):
            st.session_state.videos = get_videos_from_gcs(
                st.session_state.selected_run,
                st.session_state.rater_id
            )
    
    videos = st.session_state.videos
    if not videos:
        st.error("No videos available.")
        return
    
    # Check if done
    idx = st.session_state.current_idx
    if idx >= len(videos):
        st.balloons()
        st.success("All done! Thank you!")
        st.markdown("Your responses have been saved. You can close this page now.")
        
        if st.button("Score More Videos", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return
    
    # Current video
    video = videos[idx]
    
    # Compact progress indicator
    st.progress((idx) / len(videos), text=f"{idx+1}/3")
    st.markdown(f"### Video {idx+1}")
    
    # Download video
    with st.spinner("Loading video..."):
        video_path = download_video(video['name'], st.session_state.gcs_video_path)
    
    if not video_path:
        st.error("Could not load video.")
        if st.button("Skip to next"):
            st.session_state.current_idx += 1
            st.rerun()
        return
    
    # MOBILE-FRIENDLY SINGLE COLUMN LAYOUT
    # Video at top (compact)
    st.video(str(video_path))
    
    # Both descriptions stacked vertically (no tabs, no scrolling)
    color1 = video['color1']
    color2 = video['color2']
    emoji1 = "🔴" if color1 == 'red' else "🟡"
    emoji2 = "🟡" if color2 == 'yellow' else "🔴"
    
    # First description
    st.markdown(f"#### {emoji1} {color1.upper()} Description")
    formatted1 = format_steps(video['text1'])
    st.markdown(f"<div class='description-box'><span style='color: {color1};'>{formatted1}</span></div>", unsafe_allow_html=True)
    
    # Second description
    st.markdown(f"#### {emoji2} {color2.upper()} Description")
    formatted2 = format_steps(video['text2'])
    st.markdown(f"<div class='description-box'><span style='color: {color2};'>{formatted2}</span></div>", unsafe_allow_html=True)
    
    # Scoring section
    if st.session_state.mode == 'binary':
        st.markdown("### Which is better?")
        
        choice = st.radio(
            "Select:",
            [f"{emoji1} {color1.upper()}", 
             f"{emoji2} {color2.upper()}", 
             "Both equal"],
            key=f"binary_choice_{idx}",
            label_visibility="collapsed"
        )
        
        if st.button("Submit & Next", type="primary", use_container_width=True):
            # Binary scoring: 1 for winner, 0 for loser, 0.5 for tie
            if "equal" in choice.lower():
                score1, score2 = 0.5, 0.5
            elif color1.upper() in choice:
                score1, score2 = 1, 0
            else:
                score1, score2 = 0, 1
            
            # Use empty notes since we removed the field
            notes = ""
            
            with st.spinner("Saving..."):
                save_score_to_gcs(video['name'], st.session_state.rater_id, color1, 
                          video['model1'], {}, score1, notes, mode='binary')
                save_score_to_gcs(video['name'], st.session_state.rater_id, color2,
                          video['model2'], {}, score2, notes, mode='binary')
            
            st.session_state.current_idx += 1
            st.rerun()
    
    else:
        # DETAILED MODE (not used, but keeping for compatibility)
        st.caption("Enter points to deduct (0 if none)")
        
        # Score for color 1
        st.markdown(f"**{color1.upper()} Text**")
        deductions1 = {}
        for cat in RUBRIC:
            deductions1[cat['key']] = st.number_input(
                cat['name'],
                min_value=0,
                max_value=100,
                value=0,
                key=f"c1_{cat['key']}_{idx}",
                help=f"Points to deduct for {cat['name'].lower()}"
            )
        total1 = sum(deductions1.values())
        score1 = max(0, 100 - total1)
        st.markdown(f"**Score: {score1}/100**")
        
        st.divider()
        
        # Score for color 2
        st.markdown(f"**{color2.upper()} Text**")
        deductions2 = {}
        for cat in RUBRIC:
            deductions2[cat['key']] = st.number_input(
                cat['name'],
                min_value=0,
                max_value=100,
                value=0,
                key=f"c2_{cat['key']}_{idx}",
                help=f"Points to deduct for {cat['name'].lower()}"
            )
        total2 = sum(deductions2.values())
        score2 = max(0, 100 - total2)
        st.markdown(f"**Score: {score2}/100**")
        
        st.divider()
        
        # Notes
        notes = st.text_area("Notes (optional)", key=f"notes_{idx}", height=80)
        
        # Submit
        if st.button("✓ Submit & Next", type="primary", use_container_width=True):
            with st.spinner("Saving..."):
                save_score_to_gcs(video['name'], st.session_state.rater_id, color1, 
                          video['model1'], deductions1, score1, notes, mode='detailed')
                save_score_to_gcs(video['name'], st.session_state.rater_id, color2,
                          video['model2'], deductions2, score2, notes, mode='detailed')
            
            st.session_state.current_idx += 1
            st.rerun()


if __name__ == "__main__":
    main()