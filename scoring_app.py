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
    try:
        # Try Streamlit Cloud secrets first
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return Client(credentials=credentials)
    except:
        pass
    
    # Fall back to local credentials
    try:
        return Client()
    except:
        st.error("GCS authentication failed. Please configure credentials.")
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
        st.session_state.mode = None  # 'detailed' or 'binary'


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
    
    st.set_page_config(page_title="Factory Task Scoring", layout="wide")
    st.title("Factory Task Scoring")
    
    # Instructions (collapsible)
    with st.expander("📋 Instructions", expanded=False):
        st.markdown("""
        **Goal:** Score how well each text describes the wearer's actions in the video.
        
        **You will score 3 randomly selected videos.** Different raters may see different videos.
        
        **Two Modes Available:**
        
        **1. Binary Mode (Quick):**
        - Watch video and read both texts
        - Simply pick which text is better overall
        - Takes ~5 minutes for 3 videos
        
        **2. Detailed Mode (Thorough):**
        - Each text starts at 100 points
        - Deduct points per category for issues found
        - Categories: Step Coverage, Order, Verb Precision, Object/Hand/Tool, Hallucination
        - Takes ~10-15 minutes for 3 videos
        
        **Note:** Colors are randomized per video for blind evaluation. All scores saved automatically.
        """)
    
    st.divider()
    
    # Step 1: Select run
    if st.session_state.selected_run is None:
        st.subheader("1. Select Inference Run")
        
        with st.spinner("Loading available runs from cloud..."):
            runs = list_available_runs()
        
        if not runs:
            st.error("No inference runs found in cloud storage. Upload an inference run first.")
            st.info("Run locally: `python upload_inference_to_gcs.py output/run_XXXXXX`")
            return
        
        selected = st.selectbox("Choose run", runs, help="Most recent runs appear first")
        
        st.subheader("2. Enter GCS Video Path")
        gcs_input = st.text_input(
            "GCS path",
            value="gs://buildai-dataset/finetune_dataset/test/",
            help="Where source videos are stored"
        )
        
        if st.button("Load Run"):
            st.session_state.selected_run = selected
            st.session_state.gcs_video_path = gcs_input
            st.rerun()
        return
    
    # Step 2: Select mode
    if st.session_state.mode is None:
        st.subheader("2. Choose Scoring Mode")
        mode_choice = st.radio(
            "Select mode:",
            ["Binary (Quick - just pick which is better)", "Detailed (Thorough - deduct points per category)"],
            help="Binary is faster, Detailed provides more granular feedback"
        )
        
        if st.button("Continue"):
            st.session_state.mode = 'binary' if 'Binary' in mode_choice else 'detailed'
            st.rerun()
        return
    
    # Step 3: Enter rater ID
    if not st.session_state.rater_id:
        st.subheader("3. Enter Your ID")
        rater_input = st.text_input("Rater ID", placeholder="e.g., rater_1")
        if st.button("Start Scoring") and rater_input:
            st.session_state.rater_id = rater_input
            with st.spinner("Loading videos..."):
                st.session_state.videos = get_videos_from_gcs(
                    st.session_state.selected_run,
                    rater_input
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
        st.error("No videos found in this run.")
        return
    
    # Check if done
    idx = st.session_state.current_idx
    if idx >= len(videos):
        mode_name = "Binary" if st.session_state.mode == 'binary' else "Detailed"
        st.success(f"✅ All 3 videos scored ({mode_name} mode)! Thank you, {st.session_state.rater_id}.")
        st.balloons()
        if st.button("← Return to Start"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return
    
    # Current video
    video = videos[idx]
    mode_name = "Binary" if st.session_state.mode == 'binary' else "Detailed"
    st.subheader(f"Video {idx+1}/3: {video['name']}")
    st.caption(f"Rater: {st.session_state.rater_id} | Mode: {mode_name}")
    
    # Download video
    with st.spinner("Loading video..."):
        video_path = download_video(video['name'], st.session_state.gcs_video_path)
    
    if not video_path:
        st.error(f"Could not load video: {video['name']}")
        if st.button("Skip"):
            st.session_state.current_idx += 1
            st.rerun()
        return
    
    # LAYOUT
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        # Video (large, top)
        st.video(str(video_path))
        
        # Text outputs (bottom, side by side)
        text_col1, text_col2 = st.columns(2)
        
        with text_col1:
            color1 = video['color1']
            st.markdown(f"<div style='font-size: 18px; font-weight: bold; color: {color1}; margin-bottom: 10px;'>{color1.upper()} TEXT</div>", unsafe_allow_html=True)
            formatted1 = format_steps(video['text1'])
            st.markdown(f"<div style='font-size: 15px; line-height: 1.6;'><span style='color: {color1};'>{formatted1}</span></div>", unsafe_allow_html=True)
        
        with text_col2:
            color2 = video['color2']
            st.markdown(f"<div style='font-size: 18px; font-weight: bold; color: {color2}; margin-bottom: 10px;'>{color2.upper()} TEXT</div>", unsafe_allow_html=True)
            formatted2 = format_steps(video['text2'])
            st.markdown(f"<div style='font-size: 15px; line-height: 1.6;'><span style='color: {color2};'>{formatted2}</span></div>", unsafe_allow_html=True)
    
    with right_col:
        st.markdown("### Scoring")
        
        if st.session_state.mode == 'binary':
            # BINARY MODE
            st.caption("Which text better describes the video?")
            
            choice = st.radio(
                "Select the better text:",
                [f"{video['color1'].upper()} Text", f"{video['color2'].upper()} Text", "Both Equal"],
                key=f"binary_choice_{idx}"
            )
            
            notes = st.text_area("Why? (optional)", key=f"notes_{idx}", height=100, 
                               placeholder="Brief explanation of your choice...")
            
            if st.button("✓ Submit & Next", type="primary", use_container_width=True):
                # Binary scoring: 1 for winner, 0 for loser, 0.5 for tie
                if "Both Equal" in choice:
                    score1, score2 = 0.5, 0.5
                elif video['color1'].upper() in choice:
                    score1, score2 = 1, 0
                else:
                    score1, score2 = 0, 1
                
                with st.spinner("Saving scores..."):
                    save_score_to_gcs(video['name'], st.session_state.rater_id, video['color1'], 
                              video['model1'], {}, score1, notes, mode='binary')
                    save_score_to_gcs(video['name'], st.session_state.rater_id, video['color2'],
                              video['model2'], {}, score2, notes, mode='binary')
                
                st.session_state.current_idx += 1
                st.rerun()
        
        else:
            # DETAILED MODE
            st.caption("Enter points to deduct (0 if none)")
            
            # Score for color 1
            st.markdown(f"**{video['color1'].upper()} Text**")
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
            st.markdown(f"**{video['color2'].upper()} Text**")
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
                with st.spinner("Saving scores..."):
                    save_score_to_gcs(video['name'], st.session_state.rater_id, video['color1'], 
                              video['model1'], deductions1, score1, notes, mode='detailed')
                    save_score_to_gcs(video['name'], st.session_state.rater_id, video['color2'],
                              video['model2'], deductions2, score2, notes, mode='detailed')
                
                st.session_state.current_idx += 1
                st.rerun()


if __name__ == "__main__":
    main()