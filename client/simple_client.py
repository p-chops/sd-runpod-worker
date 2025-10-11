import argparse
import base64
import json
import os
import requests
import time
from dotenv import load_dotenv

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
# Get API Key and Endpoint ID from environment variables
API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")

# --- Validation ---
if not API_KEY:
    raise ValueError("RUNPOD_API_KEY not found in .env file or environment.")
if not ENDPOINT_ID:
    raise ValueError("RUNPOD_ENDPOINT_ID not found in .env file or environment.")

# Construct the API URL for a synchronous request
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

def run_img2img_job(input_path: str, output_path: str, prompt: str):
    """
    Calls the RunPod endpoint to perform an img2img task and saves the result.
    """
    print(f"Processing {input_path} with prompt: '{prompt}'...")

    # 1. Read and encode the input image
    with open(input_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Construct the API payload
    payload = {
        "input": {
            "image": encoded_image,
            "prompt": prompt,
        }
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()

    # 3. Make the API call
    response = requests.post(API_URL, headers=headers, json=payload, timeout=300)

    # 4. Handle the response
    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        print(response.text)
        return

    result = response.json()
    
    if 'output' not in result or 'image' not in result.get('output', {}):
        print("Error: The API response did not contain the expected output image.")
        print("Full response:", result)
        return

    # 5. Decode and save the output image
    output_image_data = base64.b64decode(result['output']['image'])
    with open(output_path, "wb") as output_file:
        output_file.write(output_image_data)
        
    end_time = time.time()
    
    print(f"Success! Image saved to {output_path}")
    print(f"Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI client for RunPod SD-Turbo img2img endpoint.")
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the output image file.")
    parser.add_argument("prompt", help="The text prompt to guide the image generation.")
    
    args = parser.parse_args()
    
    run_img2img_job(args.input_image, args.output_image, args.prompt)
