#!/usr/bin/env python3
"""
Render a numbered PNG frame sequence (e.g. frame_01324.png) combined with an audio file
using ffmpeg. Frame rate is taken from a source video via ffprobe.

Defaults are set as constants at the top; override via CLI arguments.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Optional, Tuple

# Default placeholders - edit as needed
DEFAULT_FRAME_DIR = 'input/frames'
DEFAULT_AUDIO_FILE = "input/audio.wav"        # path to audio file (can be omitted)
DEFAULT_SOURCE_VIDEO = "input/original.mp4"    # video to read fps from
DEFAULT_OUTPUT = "output/output.mp4"                       # default output filename
DEFAULT_QUALITY = "good"                         # one of: small, good, uncompressed

# Supported quality presets
QUALITY_PRESETS = ("small", "good", "uncompressed")


def find_sequence_pattern(frame_dir: str) -> Tuple[str, int]:
    """
    Inspect frame_dir for files matching prefix + number + .png
    Return (pattern, start_number) where pattern is like 'frame_%05d.png'
    and start_number is the lowest index found.
    """
    files = os.listdir(frame_dir)
    pngs = [f for f in files if f.lower().endswith(".png")]
    if not pngs:
        raise FileNotFoundError(f"No PNG files found in {frame_dir}")

    # find a filename that contains a number
    sample = None
    for name in pngs:
        if re.search(r"(\d+)\.png$", name):
            sample = name
            break
    if not sample:
        raise ValueError("No numbered PNG filenames found (expected like frame_01324.png)")

    m = re.search(r"^(.*?)(\d+)\.png$", sample)
    prefix = m.group(1)
    padding = len(m.group(2))

    # collect all numbers that match this prefix and padding
    pattern_re = re.compile(r"^" + re.escape(prefix) + r"(\d{" + str(padding) + r"})\.png$")
    numbers = []
    for name in pngs:
        mo = pattern_re.match(name)
        if mo:
            numbers.append(int(mo.group(1)))
    if not numbers:
        raise ValueError("No matching numbered frames found for detected prefix")

    start = min(numbers)
    pattern = f"{prefix}%0{padding}d.png"
    return pattern, start


def get_fps_from_video(src_video: str) -> float:
    """Use ffprobe to extract average frame rate as float."""
    if not shutil.which("ffprobe"):
        raise EnvironmentError("ffprobe not found in PATH")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        src_video,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
    s = proc.stdout.strip()
    # avg_frame_rate can be like "30000/1001" or "25/1"
    if "/" in s:
        num, den = s.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(s)
    return fps


def build_ffmpeg_cmd(frame_dir: str, pattern: str, start: int, fps: float,
                     audio_file: Optional[str], output: str, quality: str, sharpness: float) -> list:
    """Construct ffmpeg command for the chosen quality preset."""
    if not shutil.which("ffmpeg"):
        raise EnvironmentError("ffmpeg not found in PATH")

    input_pattern = os.path.join(frame_dir, pattern)

    fxopts = []
    if sharpness > 0.0:
        fxopts += ["-vf", f"unsharp=5:5:{sharpness}:5:5:{sharpness}"]

    # video codec and options per preset
    if quality == "small":
        vcodec_opts = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p"]
        aopts = ["-c:a", "aac", "-b:a", "192k"]
    elif quality == "good":
        vcodec_opts = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
        aopts = ["-c:a", "aac", "-b:a", "320k"]
    elif quality == "uncompressed":
        # lossless-like output (very large). Uses libx264 lossless for wide compatibility.
        vcodec_opts = ["-c:v", "libx264", "-preset", "veryslow", "-crf", "0", "-pix_fmt", "yuv444p"]
        aopts = ["-c:a", "copy"] if audio_file else []
    else:
        raise ValueError(f"Unknown quality preset: {quality}")

    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", input_pattern]
    if audio_file:
        cmd += ["-i", audio_file]
    # map streams: default mapping is okay, but ensure shortest to stop if audio shorter/longer
    cmd += vcodec_opts
    cmd += aopts
    cmd += fxopts
    # keep video and audio in sync and stop when the shorter stream ends
    cmd += ["-shortest", output]
    return cmd


def run(cmd: list) -> int:
    print("Running:", " ".join(shlex.quote(x) for x in cmd))
    proc = subprocess.run(cmd)
    return proc.returncode


def parse_args():
    p = argparse.ArgumentParser(description="Render numbered PNG frames + audio into a video using ffmpeg")
    p.add_argument("--frame-dir", default=DEFAULT_FRAME_DIR, help="Directory with frames (numbered PNGs)")
    p.add_argument("--audio", default=DEFAULT_AUDIO_FILE, help="Optional audio file to combine (omit or empty to skip)")
    p.add_argument("--source-video", default=DEFAULT_SOURCE_VIDEO, help="Video to probe for frame rate")
    p.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="Output filename")
    p.add_argument("--quality", "-q", default=DEFAULT_QUALITY, choices=QUALITY_PRESETS, help="Quality preset")
    p.add_argument("--sharpness", type=float, default=0.0, help="Unsharp mask amount")
    return p.parse_args()


def main():
    args = parse_args()

    frame_dir = args.frame_dir
    audio = args.audio if args.audio else None
    src_video = args.source_video
    output = args.output
    quality = args.quality
    sharpness = args.sharpness

    if not os.path.isdir(frame_dir):
        print(f"Frame directory not found: {frame_dir}", file=sys.stderr)
        sys.exit(2)

    try:
        pattern, start = find_sequence_pattern(frame_dir)
    except Exception as e:
        print(f"Error detecting frame sequence: {e}", file=sys.stderr)
        sys.exit(3)

    try:
        fps = get_fps_from_video(src_video)
    except Exception as e:
        print(f"Error probing source video for fps: {e}", file=sys.stderr)
        sys.exit(4)

    try:
        cmd = build_ffmpeg_cmd(frame_dir, pattern, 0, fps, audio, output, quality, sharpness)
    except Exception as e:
        print(f"Error building ffmpeg command: {e}", file=sys.stderr)
        sys.exit(5)

    print(f"Running ffmpeg command: {' '.join(cmd)}")
    rc = run(cmd)
    if rc != 0:
        print(f"ffmpeg exited with code {rc}", file=sys.stderr)
        sys.exit(rc)
    print(f"Rendered {output} (fps={fps}, start={start}, pattern={pattern}, quality={quality})")


if __name__ == "__main__":
    main()
