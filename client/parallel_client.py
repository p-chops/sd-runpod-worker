import argparse
import base64
import json
import os
import requests
import time
import io
import threading
import random
from queue import Queue
import hashlib
import shutil
import cv2

# --- Load environment variables from .env file ---
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# --- Validation ---
if not API_KEY or not ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set.")
def parse_dimensions(dim_string: str) -> tuple:
    """Parses a 'WIDTHxHEIGHT' string into a (width, height) tuple."""
    try:
        width, height = map(int, dim_string.lower().split('x'))
        return (width, height)
    except Exception:
        raise ValueError(f"Invalid dimensions format: '{dim_string}'. Must be 'WIDTHxHEIGHT'.")
import argparse
import base64
import json
import os
import requests
import time
import io
import threading
import random
from queue import Queue
import hashlib
import shutil

def frame_processor_worker(q, pbar, output_dir, prompt, dimensions, simple_output_dir=None):
    target_dims = parse_dimensions(dimensions)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    def get_cache_key(frame_number, prompt):
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:8]
        return f"frame_{frame_number:05d}_{prompt_hash}.png"

    while True:
        frame_number, frame_image = q.get()
        if frame_number is None:
            break
        try:
            output_filename = get_cache_key(frame_number, prompt)
            output_path = os.path.join(output_dir, output_filename)
            # Check cache: if file exists, skip API call
            if os.path.exists(output_path):
                # Already cached, just update progress
                # Also copy to simple output dir if requested
                if simple_output_dir:
                    simple_name = f"frame_{frame_number:05d}.png"
                    simple_path = os.path.join(simple_output_dir, simple_name)
                    if not os.path.exists(simple_path):
                        shutil.copy2(output_path, simple_path)
                pbar.update(1)
                q.task_done()
                continue

            resized_img = frame_image.resize(target_dims)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="PNG")
            encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
            payload = {"input": {"image": encoded_image, "prompt": prompt}}
            response = requests.post(API_URL, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            output_image_data = base64.b64decode(result['output']['image'])
            with open(output_path, "wb") as output_file:
                output_file.write(output_image_data)
            # Write/copy to simple output dir if requested
            if simple_output_dir:
                simple_name = f"frame_{frame_number:05d}.png"
                simple_path = os.path.join(simple_output_dir, simple_name)
                with open(simple_path, "wb") as simple_file:
                    simple_file.write(output_image_data)
        except Exception as e:
            print(f"\nError processing frame {frame_number}: {e}")
        finally:
            pbar.update(1)
            q.task_done()

def main():

    import csv

    parser = argparse.ArgumentParser(description="Multi-threaded client to process video frames via RunPod.")
    parser.add_argument("video_path", help="Path to the input video file.")
    parser.add_argument("output_dir", help="Directory to save the processed frames.")
    parser.add_argument("--scenes-csv", type=str, required=True, help="Path to scenes.csv file.")
    parser.add_argument("--scene", type=str, required=True, help="Scene name to process.")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of parallel threads. (default: 10)")
    parser.add_argument("-d", "--dimensions", default="768x328", help="Target dimensions (WIDTHxHEIGHT). (default: 768x328)")
    parser.add_argument("-s", "--shuffle", action='store_true', help="Shuffle the frame processing order.")
    parser.add_argument("-o", "--overwrite", action='store_true', help="Overwrite existing frames in the output directory.")
    parser.add_argument("--simple-output-dir", type=str, help="Optional: directory to write frames as frame_{frame_number}.png (no prompt hash)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    if args.simple_output_dir:
        os.makedirs(args.simple_output_dir, exist_ok=True)


    # --- Parse scenes.csv and get frame range and prompt for the selected scene ---
    scenes = []
    with open(args.scenes_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            scenes.append(row)

    # Find the selected scene and its frame range
    scene_idx = None
    for i, scene in enumerate(scenes):
        if scene['name'] == args.scene:
            scene_idx = i
            break
    if scene_idx is None:
        raise ValueError(f"Scene '{args.scene}' not found in {args.scenes_csv}")

    start_frame = int(scenes[scene_idx]['frame'])
    if scene_idx + 1 < len(scenes):
        end_frame = int(scenes[scene_idx + 1]['frame']) - 1
    else:
        # Last scene: go to end of video
        import cv2
        cap = cv2.VideoCapture(args.video_path)
        end_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        cap.release()

    prompt = scenes[scene_idx].get('prompt', '').strip()
    if not prompt:
        raise ValueError(f"Prompt not found for scene '{args.scene}' in {args.scenes_csv}")

    # --- Determine Frame Range ---
    initial_frame_list = list(range(start_frame, end_frame + 1))

    # --- Filter out existing frames unless --overwrite is used ---
    import hashlib
    def get_cache_key(frame_number, prompt):
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:8]
        return f"frame_{frame_number:05d}_{prompt_hash}.png"

    if not args.overwrite:
        print("Checking for existing frames to skip...")
        frames_to_process = []
        from tqdm import tqdm
        for frame_num in tqdm(initial_frame_list, desc="Scanning"):
            output_filename = get_cache_key(frame_num, prompt)
            output_path = os.path.join(args.output_dir, output_filename)
            if not os.path.exists(output_path):
                frames_to_process.append(frame_num)
        skipped_count = len(initial_frame_list) - len(frames_to_process)
        print(f"Found {skipped_count} existing frames. Skipping them.")
    else:
        print("Overwrite flag is set. All frames in range will be processed.")
        frames_to_process = initial_frame_list

    if not frames_to_process:
        print("No frames to process. Exiting.")
        return

    if args.shuffle:
        print("Shuffling frame order...")
        random.shuffle(frames_to_process)

    # --- Setup Queue, Progress Bar, and Workers ---
    q = Queue(maxsize=args.threads * 2)
    pbar = tqdm(total=len(frames_to_process), unit="frames", desc="Processing Video")
    threads = []
    for _ in range(args.threads):
        thread = threading.Thread(target=frame_processor_worker, args=(q, pbar, args.output_dir, prompt, args.dimensions, args.simple_output_dir), daemon=True)
        thread.start()
        threads.append(thread)

    cap = cv2.VideoCapture(args.video_path)
    for frame_num in frames_to_process:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Could not read frame {frame_num}. Skipping.")
            pbar.total -=1
            pbar.refresh()
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        q.put((frame_num, pil_image))

    q.join()
    for _ in range(args.threads):
        q.put((None, None))
    for thread in threads:
        thread.join()

    cap.release()
    pbar.close()
    from tqdm import tqdm
    import cv2
    from PIL import Image
    print("\nProcessing complete.")

if __name__ == "__main__":
    main()