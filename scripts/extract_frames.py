import cv2
import os
from pathlib import Path


def parse_resize(resize_str):
    if not resize_str:
        return None
    try:
        parts = resize_str.lower().split('x')
        if len(parts) != 2:
            return None
        w = int(parts[0])
        h = int(parts[1])
        if w <= 0 or h <= 0:
            return None
        return (w, h)
    except Exception:
        return None


def extract_frames(video_path, output_dir="frames", resize=None, out_format='png', jpg_quality=95):
    """Extract all frames from video. If resize is (w,h), frames are resized before saving."""
    Path(output_dir).mkdir(exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video: {fps} fps, {frame_count} frames")

    frame_num = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize if requested
        if resize:
            frame = cv2.resize(frame, (resize[0], resize[1]), interpolation=cv2.INTER_AREA)

        # Save frame (png by default, optional jpg)
        ext = 'png' if out_format.lower() != 'jpg' else 'jpg'
        frame_path = f"{output_dir}/frame_{frame_num:05d}.{ext}"
        if ext == 'jpg':
            # JPEG quality: 0-100 (higher is better). OpenCV uses IMWRITE_JPEG_QUALITY
            cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpg_quality)])
        else:
            cv2.imwrite(frame_path, frame)
        frame_num += 1

        if frame_num % 30 == 0:
            print(f"Extracted {frame_num}/{frame_count} frames")

    cap.release()
    print(f"Done! Extracted {frame_num} frames to {output_dir}/")
    return fps


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Extract frames from a video')
    parser.add_argument('video', help='Input video path')
    parser.add_argument('--out', default='frames', help='Output directory for frames')
    parser.add_argument('--resize', default=None, help='Optional resize WxH (example: 1280x720)')
    parser.add_argument('--format', choices=['png', 'jpg'], default='png', help='Output image format (png or jpg)')
    parser.add_argument('--jpg-quality', type=int, default=95, help='JPEG quality (1-100), higher is better')

    args = parser.parse_args()
    resize = parse_resize(args.resize)
    if args.resize and not resize:
        print('Invalid --resize value. Use WIDTHxHEIGHT, e.g. 1280x720')
        exit(2)

    extract_frames(args.video, output_dir=args.out, resize=resize, out_format=args.format, jpg_quality=args.jpg_quality)
