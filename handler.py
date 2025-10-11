import os
import torch
from diffusers import AutoPipelineForImage2Image
from diffusers.utils import load_image
from PIL import Image
import base64
import io
import runpod

# --- Global Model Initialization ---
# This code runs ONLY ONCE when the worker starts.
pipeline = None

def initialize_model():
    """Loads the model onto the GPU."""
    global pipeline
    # Use half-precision for better performance
    pipeline = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/sd-turbo",
        torch_dtype=torch.float16,
        variant="fp16"
    )
    pipeline.to("cuda")
    print("--- Model Initialized ---")

# --- The Handler Function ---
# This function will be called for every API request.
def handler(job):
    """
    The main function that processes the img2img request.
    """
    global pipeline
    if pipeline is None:
        initialize_model()

    # --- 1. Parse Input ---
    job_input = job['input']
    
    # Get the base64 encoded image and decode it
    base64_image_data = job_input.get('image')
    image_data = base64.b64decode(base64_image_data)
    init_image = Image.open(io.BytesIO(image_data)).convert("RGB")

    prompt = job_input.get('prompt', 'a cinematic photo') # Default prompt
    
    # Parameters for the pipeline
    num_inference_steps = int(job_input.get('num_inference_steps', 2))
    strength = float(job_input.get('strength', 0.5))
    guidance_scale = float(job_input.get('guidance_scale', 0.0))

    # --- 2. Run Inference ---
    image = pipeline(
        prompt=prompt,
        image=init_image,
        num_inference_steps=num_inference_steps,
        strength=strength,
        guidance_scale=guidance_scale
    ).images[0]

    # --- 3. Prepare and Return Output ---
    # Convert the output PIL Image to a base64 string
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Return the result as a JSON object
    return {
        "image": img_str
    }

# --- Start the RunPod Handler ---
if __name__ == "__main__":
    runpod.serverless.start({
        "handler": handler
    })
