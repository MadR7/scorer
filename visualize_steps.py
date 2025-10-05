#!/usr/bin/env python3
"""
Create videos with step-by-step visualizations for numbered list outputs.
Video on the left, steps overlay on the right in randomized red/yellow colors.
"""

import os
import sys
import json
import random
import subprocess
import shutil
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from google.cloud import storage

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")

# Parse command line arguments
parser = argparse.ArgumentParser(description="Visualize numbered step outputs")
parser.add_argument(
    "output_dir",
    type=str,
    nargs="?",
    help="Output directory from inference run"
)
parser.add_argument(
    "--gcs-path",
    type=str,
    default=f"{os.getenv('GCS_BUCKET', 'buildai-dataset')}/{os.getenv('GCS_PREFIX', 'finetune_dataset/')}",
    help="GCS path where source videos are located"
)
args = parser.parse_args()

# Get output directory
if args.output_dir:
    OUTPUT_DIR = Path(args.output_dir)
else:
    base_output = Path(os.getenv("OUTPUT_DIR", "./output"))
    run_dirs = sorted(base_output.glob("run_*"))
    if run_dirs:
        OUTPUT_DIR = run_dirs[-1]
    else:
        print("ERROR: No run directories found!")
        sys.exit(1)

JSON_DIR = OUTPUT_DIR / "json"
VIDEO_DIR = OUTPUT_DIR / "videos"
TEMP_DIR = OUTPUT_DIR / "temp"
MAPPING_FILE = OUTPUT_DIR / "color_mapping.json"

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_video_from_gcs(video_name: str, gcs_path: str) -> Path:
    """Download video from GCS to temp directory."""
    print(f"  [{video_name}] Downloading from GCS...")
    
    # Parse GCS path
    gcs_path_clean = gcs_path.replace("gs://", "")
    parts = gcs_path_clean.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    
    blobs = bucket.list_blobs(prefix=prefix)
    
    video_blob = None
    for blob in blobs:
        if video_name in blob.name.lower() and blob.name.endswith(('.mp4', '.mov', '.avi', '.MP4', '.MOV', '.AVI')):
            video_blob = blob
            break
    
    if not video_blob:
        raise FileNotFoundError(f"Video not found in GCS: {video_name}")
    
    local_path = TEMP_DIR / video_blob.name.split('/')[-1]
    video_blob.download_to_filename(str(local_path))
    
    return local_path


def create_video_with_combined_steps(video_path: Path, model1_steps: str, model2_steps: str, 
                                     model1_name: str, model2_name: str,
                                     model1_color: str, model2_color: str, 
                                     output_path: Path):
    """Create video with both models' steps in a single panel using ffmpeg."""
    print(f"  Creating combined visualization...")
    print(f"    {model1_name}: {model1_color.upper()}, {model2_name}: {model2_color.upper()}")
    
    # NO MODEL NAMES IN VIDEO - BLIND EVALUATION
    # Just show the steps in different colors, no labels
    
    # Create text files for each model
    text_file1 = TEMP_DIR / f"{video_path.stem}_{model1_name}.txt"
    text_file2 = TEMP_DIR / f"{video_path.stem}_{model2_name}.txt"
    
    with open(text_file1, 'w') as f:
        f.write(model1_steps)
    with open(text_file2, 'w') as f:
        f.write(model2_steps)
    
    # Build ffmpeg command with stacked text
    # Just draw the steps in different colors, no headers or model names
    cmd = [
        "ffmpeg",
        "-i", str(video_path.absolute()),
        "-vf", (
            f"[0:v]split[original][fortext];"
            f"[original]scale=iw/2:ih[left];"
            f"[fortext]scale=iw/2:ih,drawbox=color=black:t=fill,"
            # Model 1 steps (no header)
            f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:"
            f"textfile={text_file1.absolute()}:fontcolor={model1_color}:fontsize=14:x=10:y=10:line_spacing=3,"
            # Model 2 steps (no header)
            f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:"
            f"textfile={text_file2.absolute()}:fontcolor={model2_color}:fontsize=14:x=10:y=h/2:line_spacing=3"
            f"[right];"
            f"[left][right]hstack"
        ),
        "-c:a", "copy",
        "-y",
        str(output_path.absolute())
    ]
    
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        print(f"    ✓ Video created successfully")
    except subprocess.CalledProcessError as e:
        print(f"    ✗ FFmpeg error: {e.stderr}")
        raise


