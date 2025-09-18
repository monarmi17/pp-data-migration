# Import Error Analysis

This service analyzes failed imports from your `import-results/` directory and groups them by generic error types for easier troubleshooting.

## Features

- **Automatic Error Detection**: Identifies common error patterns in both orders and products CSV files
- **Error Grouping**: Groups similar errors together for easier analysis
- **Key Identifiers**: Includes only significant columns needed for backtracking issues
- **Summary Reports**: Creates both detailed and high-level summary reports
- **Git Ignored**: Output directory is automatically ignored by git
- **Docker Integration**: Run as a containerized service

## Usage

### Docker Service (Recommended)

```bash
# Basic usage - analyzes import-results/ directory
docker compose run --rm error-analysis

# Custom output directory
docker compose run --rm error-analysis python analyze_import_errors.py --output-dir custom-analysis
```

### Direct Script Execution

```bash
# Basic usage
python analyze_import_errors.py

# Custom directories
python analyze_import_errors.py --import-results-dir /path/to/results --output-dir /path/to/output
```

## Output Files

The service creates files in the `error-analysis/` directory:

### 1. Detailed Analysis Files

- `orders_error_summary.csv` - Detailed orders error analysis
- `products_error_summary.csv` - Detailed products error analysis

### 2. High-Level Summary

- `error_type_summary.csv` - Overview of all error types with counts

## Error Types Detected

### Orders Errors

- **duplicate_sku_variants**: Multiple variants with same SKU
- **missing_line_item_fields**: Missing Name/Title fields
- **invalid_line_items**: Invalid line item structure

### Products Errors

- **inconsistent_title**: Different titles across variants
- **inconsistent_body_html**: Different descriptions across variants
- **missing_required_fields**: Blank required fields

### Generic Errors

- **validation_error**: General validation issues
- **duplicate_identifier**: Duplicate identifiers

## Key Identifiers Included

### Orders Analysis

- Order Name, SKU, Customer Email
- Processed At, Transaction Amount
- Payment Status, Fulfillment Status

### Products Analysis

- Handle, Variant SKU, Title
- Vendor, Status, Price, Cost

## Example Output

```
ERROR ANALYSIS SUMMARY
============================================================
Total failed records analyzed: 472,450
Unique error types found: 3

Top error types:
  duplicate_sku_variants: 472,441 records (Duplicate SKU variants found)
  missing_line_item_fields: 472,441 records (Missing required line item fields)
  invalid_line_items: 472,441 records (Invalid line items structure)
```

## Integration with Pipeline

This service complements your existing data migration pipeline:

1. **Post-Import Analysis**: Run after Matrixify imports to identify issues
2. **Data Quality Insights**: Understand common failure patterns
3. **Troubleshooting Support**: Quick identification of problematic records
4. **Audit Trail**: Maintains detailed error logs for compliance

## Requirements

- Python 3.11+
- pandas >= 2.0.0
- Standard library modules (re, os, datetime, collections)

The service uses the same dependencies as your existing pipeline.

## Docker Integration

The service is fully integrated into your Docker Compose setup:

- **Service Name**: `error-analysis`
- **Dockerfile**: `Dockerfile.error-analysis`
- **Input Mount**: `./import-results:/app/import-results`
- **Output Mount**: `./error-analysis:/app/error-analysis`
- **Script Mount**: `.:/app:ro` (read-only for development)

## File Structure

```
error-analysis/
├── orders_error_summary.csv      # Detailed orders analysis
├── products_error_summary.csv    # Detailed products analysis
└── error_type_summary.csv        # High-level overview
```

All output files are created without timestamps for easier integration with other tools.
