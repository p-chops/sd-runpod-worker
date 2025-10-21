# Use the official RunPod base image with PyTorch and CUDA
FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your API script into the container
COPY api.py .

# Command to run the API when the container starts
CMD ["python", "-u", "api.py"]
