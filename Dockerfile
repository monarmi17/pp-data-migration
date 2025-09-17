# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the optimized Python script for large datasets
COPY merge_orders_products_optimized.py .

# Copy the data directories
COPY datasource/ ./datasource/

# Create processed directory
RUN mkdir -p processed

# Run the optimized script
CMD ["python", "merge_orders_products_optimized.py"]
