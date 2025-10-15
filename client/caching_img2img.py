import os
import base64
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

if not API_KEY or not ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set.")

class CachingImg2ImgClient:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

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
        Retries on error up to max_retries times (default 3) with brief delay.
        Returns: bytes (PNG image data)
        """
        import time
        cache_path = self._cache_path(image_path, prompt)
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return f.read()
        # Not cached: call RunPod API
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
