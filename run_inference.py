#!/usr/bin/env python3
"""
Run inference on videos using both base Gemini 2.5 Pro and finetuned model.
Saves JSON outputs for comparison.
"""

import os
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION")
FINETUNED_ENDPOINT = os.getenv("FINETUNED_MODEL_ENDPOINT")
BASE_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))

# Create timestamped output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = BASE_OUTPUT_DIR / f"run_{timestamp}"
JSON_OUTPUT_DIR = OUTPUT_DIR / "json"
JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Default prompts
DEFAULT_PROMPT = """You're watching an egocentric video, of a factory operator performing a task. Your goal is to understand how the task is performed, and identify all the steps. You must NOT miss any of the steps the factory operator is performing. You must NOT hallucinate any of the steps either.

You have to analyze the states of the object being manipulated at each step, and reason if your current flow of step makes sense.

This is how you identify the missing steps.

Example:
{
  "cutSegments": [
    {
      "start": "00:00",
      "end": "00:05",
      "label": "pick_item",
      "description": "The operator picks up an item from the tray"
    },
    {
      "start": "00:05",
      "end": "00:10",
      "label": "align_item",
      "description": "The operator aligns the item against the fixture"
    },
    {
      "start": "00:10",
      "end": "00:15",
      "label": "secure_item",
      "description": "The operator presses the item down to secure it"
    }
  ]
}

Return ONLY a valid JSON object with this exact structure. Do not include any other text, markdown formatting, or code blocks."""

GRANULAR_TIMESTAMP_PROMPT = """Identify the task steps performed in this egocentric factory video and return them in JSON format:

{cutSegments:[{start,end,label,description}]}

- Use timestamps in the format MM:SS.ss (minutes, seconds, hundredths).
- Always include two decimal places for seconds (e.g., 01:44.44).
- Keep the output strictly valid JSON matching the schema above.
- Do not include any extra text outside the JSON."""

NUMBERED_LIST_PROMPT = """You are watching an egocentric video recorded by a factory worker performing a task. Your job is to format the sequence of steps as clear instructions for how to perform this job. Output the result as an ordered numbered list, where each line is a concise instruction describing one distinct action. 

Format each step as an instruction on how to do the job (e.g., "Pick up the screw from the bin" rather than "The worker picks up a screw").

Focus only on what the wearer is doing with their hands, tools, and materials. Ignore actions by other people in the background. Do not include timestamps or JSON. Do not mention camera movement or unrelated actions.

Do not assume steps. Only include what is explicitly seen in the video."""


def list_videos_from_gcs(gcs_path: str) -> List[str]:
    """List videos from GCS bucket matching sample1-sample10 pattern."""
    # Parse GCS path (format: gs://bucket/prefix or bucket/prefix)
    gcs_path = gcs_path.replace("gs://", "")
    parts = gcs_path.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    
    # Ensure prefix ends with / if it exists
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'
    
    print(f"Listing videos from gs://{bucket_name}/{prefix}...")
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    
    video_uris = []
    for blob in blobs:
        # Only get files in the root of the prefix (not subfolders)
        relative_path = blob.name[len(prefix):] if prefix else blob.name
        if '/' in relative_path:
            continue
        
        # Get all video files (mp4, mov, avi)
        if blob.name.endswith(('.mp4', '.mov', '.avi', '.MP4', '.MOV', '.AVI')):
            video_uri = f"gs://{bucket_name}/{blob.name}"
            video_uris.append(video_uri)
    
    video_uris = sorted(set(video_uris))
    print(f"Found {len(video_uris)} videos:")
    for uri in video_uris:
        print(f"  - {uri}")
    
    return video_uris


