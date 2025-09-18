# Products Processing Pipeline

This document describes the unified products processing pipeline that combines variant fixing and error analysis functionality into a single script.

## Overview

The `products_to_matrixify.py` script processes product data to create Matrixify-compatible CSV files. It combines two main functionalities:

1. **Variant Fixing**: Resolves duplicate variants by splitting handles with color/identifier suffixes
2. **Error Analysis**: Analyzes failed import results and creates error summaries

## Script Structure

The unified script follows the same architectural pattern as `orders_to_matrixify.py`:

- **Argument parsing** with test/production modes
- **Logging setup** with mode-specific log files
- **File detection** based on mode (test-data vs original-data)
- **Modular processing** with separate classes for different functionalities
- **Error handling** and progress reporting
- **Output validation** and summary generation

## Usage

### Command Line Options

```bash
# Show help
python3 products_to_matrixify.py --help

# Test mode (uses datasource/test-data/products.xlsx)
python3 products_to_matrixify.py --test

# Production mode (uses datasource/original-data/products.xlsx)
python3 products_to_matrixify.py

# Custom input file
python3 products_to_matrixify.py --input-file path/to/custom/products.xlsx

# Skip variant fixing (only basic conversion)
python3 products_to_matrixify.py --test --skip-variant-fixing

# Only run error analysis
python3 products_to_matrixify.py --analyze-errors
```

### Docker Services

#### Products Processing Services

```bash
# Test mode - Process test products data
docker-compose up products-matrixify-test

# Production mode - Process production products data
docker-compose up products-matrixify-prod

# Error analysis only
docker-compose up analyze-import-errors
```

#### Orders Processing Services (Renamed for Clarity)

```bash
# Test mode - Merge orders with products
docker-compose up orders-merge-test

# Production mode - Merge orders with products
docker-compose up orders-merge-prod

# Test mode - Convert orders to Matrixify format
docker-compose up orders-matrixify-test

# Production mode - Convert orders to Matrixify format
docker-compose up orders-matrixify-prod

# Test mode - Full orders pipeline
docker-compose up orders-pipeline-test

# Production mode - Full orders pipeline
docker-compose up orders-pipeline-prod
```

## Input Files

### Test Mode

- **Input**: `datasource/test-data/products.xlsx`
- **Purpose**: Development and testing with smaller datasets

### Production Mode

- **Input**: `datasource/original-data/products.xlsx`
- **Purpose**: Processing actual production data

## Output Files

### Products Processing

- **Raw Output**: `matrixify-ready-products/[mode]_products_matrixify_raw_[timestamp].csv`
- **Fixed Output**: `matrixify-ready-products/[mode]_products_matrixify_fixed_[timestamp].csv`
- **Summary**: `processed/[mode]_products_processing_summary.txt`
- **Error Rows**: `error-rows/[mode]_products_error_rows_[timestamp].xlsx`

### Error Analysis

- **Error Summaries**: `error-analysis/products_error_summary.csv`
- **Type Summary**: `error-analysis/error_type_summary.csv`

## Functionality Details

### 1. Variant Fixing (CleanVariantFixer)

**Purpose**: Resolves duplicate product variants by splitting handles

**Process**:

1. Identifies duplicate variant groups (same Handle + Option1 Value)
2. Extracts color information from original product names
3. Creates separate handles with color/identifier suffixes
4. Updates product titles appropriately

**Example**:

- Original: `pawz` (Handle) with multiple variants of same size
- Fixed: `pawz-black`, `pawz-brown`, `pawz-red` (separate handles)

### 2. Error Analysis (ImportErrorAnalyzer)

**Purpose**: Analyzes failed Shopify import results

**Process**:

1. Loads failed records from import-results CSV files
2. Categorizes errors using pattern matching
3. Extracts key identifiers for troubleshooting
4. Generates summary reports

**Error Categories**:

- Duplicate SKU variants
- Missing required fields
- Inconsistent titles/descriptions
- Validation errors

### 3. Matrixify Conversion

**Purpose**: Converts product data to Shopify Matrixify format

**Process**:

1. Loads product data from Excel files
2. Validates required columns
3. Applies basic formatting and cleanup
4. Outputs CSV in Matrixify-compatible format

## Logging

Each mode creates separate log files:

- **Test Mode**: `logs/products_matrixify_test.log`
- **Production Mode**: `logs/products_matrixify_production.log`

## Directory Structure

```
pp-data-migration/
├── datasource/
│   ├── test-data/
│   │   └── products.xlsx          # Test input
│   └── original-data/
│       └── products.xlsx          # Production input
├── matrixify-ready-products/      # Output CSV files
├── processed/                     # Summary reports
├── error-rows/                    # Error records
├── logs/                         # Log files
├── import-results/               # Failed import data (input for error analysis)
└── error-analysis/               # Error analysis output
```

## Error Handling

The script includes comprehensive error handling:

- File not found errors with helpful messages
- Data validation with progress reporting
- Graceful handling of missing columns
- Error row tracking and reporting

## Development Notes

### Key Classes

1. **CleanVariantFixer**: Handles duplicate variant resolution
2. **ImportErrorAnalyzer**: Processes failed import analysis

### Integration Pattern

The script follows the same pattern as `orders_to_matrixify.py`:

- Modular class-based architecture
- Consistent argument parsing and logging
- Similar file naming conventions
- Docker integration with proper volume mounts

### Future Enhancements

- Support for additional product data formats
- Advanced variant detection algorithms
- Integration with Shopify API for validation
- Batch processing for large datasets
