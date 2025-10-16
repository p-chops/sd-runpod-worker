import os
import csv
import threading
from tqdm import tqdm
import random
from multiprocessing import Process, Queue, Value
import time
from caching_img2img import CachingImg2ImgClient

def load_scenes(scenes_csv):
    scenes = []
    with open(scenes_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            scenes.append(row)
    return scenes

def get_scene_ranges(scenes, total_frames):
    ranges = []
    for i, scene in enumerate(scenes):
        start = int(scene['frame'])
        end = int(scenes[i+1]['frame']) - 1 if i+1 < len(scenes) else total_frames - 1
        ranges.append((scene['name'], start, end, scene.get('prompt', '').strip()))
    return ranges

def worker(q, cache_dir, output_dir, start_time, counter, total_frames):
    from caching_img2img import CachingImg2ImgClient
    client = CachingImg2ImgClient(cache_dir)
    # total_frames is now passed as an argument
    while True:
        item = q.get()
        if item is None:
            break
        frame_num, input_path, prompt = item
        output_path = os.path.join(output_dir, f"frame_{frame_num:05d}.png")
        try:
            start = time.time()
            result_data = client.get_or_run(input_path, prompt)
            end = time.time()
            latency_ms = int((end - start) * 1000)
            with open(output_path, "wb") as f:
                f.write(result_data)
            with counter.get_lock():
                counter.value += 1
                total_written = counter.value
            elapsed = end - start_time.value
            frame_rate = total_written / elapsed if elapsed > 0 else 0.0
            percent_complete = (total_written / total_frames) * 100 if total_frames > 0 else 0.0
            # compute ETA based on current frame_rate and remaining frames
            remaining = max(total_frames - total_written, 0)
            if remaining == 0:
                eta_str = "00:00:00"
            elif frame_rate > 0:
                eta_seconds = remaining / frame_rate
                eta_str = time.strftime("%H:%M:%S", time.gmtime(int(round(eta_seconds))))
            else:
                eta_str = "N/A"
            print(f"Wrote {output_path} in {latency_ms:05d} ms | {frame_rate:.2f} fps | {percent_complete:.1f}% complete | ETA: {eta_str}")
        except Exception as e:
            print(f"Error processing {input_path}: {e}")

def main(input_dir, output_dir, scenes_csv, cache_dir, scene_names=None, threads=10, no_cache=False):
    frame_files = sorted([f for f in os.listdir(input_dir) if f.startswith('frame_') and f.endswith('.png')])
    total_frames = len(frame_files)
    scenes = load_scenes(scenes_csv)
    scene_ranges = get_scene_ranges(scenes, total_frames)
    if scene_names:
        scene_names_set = set(scene_names)
        scene_ranges = [r for r in scene_ranges if r[0] in scene_names_set]
    os.makedirs(output_dir, exist_ok=True)
    client = CachingImg2ImgClient(cache_dir if not no_cache else None)

    # Extract prompts and update the prompt-to-hash mapping
    prompts = [scene[3] for scene in scene_ranges if scene[3]]
    client.update_prompt_hashes(prompts)

    # Build frame queue
    frame_queue = []
    for scene_name, start, end, prompt in scene_ranges:
        print(f"Queueing scene '{scene_name}' frames {start}-{end} with prompt: {prompt}")
        for frame_num in range(start, end+1):
            input_path = os.path.join(input_dir, f"frame_{frame_num:05d}.png")
            if not os.path.exists(input_path):
                print(f"Warning: {input_path} not found, skipping.")
                continue
            frame_queue.append((frame_num, input_path, prompt))
    random.shuffle(frame_queue)
    from multiprocessing import Value
    q = Queue()
    for item in frame_queue:
        q.put(item)
    # Shared start time and counter
    start_time = Value('d', time.time())
    counter = Value('i', 0)
    total_frames = len(frame_queue)
    # Start processes
    processes = []
    for _ in range(threads):
        p = Process(target=worker, args=(q, cache_dir if not no_cache else None, output_dir, start_time, counter, total_frames))
        p.start()
        processes.append(p)
    for _ in range(threads):
        q.put(None)
    for p in processes:
        p.join()

def parse_scene_names(s):
    return s.split(",") if s else None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parallel batch process frames by scene using caching img2img.")
    parser.add_argument("input_dir", help="Directory containing input frames named frame_{frame_number}.png")
    parser.add_argument("output_dir", help="Directory to write processed frames.")
    parser.add_argument("--scenes-csv", default="./scenes.csv", help="Path to scenes.csv file (default: ./scenes.csv)")
    parser.add_argument("--cache-dir", default=".img2img_cache", help="Directory to store cached results.")
    parser.add_argument("--scenes", type=str, help="Comma-separated list of scene names to process (optional)")
    parser.add_argument("--threads", type=int, default=10, help="Number of parallel client threads (default: 10)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    args = parser.parse_args()
    scene_names = parse_scene_names(args.scenes)
    main(args.input_dir, args.output_dir, args.scenes_csv, args.cache_dir, scene_names, args.threads, args.no_cache)
