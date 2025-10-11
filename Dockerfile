# Use the official RunPod base image with PyTorch and CUDA
FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your handler script into the container
COPY handler.py .

# Command to run the handler when the container starts
CMD ["python", "-u", "handler.py"]
