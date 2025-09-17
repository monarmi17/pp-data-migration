#!/bin/bash

# Orders and Products Data Merger - Shell Script
# This script provides an alternative to Docker for running the data merger

echo "Starting Orders and Products Data Merger"
echo "========================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if required packages are installed
echo "Checking Python dependencies..."
python3 -c "import pandas, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required Python packages..."
    python3 -m pip install --break-system-packages pandas openpyxl
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install required packages"
        echo "Please install pandas and openpyxl manually:"
        echo "  python3 -m pip install --break-system-packages pandas openpyxl"
        exit 1
    fi
fi

# Check if data files exist
if [ ! -f "datasource/orders.xlsx" ]; then
    echo "Error: datasource/orders.xlsx not found"
    exit 1
fi

if [ ! -f "datasource/products.xlsx" ]; then
    echo "Error: datasource/products.xlsx not found"
    exit 1
fi

# Create processed directory if it doesn't exist
mkdir -p processed

# Run the Python script
echo "Running data merger..."
python3 merge_orders_products.py

if [ $? -eq 0 ]; then
    echo "========================================"
    echo "Data merging completed successfully!"
    echo "Output file: processed/orders.xlsx"
else
    echo "Error: Data merging failed"
    exit 1
fi
