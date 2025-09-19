# PetPlanet Data Migration Pipeline

This project provides a complete data migration pipeline for PetPlanet, supporting both product and order data migration to Shopify. The pipeline handles multiple regions and is optimized for large datasets.

## 🚀 Quick Start

**New to this project?** Check out the **[ONBOARDING.md](ONBOARDING.md)** guide for a 5-minute setup!

```bash
# Clone and setup
git clone <repository-url>
cd pp-data-migration

# Test the complete pipeline
docker compose run --rm full-pipeline-test
```

## Main Components

1. **Product Processing**: Converts product data to Shopify-compatible format with variant handling
2. **Order Processing**: Merges orders with products and converts to Matrixify format
3. **Error Analysis**: Analyzes failed Shopify imports and provides troubleshooting insights

## Key Features

- **Multi-Region Support**: Process different regional order files (e.g., Auburn Bay, Beddington)
- **Test and Production Modes**: Test with small datasets before processing full production data
- **Scalable Processing**: Handles 40+ regional files with 500k+ orders each
- **Docker Integration**: Containerized processing with bind mounts for development
- **Timestamped Outputs**: Unique file naming with timestamps for production runs
- **Comprehensive Logging**: Region-specific logs for tracking and debugging

## Directory Structure

```
order-data-migration/
├── datasource/
│   ├── original-data/           # Production data
│   │   ├── Sales_By_Customer_Auburn_Bay.xlsx
│   │   ├── Sales_By_Customer_Beddington.xlsx
│   │   └── products.xlsx
│   └── test-data/               # Small test datasets
│       ├── orders.xlsx          # ~1,000 test orders
│       └── products.xlsx        # ~500 test products
├── order-line-items-with-product-codes/  # Merged data output
│   ├── test_order_line_items_with_product_codes.xlsx
│   └── auburn_bay_order_line_items_with_product_codes.xlsx
├── matrixify-ready-orders/      # Final Matrixify CSV files
│   ├── test_matrixify_orders.csv
│   └── auburn_bay_matrixify_orders_2024_09_18_143022.csv
├── logs/                        # Processing logs
│   ├── data_merger_test.log
│   ├── data_merger_auburn_bay.log
│   ├── matrixify_converter_test.log
│   └── matrixify_converter_auburn_bay.log
└── ... (scripts and configs)
```

## Overview

### Step 1: Orders and Products Data Merger

**Test Mode:**

1. Loads orders from `datasource/test-data/orders.xlsx`
2. Loads products from `datasource/test-data/products.xlsx`
3. Saves merged data to `order-line-items-with-product-codes/test_order_line_items_with_product_codes.xlsx`

**Production Mode:**

1. Loads orders from `datasource/original-data/Sales_By_Customer_<Region>.xlsx`
2. Loads products from `datasource/original-data/products.xlsx`
3. Extracts region name from filename (e.g., "Auburn_Bay" → "auburn_bay")
4. Saves merged data to `order-line-items-with-product-codes/<region>_order_line_items_with_product_codes.xlsx`

### Step 2: Matrixify CSV Conversion

**Test Mode:**

1. Loads processed orders from test file
2. Saves to `matrixify-ready-orders/test_matrixify_orders.csv`

**Production Mode:**

1. Loads processed orders from region-specific file
2. Generates timestamped filename: `<region>_matrixify_orders_YYYY_MM_DD_HHMMSS.csv`
3. Saves to `matrixify-ready-orders/<timestamped_filename>.csv`

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

### Test Mode (Recommended for First Run)

Test the pipeline with small datasets:

```bash
# Run complete test pipeline
docker-compose up full-pipeline-test

# Or run individual steps in test mode
docker-compose up merge-orders-test       # Step 1 only
docker-compose up matrixify-convert-test  # Step 2 only
```

### Production Mode

#### Method 1: Using Environment Variables

Create a `.env` file (copy from `env.example`):

```bash
cp env.example .env
```

Edit `.env` to specify the region:

```bash
# Option 1: Specify exact filename
ORDERS_FILE=Sales_By_Customer_Auburn_Bay.xlsx

# OR Option 2: Specify region name
REGION_NAME=auburn_bay
```

Run the pipeline:

```bash
# Run complete production pipeline
docker-compose up full-pipeline-prod

# Or run individual steps
docker-compose up merge-orders-prod       # Step 1 only
docker-compose up matrixify-convert-prod  # Step 2 only
```

#### Method 2: Using Inline Environment Variables

```bash
# For Auburn Bay region
ORDERS_FILE=Sales_By_Customer_Auburn_Bay.xlsx docker-compose up full-pipeline-prod

# For Beddington region
ORDERS_FILE=Sales_By_Customer_Beddington.xlsx docker-compose up full-pipeline-prod

# Using region name directly
REGION_NAME=auburn_bay docker-compose up full-pipeline-prod
```

### Direct Script Execution (Without Docker)

#### Test Mode

```bash
# Step 1: Merge orders with products (test mode)
python merge_orders_products_optimized.py --test

# Step 2: Convert to Matrixify format (test mode)
python orders_to_matrixify.py --test
```

#### Production Mode

```bash
# Step 1: Merge orders with products (production mode)
python merge_orders_products_optimized.py --orders-file Sales_By_Customer_Auburn_Bay.xlsx
# OR
python merge_orders_products_optimized.py --region auburn_bay

# Step 2: Convert to Matrixify format (production mode)
python orders_to_matrixify.py --region auburn_bay
```

