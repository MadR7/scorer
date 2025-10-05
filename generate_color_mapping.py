#!/usr/bin/env python3
"""
Generate color mapping for blind evaluation.
Run this if you don't have a color_mapping.json from visualize_steps.py
"""

import json
import random
from pathlib import Path

OUTPUT_DIR = Path("output")

def get_latest_run():
    """Get the most recent run directory."""
    run_dirs = sorted(OUTPUT_DIR.glob("run_*"))
    if run_dirs:
        return run_dirs[-1]
    return None

def main():
    run_dir = get_latest_run()
    if not run_dir:
        print("ERROR: No run directory found")
        return
    
    json_dir = run_dir / "json"
    if not json_dir.exists():
        print("ERROR: No JSON directory found")
        return
    
    # Group JSON files by video
    video_dict = {}
    for json_path in sorted(json_dir.glob("*.json")):
        parts = json_path.stem.rsplit('_', 1)
        if len(parts) == 2:
            video_name, model_name = parts
            if video_name not in video_dict:
                video_dict[video_name] = []
            video_dict[video_name].append(model_name)
    
    # Generate random color mapping for each video
    color_mapping = {}
    for video_name, models in video_dict.items():
        if len(models) >= 2:
            colors = ["red", "yellow"]
            random.shuffle(colors)
            color_mapping[video_name] = {
                models[0]: colors[0],
                models[1]: colors[1]
            }
    
    # Save
    mapping_file = run_dir / "color_mapping.json"
    with open(mapping_file, 'w') as f:
        json.dump(color_mapping, f, indent=2)
    
    print(f"✓ Color mapping generated: {mapping_file}")
    print(f"  {len(color_mapping)} videos")
    print()
    print("Color assignments (randomized per video):")
    for video, mapping in sorted(color_mapping.items()):
        print(f"  {video}: {mapping}")

if __name__ == "__main__":
    main()
