# Use a lightweight official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables to optimize Python performance
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY sql/ ./sql/

# Create empty directories for volume mounting
RUN mkdir -p data/raw data/processed logs dashboard

# Run the pipeline orchestrator by default when the container starts
CMD ["python", "scripts/run_pipeline.py"]
