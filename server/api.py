import os
import torch
from diffusers import AutoPipelineForImage2Image
from PIL import Image
import base64
import io
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from concurrent.futures import ProcessPoolExecutor

# ----------------------------
#  FastAPI App Initialization
# ----------------------------
app = FastAPI()

# ----------------------------
#  Pydantic Request Models
# ----------------------------
class Img2ImgRequest(BaseModel):
    """Defines the expected JSON input for an image generation request."""
    image: str  # Base64 encoded input image
    prompt: str
    num_inference_steps: int = 2
    strength: float = 0.5
    guidance_scale: float = 0.0

# ----------------------------
#  Global Process Pool
# ----------------------------
num_gpus = torch.cuda.device_count()
if num_gpus == 0:
    raise RuntimeError("No GPUs detected. At least one GPU is required.")

executor = ProcessPoolExecutor(max_workers=num_gpus)

def initialize_pipeline():
    """
    Initializes and returns a pipeline instance for a process.
    This function will be called once per process in the pool.
    """
    pipeline = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/sd-turbo",
        torch_dtype=torch.float16,
        variant="fp16"
    )
    pipeline.to("cuda")
    return pipeline

def run_inference_in_process(prompt: str, image_data: bytes, steps: int, strength: float, guidance: float):
    """
    Runs inference in a separate process. Each process initializes its own pipeline.
    """
    # Initialize the pipeline for the process if not already done
    if not hasattr(run_inference_in_process, "pipeline"):
        run_inference_in_process.pipeline = initialize_pipeline()
    
    # Decode the input image
    init_image = Image.open(io.BytesIO(image_data)).convert("RGB")
    
    # Perform inference
    image = run_inference_in_process.pipeline(
        prompt=prompt,
        image=init_image,
        num_inference_steps=steps,
        strength=strength,
        guidance_scale=guidance
    ).images[0]
    
    # Encode the output image to a Base64 string
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# ----------------------------
#  API Endpoints
# ----------------------------
@app.get("/ping")
async def health_check():
    """Health check endpoint for the load balancer."""
    return {"status": "ok"}

@app.post("/img2img")
async def generate_image(request: Img2ImgRequest):
    """The main endpoint to generate an image."""
    # 1. Decode the input image from Base64
    image_data = base64.b64decode(request.image)

    # 2. Run the inference in a separate process
    img_str = await asyncio.get_event_loop().run_in_executor(
        executor,
        run_inference_in_process,
        request.prompt,
        image_data,
        request.num_inference_steps,
        request.strength,
        request.guidance_scale
    )
    
    return {"image": img_str}

# -------------------------------------------------
#  Model Loading and Server Startup
# -------------------------------------------------
print("--- Starting server... ---")
print("--- Server is ready. ---")

if __name__ == "__main__":
    # Get the port from an environment variable, defaulting to 80
    port = int(os.getenv("PORT", "80"))
    # Run the Uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=port)

# Shutdown the executor when the server stops
@app.on_event("shutdown")
def shutdown_event():
    executor.shutdown()