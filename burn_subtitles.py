#!/usr/bin/env python3
"""
Download videos from GCS and burn ASS subtitles into them using ffmpeg.
"""

import os
import sys
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
parser = argparse.ArgumentParser(description="Burn subtitles into videos")
parser.add_argument(
    "output_dir",
    type=str,
    nargs="?",
    help="Output directory from inference run (e.g., output/run_20251004_003215)"
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
    # Find the most recent run directory
    base_output = Path(os.getenv("OUTPUT_DIR", "./output"))
    run_dirs = sorted(base_output.glob("run_*"))
    if run_dirs:
        OUTPUT_DIR = run_dirs[-1]
    else:
        print("ERROR: No run directories found! Run inference first.")
        sys.exit(1)

SUBTITLE_DIR = OUTPUT_DIR / "subtitles"
VIDEO_DIR = OUTPUT_DIR / "videos"
TEMP_DIR = OUTPUT_DIR / "temp"

# Create output directories
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
    
    # Ensure prefix ends with / if it exists
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    
    # Find the blob matching the video name
    blobs = bucket.list_blobs(prefix=prefix)
    
    video_blob = None
    for blob in blobs:
        if video_name in blob.name.lower() and (
            blob.name.endswith('.mp4') or 
            blob.name.endswith('.mov') or 
            blob.name.endswith('.avi')
        ):
            video_blob = blob
            break
    
    if not video_blob:
        raise FileNotFoundError(f"Video not found in GCS: {video_name}")
    
    # Download to temp
    local_path = TEMP_DIR / video_blob.name.split('/')[-1]
    video_blob.download_to_filename(str(local_path))
    print(f"    ✓ Downloaded to {local_path}")
    
    return local_path


def burn_subtitles_ffmpeg(video_path: Path, subtitle_path: Path, output_path: Path):
    """Use ffmpeg to burn ASS subtitles into video."""
    print(f"  [2/3] Burning subtitles with ffmpeg...")
    
    # Convert paths to absolute paths for ffmpeg
    video_path_abs = video_path.absolute()
    subtitle_path_abs = subtitle_path.absolute()
    output_path_abs = output_path.absolute()
    
    # Construct ffmpeg command
    # Use ASS subtitle filter for styled subtitles
    cmd = [
        "ffmpeg",
        "-i", str(video_path_abs),
        "-vf", f"ass={subtitle_path_abs}",
        "-c:a", "copy",  # Copy audio without re-encoding
        "-y",  # Overwrite output file
        str(output_path_abs)
    ]
    
    # Run ffmpeg
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        print(f"    ✓ Subtitles burned successfully")
    except subprocess.CalledProcessError as e:
        print(f"    ✗ FFmpeg error:")
        print(f"    {e.stderr}")
        raise


def process_single_video(subtitle_path: Path, gcs_path: str):
    """Process a single video with subtitles."""
    video_name = subtitle_path.stem
    print(f"[START] {video_name}")
    
    try:
        # Download video from GCS
        local_video_path = download_video_from_gcs(video_name, gcs_path)
        
        # Output path
        output_path = VIDEO_DIR / f"{video_name}_comparison.mp4"
        
        # Burn subtitles
        print(f"  [{video_name}] Burning subtitles...")
        burn_subtitles_ffmpeg(local_video_path, subtitle_path, output_path)
        
        # Clean up temp video
        local_video_path.unlink()
        
        print(f"[✓ DONE] {video_name}")
        return (video_name, True, None)
        
    except Exception as e:
        print(f"[✗ ERROR] {video_name}: {str(e)}")
        return (video_name, False, str(e))


def main():
    """Main execution function."""
    print("=" * 80)
    print("Burning Subtitles into Videos (PARALLEL)")
    print("=" * 80)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"GCS source path: {args.gcs_path}")
    print()
    
    # Check ffmpeg
    print("Checking dependencies...")
    if not check_ffmpeg():
        print("ERROR: ffmpeg is not installed!")
        print("Install it with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
        return
    print("  ✓ ffmpeg found")
    print()
    
    # Find all subtitle files
    subtitle_files = sorted(SUBTITLE_DIR.glob("*.ass"))
    
    if not subtitle_files:
        print("ERROR: No subtitle files found!")
        print(f"Make sure you've run 'python create_subtitles.py' first.")
        return
    
    print(f"Found {len(subtitle_files)} videos to process")
    print()
    
    # Process all videos in parallel
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(process_single_video, subtitle_path, args.gcs_path): subtitle_path
            for subtitle_path in subtitle_files
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
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
        for video_name, _, error in failed:
            print(f"    - {video_name}: {error}")
    
    print()
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  - JSON outputs: {OUTPUT_DIR / 'json'}")
    print(f"  - Subtitles: {SUBTITLE_DIR}")
    print(f"  - Videos: {VIDEO_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()

