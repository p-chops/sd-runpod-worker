import cv2
import os
import json
import numpy as np
import re
import argparse
import sys

def find_scene_cuts(frames_dir, output_csv_path, threshold=0.8):
    """
    Detects scene cuts by comparing color histograms of consecutive frames.

    Args:
        frames_dir (str): The directory containing the input frames.
        output_csv_path (str): The path to the output JSON file.
        threshold (float): The threshold for detecting a scene cut. Higher values
                           mean the difference must be more significant to be
                           considered a cut. Experimentation is key.
    """
    # Get a sorted list of frame image files
    try:
        # This regex helps extract numbers correctly for sorting
        def get_frame_number(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else -1

        frame_files = sorted(
            [f for f in os.listdir(frames_dir) if f.endswith(('.png', '.jpg', '.jpeg'))],
            key=get_frame_number
        )

        if not frame_files:
            print(f"Error: No image files found in '{frames_dir}'")
            return

    except FileNotFoundError:
        print(f"Error: The directory '{frames_dir}' does not exist.")
        return

    cuts = []
    prev_hist = None

    print(f"Processing {len(frame_files)} frames...")

    for i, frame_filename in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_filename)
        frame = cv2.imread(frame_path)
        
        if frame is None:
            print(f"Warning: Could not read frame {frame_filename}. Skipping.")
            continue

        # Convert frame to HSV color space, which is often better for this task
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Calculate the histogram for the Hue channel
        # Using 50 bins for Hue, with a range of 0-179
        current_hist = cv2.calcHist([hsv_frame], [0], None, [50], [0, 180])
        
        # Normalize the histogram so comparisons are consistent
        cv2.normalize(current_hist, current_hist, 0, 1, cv2.NORM_MINMAX)

        if prev_hist is not None:
            # Compare the current histogram with the previous one
            # Using Chi-Squared distance: lower value means more similar
            # We are looking for a value that is NOT similar, so a value
            # greater than our threshold.
            diff = cv2.compareHist(prev_hist, current_hist, cv2.HISTCMP_CHISQR_ALT)

            if diff > threshold:
                frame_number = get_frame_number(frame_filename)
                print(f"Scene cut detected at frame {frame_number} (Difference: {diff:.4f})")
                cuts.append(frame_number)
        
        prev_hist = current_hist

    # Write the results to a CSV file
    
    with open(output_csv_path, 'w') as f:
        f.write("name,frame,prompt\n")
        for i, cut in enumerate(cuts):
            f.write(f"scene{i},{cut},\n")

    print(f"\nDetection complete. Found {len(cuts)} cuts.")
    print(f"Results saved to '{output_csv_path}'")

# --- HOW TO USE ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Detect scene cuts by comparing color histograms of consecutive frames.'
    )
    parser.add_argument('frames_dir', help='Directory containing frame images (png/jpg/jpeg)')
    parser.add_argument('output_csv', nargs='?', default='scenes.csv', help="Output CSV path (default: scenes.csv)")
    parser.add_argument('--threshold', type=float, default=0.8, help='Chi-squared diff threshold for cut detection (default: 0.8)')
    args = parser.parse_args()

    if not os.path.isdir(args.frames_dir):
        print(f"Error: input directory does not exist: {args.frames_dir}", file=sys.stderr)
        sys.exit(2)

    try:
        find_scene_cuts(args.frames_dir, args.output_csv, args.threshold)
    except Exception as e:
        print(f"Error processing frames: {e}", file=sys.stderr)
        sys.exit(1)