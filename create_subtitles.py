#!/usr/bin/env python3
"""
Create ASS subtitle files from JSON outputs.
Combines both base and finetuned model outputs with different colors.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get output directory from command line argument or default
if len(sys.argv) > 1:
    OUTPUT_DIR = Path(sys.argv[1])
else:
    # Find the most recent run directory
    base_output = Path(os.getenv("OUTPUT_DIR", "./output"))
    run_dirs = sorted(base_output.glob("run_*"))
    if run_dirs:
        OUTPUT_DIR = run_dirs[-1]
    else:
        print("ERROR: No run directories found! Run inference first.")
        sys.exit(1)

JSON_DIR = OUTPUT_DIR / "json"
SUBTITLE_DIR = OUTPUT_DIR / "subtitles"

# Create subtitle output directory
SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)

# ASS subtitle template
ASS_HEADER = """[Script Info]
Title: Model Comparison Subtitles
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BaseModel,Arial,14,&H00FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,50,1
Style: FinetunedModel,Arial,14,&H00FFFF00,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def time_to_ass_format(time_str: str) -> str:
    """Convert MM:SS to ASS timestamp format (H:MM:SS.CS)."""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                mm, ss = parts
                return f"0:{mm}:{ss}.00"
            elif len(parts) == 3:
                hh, mm, ss = parts
                return f"{hh}:{mm}:{ss}.00"
        return "0:00:00.00"
    except:
        return "0:00:00.00"


def create_ass_subtitle(video_name: str, model1_json_path: Path, model2_json_path: Path) -> str:
    """Create a combined ASS subtitle file from both model outputs."""
    
    # Load JSON files
    with open(model1_json_path, 'r') as f:
        model1_data = json.load(f)
    
    with open(model2_json_path, 'r') as f:
        model2_data = json.load(f)
    
    # Start with header
    ass_content = ASS_HEADER
    
    # Add model1 segments (BaseModel style - Yellow/Cyan at bottom)
    model1_segments = model1_data.get("cutSegments", [])
    for segment in model1_segments:
        start = time_to_ass_format(segment.get("start", "00:00"))
        end = time_to_ass_format(segment.get("end", "00:00"))
        description = segment.get("description", "")
        
        text = description
        # Escape special characters in ASS format
        text = text.replace('\n', '\\N')
        
        ass_content += f"Dialogue: 0,{start},{end},BaseModel,,0,0,0,,{text}\n"
    
    # Add model2 segments (FinetunedModel style - Yellow at top)
    model2_segments = model2_data.get("cutSegments", [])
    for segment in model2_segments:
        start = time_to_ass_format(segment.get("start", "00:00"))
        end = time_to_ass_format(segment.get("end", "00:00"))
        description = segment.get("description", "")
        
        text = description
        # Escape special characters in ASS format
        text = text.replace('\n', '\\N')
        
        ass_content += f"Dialogue: 0,{start},{end},FinetunedModel,,0,0,0,,{text}\n"
    
    return ass_content


def main():
    """Main execution function."""
    print("=" * 80)
    print("Creating ASS Subtitle Files")
    print("=" * 80)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Reading JSON files from: {JSON_DIR}")
    print(f"Saving subtitles to: {SUBTITLE_DIR}")
    print()
    
    # Find all JSON files and group by video name
    all_json_files = sorted(JSON_DIR.glob("*.json"))
    
    if not all_json_files:
        print("ERROR: No JSON files found!")
        print(f"Make sure you've run 'python run_inference.py' first.")
        return
    
    # Group files by video name (everything before the last _)
    video_dict = {}
    for json_path in all_json_files:
        # Extract video name and model name
        # Format: videoname_modelname.json
        parts = json_path.stem.rsplit('_', 1)
        if len(parts) == 2:
            video_name, model_name = parts
            if video_name not in video_dict:
                video_dict[video_name] = {}
            video_dict[video_name][model_name] = json_path
    
    print(f"Found {len(video_dict)} videos to process")
    print()
    
    # Process each video
    for video_name, models in sorted(video_dict.items()):
        # We need at least 2 models to compare
        if len(models) < 2:
            print(f"⚠ Skipping {video_name}: Only found {len(models)} model output(s)")
            continue
        
        # Get the two model JSONs (first two alphabetically)
        model_names = sorted(models.keys())
        model1_name = model_names[0]
        model2_name = model_names[1]
        
        model1_json_path = models[model1_name]
        model2_json_path = models[model2_name]
        
        print(f"Processing: {video_name} (comparing {model1_name} vs {model2_name})")
        
        try:
            # Create combined ASS subtitle
            ass_content = create_ass_subtitle(video_name, model1_json_path, model2_json_path)
            
            # Save ASS file
            ass_output_path = SUBTITLE_DIR / f"{video_name}.ass"
            with open(ass_output_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            print(f"  ✓ Created: {ass_output_path}")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    
    print()
    print("=" * 80)
    print("✓ Subtitle creation complete!")
    print(f"  ASS files saved to: {SUBTITLE_DIR}")
    print()
    print("Next step:")
    print(f"  Run: python burn_subtitles.py {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()

