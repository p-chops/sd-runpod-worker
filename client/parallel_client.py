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
from dotenv import load_dotenv
from PIL import Image
import cv2  # OpenCV
from tqdm import tqdm

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# --- Validation ---
if not API_KEY or not ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set.")

def parse_dimensions(dim_string: str) -> tuple[int, int]:
    """Parses a 'WIDTHxHEIGHT' string into a (width, height) tuple."""
    try:
        width, height = map(int, dim_string.lower().split('x'))
        return width, height
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid dimensions format: '{dim_string}'. Must be 'WIDTHxHEIGHT'.")

def parse_range(range_string: str) -> tuple[int, int]:
    """Parses a 'START-END' frame range string."""
    try:
        start, end = map(int, range_string.split('-'))
        if start >= end:
            raise ValueError("Start frame must be less than end frame.")
        return start, end
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"Invalid range format: '{range_string}'. Must be 'START-END'.")

def frame_processor_worker(q, pbar, output_dir, prompt, dimensions):
    """The function that each thread will execute."""
    # (This worker function remains unchanged)
    target_dims = parse_dimensions(dimensions)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    while True:
        frame_number, frame_image = q.get()
        if frame_number is None:
            break
        try:
            resized_img = frame_image.resize(target_dims)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="PNG")
            encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
            payload = {"input": {"image": encoded_image, "prompt": prompt}}
            response = requests.post(API_URL, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            output_image_data = base64.b64decode(result['output']['image'])
            output_filename = f"frame_{frame_number:05d}.png"
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, "wb") as output_file:
                output_file.write(output_image_data)
        except Exception as e:
            print(f"\nError processing frame {frame_number}: {e}")
        finally:
            pbar.update(1)
            q.task_done()

def main():
    parser = argparse.ArgumentParser(description="Multi-threaded client to process video frames via RunPod.")
    parser.add_argument("video_path", help="Path to the input video file.")
    parser.add_argument("output_dir", help="Directory to save the processed frames.")
    parser.add_argument("prompt", help="The text prompt for all frames.")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of parallel threads. (default: 10)")
    parser.add_argument("-d", "--dimensions", default="768x328", help="Target dimensions (WIDTHxHEIGHT). (default: 768x328)")
    parser.add_argument("-r", "--range", type=str, help="Optional frame range to process, e.g., '100-500'.")
    parser.add_argument("-s", "--shuffle", action='store_true', help="Shuffle the frame processing order.")
    parser.add_argument("-o", "--overwrite", action='store_true', help="Overwrite existing frames in the output directory.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    
    # --- Determine Frame Range ---
    cap = cv2.VideoCapture(args.video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_frame, end_frame = 0, total_frames - 1

    if args.range:
        start_frame, end_frame = parse_range(args.range)
        if end_frame >= total_frames:
            print(f"Warning: End frame {end_frame} is out of bounds for video with {total_frames} frames. Clamping to max.")
            end_frame = total_frames - 1

    initial_frame_list = list(range(start_frame, end_frame + 1))
    
    # --- Filter out existing frames unless --overwrite is used ---
    if not args.overwrite:
        print("Checking for existing frames to skip...")
        frames_to_process = []
        for frame_num in tqdm(initial_frame_list, desc="Scanning"):
            output_filename = f"frame_{frame_num:05d}.png"
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
    # ... (rest of the script is the same) ...
    threads = []
    for _ in range(args.threads):
        thread = threading.Thread(target=frame_processor_worker, args=(q, pbar, args.output_dir, args.prompt, args.dimensions), daemon=True)
        thread.start()
        threads.append(thread)

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
    print("\nProcessing complete.")

if __name__ == "__main__":
    main()