import os
import csv
from caching_img2img import CachingImg2ImgClient

# Usage: python batch_scene_img2img.py input_frames_dir output_frames_dir scenes.csv
# Each frame in input_frames_dir should be named frame_{frame_number}.png

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

def main(input_dir, output_dir, scenes_csv, cache_dir, scene_names=None):
    # Find total frames by listing input_dir
    frame_files = sorted([f for f in os.listdir(input_dir) if f.startswith('frame_') and f.endswith('.png')])
    total_frames = len(frame_files)
    scenes = load_scenes(scenes_csv)
    scene_ranges = get_scene_ranges(scenes, total_frames)
    if scene_names:
        scene_names_set = set(scene_names)
        scene_ranges = [r for r in scene_ranges if r[0] in scene_names_set]
    os.makedirs(output_dir, exist_ok=True)
    client = CachingImg2ImgClient(cache_dir)
    for scene_name, start, end, prompt in scene_ranges:
        print(f"Processing scene '{scene_name}' frames {start}-{end} with prompt: {prompt}")
        for frame_num in range(start, end+1):
            input_path = os.path.join(input_dir, f"frame_{frame_num:05d}.png")
            output_path = os.path.join(output_dir, f"frame_{frame_num:05d}.png")
            if not os.path.exists(input_path):
                print(f"Warning: {input_path} not found, skipping.")
                continue
            result_data = client.get_or_run(input_path, prompt)
            with open(output_path, "wb") as f:
                f.write(result_data)
            print(f"Wrote {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch process frames by scene using caching img2img.")
    parser.add_argument("input_dir", help="Directory containing input frames named frame_{frame_number}.png")
    parser.add_argument("output_dir", help="Directory to write processed frames.")
    parser.add_argument("--scenes-csv", default="./scenes.csv", help="Path to scenes.csv file (default: ./scenes.csv)")
    parser.add_argument("--cache-dir", default=".img2img_cache", help="Directory to store cached results.")
    parser.add_argument("--scenes", type=str, help="Comma-separated list of scene names to process (optional)")
    args = parser.parse_args()
    scene_names = args.scenes.split(",") if args.scenes else None
    main(args.input_dir, args.output_dir, args.scenes_csv, args.cache_dir, scene_names)