def process_video(video_name: str, model1_json: Path, model2_json: Path, model1_name: str, model2_name: str):
    """Process a single video with both model outputs in one combined video."""
    print(f"[START] {video_name}")
    
    try:
        # Randomize colors for THIS video only
        colors = ["red", "yellow"]
        random.shuffle(colors)
        video_color_map = {
            model1_name: colors[0],
            model2_name: colors[1]
        }
        
        # Load JSON outputs
        with open(model1_json, 'r') as f:
            model1_data = json.load(f)
        with open(model2_json, 'r') as f:
            model2_data = json.load(f)
        
        # Check if outputs are numbered lists
        model1_steps = model1_data.get("steps", "")
        model2_steps = model2_data.get("steps", "")
        
        if not model1_steps or not model2_steps:
            print(f"  ✗ Skipping {video_name}: Not numbered list format")
            return (video_name, False, "Not numbered list format", None)
        
        # Download video
        local_video_path = download_video_from_gcs(video_name, args.gcs_path)
        
        # Create ONE output video with both models' steps
        output_path = VIDEO_DIR / f"{video_name}_comparison.mp4"
        create_video_with_combined_steps(
            local_video_path, 
            model1_steps, 
            model2_steps,
            model1_name,
            model2_name,
            video_color_map[model1_name],
            video_color_map[model2_name],
            output_path
        )
        
        # Clean up
        local_video_path.unlink()
        
        print(f"[✓ DONE] {video_name}")
        return (video_name, True, None, video_color_map)
        
    except Exception as e:
        print(f"[✗ ERROR] {video_name}: {str(e)}")
        return (video_name, False, str(e), None)


def main():
    """Main execution function."""
    print("=" * 80)
    print("Visualizing Numbered Steps (PARALLEL)")
    print("=" * 80)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"GCS source path: {args.gcs_path}")
    print()
    
    # Check ffmpeg
    print("Checking dependencies...")
    if not check_ffmpeg():
        print("ERROR: ffmpeg is not installed!")
        print("Install it with: brew install ffmpeg (macOS)")
        return
    print("  ✓ ffmpeg found")
    print()
    
    # Find all JSON files and group by video
    all_json_files = sorted(JSON_DIR.glob("*.json"))
    if not all_json_files:
        print("ERROR: No JSON files found!")
        return
    
    # Group by video name
    video_dict = {}
    for json_path in all_json_files:
        parts = json_path.stem.rsplit('_', 1)
        if len(parts) == 2:
            video_name, model_name = parts
            if video_name not in video_dict:
                video_dict[video_name] = {}
            video_dict[video_name][model_name] = json_path
    
    # Filter to only numbered list outputs
    valid_videos = {}
    for video_name, models in video_dict.items():
        if len(models) >= 2:
            valid_videos[video_name] = models
    
    if not valid_videos:
        print("ERROR: No valid video pairs found!")
        return
    
    print(f"Found {len(valid_videos)} videos to process")
    print()
    print("🎨 Colors will be RANDOMIZED per video to avoid bias")
    print()
    
    # Get model names
    model_names = list(list(valid_videos.values())[0].keys())
    
    # Process all videos in parallel
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for video_name, models in valid_videos.items():
            model1_name = model_names[0]
            model2_name = model_names[1]
            futures.append(
                executor.submit(
                    process_video,
                    video_name,
                    models[model1_name],
                    models[model2_name],
                    model1_name,
                    model2_name
                )
            )
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    # Collect color mappings from successful results
    color_mapping = {}
    for video_name, success, error, video_colors in results:
        if success and video_colors:
            color_mapping[video_name] = video_colors
    
    # Save color mapping
    with open(MAPPING_FILE, 'w') as f:
        json.dump(color_mapping, f, indent=2)
    print()
    print(f"✓ Color mapping saved to: {MAPPING_FILE}")
    print()
    
    # Clean up temp directory
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    
    print()
    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print(f"  ✓ Successful: {len(successful)}/{len(results)}")
    if failed:
        print(f"  ✗ Failed: {len(failed)}")
        for video_name, _, error, _ in failed:
            print(f"    - {video_name}: {error}")
    
    print()
    print(f"  Output videos: {VIDEO_DIR}")
    print(f"  Color mapping: {MAPPING_FILE}")
    print()
    print("  Each video has RANDOMIZED colors to prevent evaluation bias!")
    print("=" * 80)


if __name__ == "__main__":
    main()