def run_inference(model: GenerativeModel, video_uri: str, prompt: str = None, expect_json: bool = True) -> Dict[str, Any]:
    """Run inference on a video using the specified model."""
    print(f"  Running inference on {video_uri.split('/')[-1]}...")
    
    # Create video part from GCS URI
    video_part = Part.from_uri(video_uri, mime_type="video/mp4")
    
    # Generate content with or without prompt
    if prompt:
        response = model.generate_content([prompt, video_part])
    else:
        response = model.generate_content([video_part])
    
    # Extract text from response
    response_text = response.text.strip()
    
    # If not expecting JSON (numbered list format), return as-is
    if not expect_json:
        return {
            "format": "numbered_list",
            "steps": response_text
        }
    
    # Try to parse as JSON
    # Sometimes the model wraps it in markdown code blocks, so clean that up
    if response_text.startswith("```"):
        # Remove markdown code blocks
        lines = response_text.split('\n')
        response_text = '\n'.join([
            line for line in lines 
            if not line.startswith("```")
        ]).strip()
    
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError as e:
        print(f"    WARNING: Failed to parse JSON response: {e}")
        print(f"    Raw response: {response_text[:500]}")
        # Return a fallback structure
        return {
            "cutSegments": [],
            "error": "Failed to parse JSON",
            "raw_response": response_text
        }


