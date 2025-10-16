import os
import base64
import hashlib
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

if not API_KEY or not ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set.")

class CachingImg2ImgClient:
    PROMPT_HASH_FILE = "prompt_hashes.json"

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        self.prompt_hash_file = os.path.join(cache_dir, self.PROMPT_HASH_FILE)
        self.prompt_hashes = self._load_prompt_hashes()

    def _load_prompt_hashes(self):
        """Load the prompt-to-hash mapping from the JSON file."""
        if os.path.exists(self.prompt_hash_file):
            with open(self.prompt_hash_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_prompt_hashes(self):
        """Save the prompt-to-hash mapping to the JSON file."""
        os.makedirs(os.path.dirname(self.prompt_hash_file), exist_ok=True)
        with open(self.prompt_hash_file, 'w') as f:
            json.dump(self.prompt_hashes, f, indent=4)

    def compute_hash_prefix(self, prompt):
        """Compute a hash prefix for a given prompt."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:8]

    def update_prompt_hashes(self, prompts):
        """Update the JSON file with new prompts."""
        for prompt in prompts:
            if prompt not in self.prompt_hashes:
                self.prompt_hashes[prompt] = self.compute_hash_prefix(prompt)
        self._save_prompt_hashes()

    def get_hash_prefix(self, prompt):
        """Retrieve the hash prefix for a given prompt."""
        return self.prompt_hashes.get(prompt)

    def _cache_key(self, image_path, prompt):
        """Generate a cache key: frame_{frame number}_{prompt hash}.png (prompt hash: 8 hex digits)."""
        import re
        basename = os.path.basename(image_path)
        match = re.match(r"frame_(\d+)", basename)
        if match:
            frame_number = match.group(1)
        else:
            frame_number = "unknown"
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"frame_{frame_number}_{prompt_hash}.png"

    def _cache_path(self, image_path, prompt):
        return os.path.join(self.cache_dir, self._cache_key(image_path, prompt))

    def get_or_run(self, image_path, prompt, max_retries=3, retry_delay=0.5):
        """
        If cached, return image data from cache. Otherwise, call RunPod API, cache, and return image data.
        If cache_dir is None, always call RunPod API and do not read/write cache files.
        Retries on error up to max_retries times (default 3) with brief delay.
        Returns: bytes (PNG image data)
        """
        import time
        cache_enabled = self.cache_dir is not None
        cache_path = self._cache_path(image_path, prompt) if cache_enabled else None
        if cache_enabled and os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return f.read()
        # Not cached or caching disabled: call RunPod API
        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")
        payload = {"input": {"image": encoded_image, "prompt": prompt}}
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(API_URL, headers=headers, json=payload, timeout=300)
                response.raise_for_status()
                result = response.json()
                output_image_data = base64.b64decode(result['output']['image'])
                if cache_enabled:
                    with open(cache_path, "wb") as f:
                        f.write(output_image_data)
                return output_image_data
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    print(f"Failed after {max_retries} attempts: {e}")
        raise last_exception

    def clear_cache_except(self, prompts_to_keep, dry_run=False):
        """
        Clears the cache of all data except for the specified prompts.

        Args:
            prompts_to_keep (list of str): Prompts whose cached data should be retained.
            dry_run (bool): If True, log deletion decisions without actually deleting files.
        """
        if not self.cache_dir:
            print("Cache directory is not set. Skipping cache clearing.")
            return

        # Generate a set of cache keys to keep based on the prompts
        keys_to_keep = set(self._generate_cache_key(prompt) for prompt in prompts_to_keep)

        # Iterate through cache directory and log/remove files not matching the keys
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            if not os.path.isfile(filepath):
                continue

            # Extract the hash prefix from the filename (e.g., frame_{frame number}_{hash prefix})
            parts = filename.split("_")
            if len(parts) < 3:
                print(f"Skipping unrecognized file format: {filename}")
                continue
            hash_prefix = parts[-1]  # The last part is the hash prefix

            if hash_prefix not in keys_to_keep:
                if dry_run:
                    print(f"[DRY RUN] Would remove cached file: {filepath}")
                else:
                    os.remove(filepath)
                    print(f"Removed cached file: {filepath}")

    def _generate_cache_key(self, prompt):
        """
        Generates a cache key for a given prompt. This method should match the logic
        used when creating cache keys for storing results.

        Args:
            prompt (str): The prompt to generate a cache key for.

        Returns:
            str: The cache key.
        """
        # Example: Hash the prompt to create a unique cache key
        import hashlib
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()
