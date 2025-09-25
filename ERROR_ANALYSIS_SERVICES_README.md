# Error Analysis Services

This document describes the separate error analysis services that have been extracted from the products processing pipeline.

## Overview

The error analysis functionality has been separated into two specialized services:

1. **analyze-region-orders-import-errors**: Analyzes failed orders imports by region
2. **analyze-products-import-errors**: Analyzes failed products imports

## Services

### analyze-region-orders-import-errors

**Purpose**: Analyzes failed orders imports from region-specific CSV files.

**Expected File Pattern**: `[region]_matrixify_orders_[timestamp].csv`  
**Example**: `brentwood_village_matrixify_orders_2025_09_23_164637.csv`

**Features**:

- Automatically detects region-specific orders CSV files in `import-results/` directory
- Extracts region names from the matrixify orders filename pattern
- Works independently of `.env` configuration
- Creates region-specific error summaries
- Groups errors by severity (high, medium, low)
- Provides consolidated analysis across all regions

**Output Files**:

- `[region]_orders_error_summary.csv`: Detailed error analysis for each region
- `[region]_orders_error_type_summary.csv`: Error type summary for each region
- `all_regions_orders_error_summary.csv`: Consolidated summary across all regions

**Usage**:

```bash
# Run via Docker Compose
docker compose run --rm analyze-region-orders-import-errors

# Run directly
python analyze_region_orders_import_errors.py

# With custom options
python analyze_region_orders_import_errors.py --output-dir custom-analysis --verbose
```

**Error Types Detected**:

- Duplicate SKU variants
- Missing line item fields
- Invalid line items structure
- Missing customer information
- Invalid date formats
- Missing payment information
- Invalid fulfillment status
- Duplicate order names

### analyze-products-import-errors

**Purpose**: Analyzes failed products imports from CSV files.

**Features**:

- Automatically detects products CSV files in `import-results/` directory
- Categorizes errors by type (data_consistency, missing_data, duplicates, etc.)
- Groups errors by severity
- Provides detailed analysis of product-specific issues

**Output Files**:

- `products_error_summary.csv`: Detailed products error analysis
- `products_error_type_summary.csv`: Error type summary for products

**Usage**:

```bash
# Run via Docker Compose
docker compose run --rm analyze-products-import-errors

# Run directly
python analyze_products_import_errors.py

# With custom options
python analyze_products_import_errors.py --output-dir custom-analysis --verbose
```

**Error Types Detected**:

- Inconsistent titles across variants
- Inconsistent descriptions across variants
- Inconsistent vendor information
- Missing required fields (title, handle, SKU)
- Duplicate handles or SKUs
- Invalid price/weight/inventory formats
- Invalid option values for variants
- Too many variants
- Image upload errors
- Metafield validation errors

**Error Categories**:

- `data_consistency`: Issues with inconsistent data across variants
- `missing_data`: Required fields that are missing
- `duplicates`: Duplicate identifiers
- `data_format`: Invalid data formats
- `variant_issues`: Problems with product variants
- `media`: Image and media-related errors
- `metadata`: Metafield and metadata issues
- `general`: General validation errors

## File Structure

```
├── analyze_region_orders_import_errors.py    # Region orders error analyzer
├── analyze_products_import_errors.py         # Products error analyzer
├── Dockerfile.error-analysis                 # Docker container for error analysis
├── import-results/                           # Input directory for CSV files
│   ├── products.csv                         # Failed products import results
│   └── [region]_matrixify_orders_[timestamp].csv  # Region-specific orders files
└── error-analysis/                          # Output directory for analysis
    ├── [region]_orders_error_summary.csv
    ├── [region]_orders_error_type_summary.csv
    ├── products_error_summary.csv
    ├── products_error_type_summary.csv
    └── all_regions_orders_error_summary.csv
```

## Migration from Legacy System

### What Changed

1. **Removed**: Legacy `error-analysis` service from docker-compose.yml
2. **Removed**: Error analysis code from `products_to_matrixify.py`
3. **Removed**: Legacy `analyze_import_errors.py` file
4. **Added**: Two specialized error analysis services
5. **Added**: Region-specific error analysis capabilities
6. **Added**: Enhanced error categorization and severity levels

### Benefits

- **Separation of Concerns**: Error analysis is now separate from data processing
- **Specialized Analysis**: Different analyzers for orders vs products
- **Region Support**: Automatic detection and analysis of region-specific files
- **Enhanced Categorization**: Better error grouping and severity levels
- **Independent Execution**: Can run error analysis without data processing
- **Improved Maintainability**: Cleaner codebase with focused responsibilities

## Docker Services

The services are defined in `docker-compose.yml`:

```yaml
# Service for analyzing region-specific orders import errors
analyze-region-orders-import-errors:
  build:
    context: .
    dockerfile: Dockerfile.error-analysis
  volumes:
    - ./import-results:/app/import-results
    - ./error-analysis:/app/error-analysis
    - ./logs:/app/logs
    - .:/app:ro
  environment:
    - PYTHONUNBUFFERED=1
  command: python analyze_region_orders_import_errors.py

# Service for analyzing products import errors
analyze-products-import-errors:
  build:
    context: .
    dockerfile: Dockerfile.error-analysis
  volumes:
    - ./import-results:/app/import-results
    - ./error-analysis:/app/error-analysis
    - ./logs:/app/logs
    - .:/app:ro
  environment:
    - PYTHONUNBUFFERED=1
  command: python analyze_products_import_errors.py
```

## Logs

Both services create detailed logs in the `logs/` directory:

- `region_orders_error_analysis.log`
- `products_error_analysis.log`

## Command Line Options

Both scripts support the following options:

- `--output-dir`: Custom output directory (default: error-analysis)
- `--import-results-dir`: Custom input directory (default: import-results)
- `--verbose`: Enable verbose logging

## Examples

### Analyze all region orders errors

```bash
docker compose run --rm analyze-region-orders-import-errors
```

### Analyze products errors with verbose output

```bash
docker compose run --rm -e VERBOSE=1 analyze-products-import-errors
```

### Run with custom directories

```bash
python analyze_region_orders_import_errors.py \
  --import-results-dir custom-results \
  --output-dir custom-analysis \
  --verbose
```