## Troubleshooting

### Docker Issues

If you encounter Docker permission errors like "permission denied" or "failed to xattr", try:

- Restart Docker Desktop
- Check Docker Desktop is running and has sufficient resources allocated

### Large Dataset Performance

For datasets with 500k+ orders:

- The optimized script automatically handles chunked processing
- Monitor memory usage and processing logs
- Processing time scales linearly with dataset size

## Output

### Step 1 Output: `processed/orders.xlsx`

The merge script creates `processed/orders.xlsx` with the following enhancements:

- All original columns from the orders data
- New "Product Code" column positioned right after the "Product" column
- Product Code values mapped from the products data using SKU as the foreign key

### Step 2 Output: `output/matrixify_orders.csv`

The Matrixify converter creates a CSV file with the following structure:

| Column                       | Source               | Description                        |
| ---------------------------- | -------------------- | ---------------------------------- |
| Name                         | Ticket Number        | Order identifier                   |
| Command                      | Static: "NEW"        | Matrixify command                  |
| Processed At                 | Generated from Date  | Logical timestamp (business hours) |
| Customer: Email              | Email                | Customer email address             |
| Line: Type                   | Static: "Line Item"  | Item type                          |
| Line: SKU                    | Product Code         | 12-digit Product Code              |
| Line: Quantity               | Product quantity     | Item quantity                      |
| Line: Price                  | Price ($)            | Item price                         |
| Line: Grams                  | Static: 0            | Weight (not used)                  |
| Line: Requires Shipping      | Static: TRUE         | Shipping requirement               |
| Line: Vendor                 | Empty                | Vendor information                 |
| Transaction: Kind            | Static: "sale"       | Transaction type                   |
| Transaction: Processed At    | Same as Processed At | Transaction timestamp              |
| Transaction: Amount          | Price ($)            | Transaction amount                 |
| Payment: Status              | Static: "paid"       | Payment status                     |
| Fulfillment: Status          | Static: "success"    | Fulfillment status                 |
| Fulfillment: Processed At    | Same as Processed At | Fulfillment timestamp              |
| Fulfillment: Tracking Number | Empty                | Tracking information               |
| Fulfillment: Shipment Status | Static: "delivered"  | Shipment status                    |

## Error Handling

The script includes comprehensive error handling for:

- Missing input files
- Missing required columns
- Unmapped SKUs (warns about SKUs that don't have corresponding Product Codes)
- File I/O errors

## Performance Optimizations for Large Datasets

The optimized version (`merge_orders_products_optimized.py`) includes several enhancements for handling large datasets:

### Memory Efficiency

- **Chunked Processing**: Processes orders in 50k row chunks to avoid memory overflow
- **Selective Column Loading**: Only loads required columns from Excel files
- **Memory Cleanup**: Explicit garbage collection after processing each chunk
- **Optimized Data Types**: Uses efficient pandas operations

### Performance Features

- **Progress Tracking**: Real-time progress updates and processing rates
- **Detailed Logging**: Comprehensive logs saved to `data_merger.log`
- **Batch Writing**: Efficient Excel file writing with minimal memory usage
- **Error Recovery**: Graceful handling of large file operations

### Scalability

- **Estimated Processing Time**: ~500k orders in 5-15 minutes (depending on hardware)
- **Memory Usage**: ~200-500MB RAM (vs 2-5GB for non-chunked processing)
- **File Size Support**: Handles files up to several GB

## Dependencies

- pandas >= 2.0.0
- openpyxl >= 3.1.0
- xlsxwriter >= 3.0.0 (for optimized version)

## File Structure

```
order-data-migration/
├── datasource/
│   ├── orders.xlsx
│   ├── orders-original.xlsx
│   ├── products.xlsx
│   ├── test-orders.xlsx
│   └── test-products.xlsx
├── processed/
│   ├── orders.xlsx (generated by Step 1)
│   └── orders.bak.xlsx
├── output/
│   └── matrixify_orders.csv (generated by Step 2)
├── specs/
│   ├── orders-technical-specs.md
│   └── product-technical-specs.md
├── templates/
│   └── matrixify-orders.csv
├── merge_orders_products_optimized.py (Step 1 script)
├── orders_to_matrixify.py (Step 2 script)
├── requirements.txt
├── Dockerfile (Legacy - Step 1 only)
├── Dockerfile.merge (Step 1 container)
├── Dockerfile.matrixify (Step 2 container)
├── Dockerfile.pipeline (Full pipeline container)
├── docker-compose.yml (Orchestration)
└── README.md
```

## Docker Services

The project includes three Docker services via `docker-compose.yml`:

- **merge-orders**: Runs Step 1 (orders-products merger)
- **matrixify-convert**: Runs Step 2 (Matrixify CSV conversion)
- **full-pipeline**: Runs both steps sequentially

## Logs

Both scripts generate detailed logs when running in Docker containers. The logs are visible in the Docker container output and can be accessed using:

```bash
# View logs for individual services
docker-compose logs merge-orders
docker-compose logs matrixify-convert
docker-compose logs full-pipeline

# Follow logs in real-time
docker-compose logs -f full-pipeline
```
