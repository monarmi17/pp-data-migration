# PetPlanet Order Data Migration Pipeline

This project provides a complete data migration pipeline for PetPlanet orders, consisting of two main steps:

1. **Orders-Products Merger**: Merges orders and products data to add Product Code information
2. **Matrixify Converter**: Converts processed orders to Matrixify CSV format for Shopify import

## Overview

### Step 1: Orders and Products Data Merger

1. Loads orders data from `datasource/orders.xlsx`
2. Loads products data from `datasource/products.xlsx`
3. Merges the data using SKU as the foreign key
4. Adds a "Product Code" column to the orders data
5. Saves the merged data to `processed/orders.xlsx`

### Step 2: Matrixify CSV Conversion

1. Loads processed orders from `processed/orders.xlsx`
2. Converts data to Matrixify CSV format with proper column mapping
3. Generates logical timestamps based on order dates
4. Groups data by Product Code (SKU)
5. Saves the Matrixify-compatible CSV to `output/matrixify_orders.csv`

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

### Option 1: Docker Compose (Recommended - Full Pipeline)

Run the complete pipeline (both steps) with Docker Compose:

```bash
# Run the full pipeline
docker-compose up full-pipeline

# Or run individual steps
docker-compose up merge-orders    # Step 1 only
docker-compose up matrixify-convert  # Step 2 only (requires Step 1 first)
```

### Option 2: Individual Docker Containers

Run each step separately:

```bash
# Step 1: Merge orders with products
docker build -f Dockerfile.merge -t orders-merger .
docker run --rm -v $(pwd)/datasource:/app/datasource -v $(pwd)/processed:/app/processed orders-merger

# Step 2: Convert to Matrixify format
docker build -f Dockerfile.matrixify -t matrixify-converter .
docker run --rm -v $(pwd)/processed:/app/processed -v $(pwd)/output:/app/output matrixify-converter
```

### Option 3: Legacy Docker (Step 1 Only)

For backward compatibility:

```bash
docker build -t orders-merger .
docker run --rm -v $(pwd)/processed:/app/processed orders-merger
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
