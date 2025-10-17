# We Squeak

This project implements a cloud img2img worker for runpod.io that runs an outdated Stable Diffusion model (sd-turbo) on demand.

Client code is provided for a workflow that interacts with the service to run scene processing jobs in parallel based on a prompt schedule defined in a CSV file. The system caches processed frames to allow for rapid iteration on subsets of the source video.

Utilities are provided for detecting scene transitions, reviewing frames for reprocessing, and rendering the output video.