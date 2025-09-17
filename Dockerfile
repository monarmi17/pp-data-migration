# Legacy Dockerfile for backward compatibility
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy both scripts for flexibility
COPY merge_orders_products_optimized.py .
COPY orders_to_matrixify.py .

# Copy the data directories
COPY datasource/ ./datasource/

# Create necessary directories
RUN mkdir -p processed output

# Default: Run the merge script (Step 1 only)
# To run Step 2: docker run <image> python orders_to_matrixify.py
# To run full pipeline: use docker-compose up full-pipeline
CMD ["python", "merge_orders_products_optimized.py"]