def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run inference on videos using Gemini models")
    parser.add_argument(
        "--gcs-path",
        type=str,
        default=f"{os.getenv('GCS_BUCKET', 'buildai-dataset')}/{os.getenv('GCS_PREFIX', 'finetune_dataset/')}",
        help="GCS path to videos (e.g., gs://bucket/prefix or bucket/prefix). Default from .env"
    )
    parser.add_argument(
        "--model1",
        type=str,
        default=os.getenv("FINETUNED_MODEL_ENDPOINT"),
        help="First model endpoint ID. Default from .env"
    )
    parser.add_argument(
        "--model2",
        type=str,
        default="gemini-2.5-pro",
        help="Second model endpoint ID or name. Default: gemini-2.5-pro"
    )
    parser.add_argument(
        "--model1-name",
        type=str,
        default="model1",
        help="Name for first model in output files. Default: model1"
    )
    parser.add_argument(
        "--model2-name",
        type=str,
        default="model2",
        help="Name for second model in output files. Default: model2"
    )
    parser.add_argument(
        "--model1-no-prompt",
        action="store_true",
        help="Don't send prompt to model1, just send the video"
    )
    parser.add_argument(
        "--model2-no-prompt",
        action="store_true",
        help="Don't send prompt to model2, just send the video"
    )
    parser.add_argument(
        "--model1-prompt",
        type=str,
        choices=["default", "granular", "numbered"],
        default="default",
        help="Which prompt to use for model1: 'default' (MM:SS), 'granular' (MM:SS.ss), or 'numbered' (numbered list)"
    )
    parser.add_argument(
        "--model2-prompt",
        type=str,
        choices=["default", "granular", "numbered"],
        default="default",
        help="Which prompt to use for model2: 'default' (MM:SS), 'granular' (MM:SS.ss), or 'numbered' (numbered list)"
    )
    args = parser.parse_args()
    
    # Select prompts based on arguments
    def get_prompt(prompt_type: str):
        if prompt_type == "granular":
            return GRANULAR_TIMESTAMP_PROMPT
        elif prompt_type == "numbered":
            return NUMBERED_LIST_PROMPT
        else:
            return DEFAULT_PROMPT
    
    model1_prompt = get_prompt(args.model1_prompt)
    model2_prompt = get_prompt(args.model2_prompt)
    
    print("=" * 80)
    print("Gemini Model Comparison - Video Inference")
    print("=" * 80)
    print(f"Project: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"GCS Path: {args.gcs_path}")
    print()
    print(f"Model 1 ({args.model1_name}): {args.model1}")
    if args.model1_no_prompt:
        print(f"  Prompt: NO")
    else:
        print(f"  Prompt: {args.model1_prompt.upper()}")
    print(f"Model 2 ({args.model2_name}): {args.model2}")
    if args.model2_no_prompt:
        print(f"  Prompt: NO")
    else:
        print(f"  Prompt: {args.model2_prompt.upper()}")
    print()
    
    # List videos
    video_uris = list_videos_from_gcs(args.gcs_path)
    if not video_uris:
        print("ERROR: No videos found!")
        sys.exit(1)
    
    print()
    print("-" * 80)
    print("Initializing models...")
    print("-" * 80)
    
    def load_model(model_id: str, model_name: str):
        """Load a model with error handling."""
        print(f"Loading {model_name}: {model_id}...")
        
        # Check if it's a base model name or an endpoint
        if model_id.startswith("gemini-"):
            return GenerativeModel(model_id)
        
        # Try different endpoint formats
        try:
            # Format 1: Direct endpoint reference
            return GenerativeModel(
                f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{model_id}"
            )
        except Exception as e:
            print(f"  Format 1 failed: {e}")
            try:
                # Format 2: Just the endpoint ID
                return GenerativeModel(model_id)
            except Exception as e2:
                print(f"  Format 2 failed: {e2}")
                print(f"  ERROR: Could not initialize {model_name}")
                sys.exit(1)
    
    model1 = load_model(args.model1, args.model1_name)
    model2 = load_model(args.model2, args.model2_name)
    
    print()
    print("-" * 80)
    print(f"Running inference on {len(video_uris)} videos IN PARALLEL...")
    print("-" * 80)
    
    def process_video_with_model(video_uri: str, model: GenerativeModel, model_name: str, prompt: str, prompt_type: str):
        """Process a single video with a single model."""
        video_name = video_uri.split('/')[-1].rsplit('.', 1)[0]
        output_path = JSON_OUTPUT_DIR / f"{video_name}_{model_name}.json"
        
        prompt_status = "no prompt" if prompt is None else f"with {prompt_type} prompt"
        print(f"[{model_name.upper()}] Starting {video_name} ({prompt_status})...")
        
        try:
            expect_json = prompt_type != "numbered"
            result = run_inference(model, video_uri, prompt, expect_json)
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Count segments differently based on format
            if result.get("format") == "numbered_list":
                # Count lines that start with numbers
                lines = result.get("steps", "").strip().split('\n')
                segments = sum(1 for line in lines if line.strip() and line.strip()[0].isdigit())
            else:
                segments = len(result.get("cutSegments", []))
            
            print(f"[{model_name.upper()}] ✓ {video_name}: {segments} steps")
            return (video_name, model_name, segments, None)
        except Exception as e:
            print(f"[{model_name.upper()}] ✗ {video_name}: {str(e)}")
            error_result = {"error": str(e)}
            with open(output_path, 'w') as f:
                json.dump(error_result, f, indent=2)
            return (video_name, model_name, 0, str(e))
    
    # Create all tasks (video x model combinations)
    tasks = []
    for video_uri in video_uris:
        prompt1 = None if args.model1_no_prompt else model1_prompt
        prompt2 = None if args.model2_no_prompt else model2_prompt
        prompt1_type = "none" if args.model1_no_prompt else args.model1_prompt
        prompt2_type = "none" if args.model2_no_prompt else args.model2_prompt
        tasks.append((video_uri, model1, args.model1_name, prompt1, prompt1_type))
        tasks.append((video_uri, model2, args.model2_name, prompt2, prompt2_type))
    
    # Run all tasks in parallel
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_video_with_model, video_uri, model, model_name, prompt, prompt_type): (video_uri, model_name)
            for video_uri, model, model_name, prompt, prompt_type in tasks
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    # Print summary
    print()
    print("-" * 80)
    print("Summary by video:")
    print("-" * 80)
    
    video_names = sorted(set(r[0] for r in results))
    for video_name in video_names:
        model1_result = next((r for r in results if r[0] == video_name and r[1] == args.model1_name), None)
        model2_result = next((r for r in results if r[0] == video_name and r[1] == args.model2_name), None)
        
        model1_status = f"{model1_result[2]} segments" if model1_result and not model1_result[3] else f"ERROR: {model1_result[3]}" if model1_result else "N/A"
        model2_status = f"{model2_result[2]} segments" if model2_result and not model2_result[3] else f"ERROR: {model2_result[3]}" if model2_result else "N/A"
        
        print(f"  {video_name}:")
        print(f"    {args.model1_name}: {model1_status}")
        print(f"    {args.model2_name}: {model2_status}")
    
    print()
    print("=" * 80)
    print("✓ Inference complete!")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  JSON outputs saved to: {JSON_OUTPUT_DIR}")
    print()
    print("Next steps:")
    print(f"  1. Run: python create_subtitles.py {OUTPUT_DIR}")
    print(f"  2. Run: python burn_subtitles.py {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()

