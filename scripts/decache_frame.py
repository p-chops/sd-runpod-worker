import os
import hashlib
import argparse

def compute_checksum(file_path):
    """Compute the SHA256 checksum of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def find_and_decache_frame(frame_number, cache_dir, output_dir, dry_run=False):
    """Find and decache the cached frame matching the output frame."""
    output_frame_path = os.path.join(output_dir, f"frame_{frame_number:05d}.png")
    if not os.path.exists(output_frame_path):
        print(f"Output frame not found: {output_frame_path}")
        return

    output_checksum = compute_checksum(output_frame_path)
    print(f"Checksum of output frame: {output_checksum}")

    # Search for cached frames for the given frame number
    cached_files = [
        f for f in os.listdir(cache_dir)
        if f.startswith(f"frame_{frame_number:05d}_")
    ]

    if not cached_files:
        print(f"No cached frames found for frame {frame_number} in {cache_dir}")
        return

    for cached_file in cached_files:
        cached_file_path = os.path.join(cache_dir, cached_file)
        cached_checksum = compute_checksum(cached_file_path)
        print(f"Checking cached file: {cached_file} (checksum: {cached_checksum})")

        if cached_checksum == output_checksum:
            print(f"Match found! Decaching: {cached_file_path}")
            if not dry_run:
                os.remove(cached_file_path)
                print(f"Decached: {cached_file_path}")
            else:
                print(f"[Dry Run] Would decache: {cached_file_path}")

            # Remove the output frame
            if not dry_run:
                os.remove(output_frame_path)
                print(f"Removed output frame: {output_frame_path}")
            else:
                print(f"[Dry Run] Would remove output frame: {output_frame_path}")
            return

    print(f"No matching cached frame found for frame {frame_number}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decache a specific frame by comparing checksums.")
    parser.add_argument("frame_number", type=int, help="The frame number to decache.")
    parser.add_argument("cache_dir", help="The directory containing cached frames.")
    parser.add_argument("output_dir", help="The directory containing output frames.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the changes without making modifications.")
    args = parser.parse_args()

    find_and_decache_frame(args.frame_number, args.cache_dir, args.output_dir, args.dry_run)
