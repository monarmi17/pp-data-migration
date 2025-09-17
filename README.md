# Orders and Products Data Merger

This project merges orders and products data to add Product Code information to the orders dataset.

## Overview

The script performs the following operations:

1. Loads orders data from `datasource/orders.xlsx`
2. Loads products data from `datasource/products.xlsx`
3. Merges the data using SKU as the foreign key
4. Adds a "Product Code" column to the orders data
5. Saves the merged data to `processed/orders.xlsx`

## Data Structure

### Orders Data

- Contains order line items with SKU information in the "Product" column
- 21 line items across 16 unique orders
- Primary key: Combination of Ticket number + Product (SKU)

### Products Data

- Contains product catalog with SKU and Product Code mapping
- 9 product variants
- Primary key: SKU
- Secondary key: Product Code

## Usage

### Option 1: Run with Shell Script (Recommended)

The easiest way to run the script with automatic dependency installation:

```bash
./run_merger.sh
```

### Option 2: Run with Docker

1. Build the Docker image:

```bash
docker build -t orders-merger .
```

2. Run the container:

```bash
docker run --rm -v $(pwd)/processed:/app/processed orders-merger
```

**Note**: If you encounter Docker permission issues, use Option 1 or 3 instead.

### Option 3: Run Locally

1. Install dependencies:

```bash
python3 -m pip install --break-system-packages pandas openpyxl
```

2. Run the script:

```bash
python3 merge_orders_products.py
```

## Troubleshooting

### Docker Issues

If you encounter Docker permission errors like "permission denied" or "failed to xattr", try:

- Restart Docker Desktop
- Use the shell script option instead: `./run_merger.sh`

### Python Environment Issues

If you get "externally-managed-environment" errors:

- Use the `--break-system-packages` flag as shown in Option 3
- Or use the shell script which handles this automatically

### Missing Dependencies

The shell script automatically checks and installs required packages. If manual installation is needed:

```bash
python3 -m pip install --break-system-packages pandas openpyxl
```

## Output

The script will create `processed/orders.xlsx` with the following enhancements:

- All original columns from the orders data
- New "Product Code" column positioned right after the "Product" column
- Product Code values mapped from the products data using SKU as the foreign key

## Error Handling

The script includes comprehensive error handling for:

- Missing input files
- Missing required columns
- Unmapped SKUs (warns about SKUs that don't have corresponding Product Codes)
- File I/O errors

## Dependencies

- pandas >= 2.0.0
- openpyxl >= 3.1.0

## File Structure

```
order-data-migration/
├── datasource/
│   ├── orders.xlsx
│   └── products.xlsx
├── processed/
│   └── orders.xlsx (generated)
├── specs/
│   ├── orders-technical-specs.md
│   └── product-technical-specs.md
├── merge_orders_products.py
├── run_merger.sh
├── requirements.txt
├── Dockerfile
└── README.md
```
