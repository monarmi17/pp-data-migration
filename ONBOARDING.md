# PetPlanet Data Migration - Onboarding Guide

Welcome to the PetPlanet data migration project! This guide will help you get up and running quickly with the tools and processes for migrating product and order data to Shopify.

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd pp-data-migration
cp env.example .env  # Optional: for production processing
```

### 2. Understand Product Name Processing

```bash
# Run pattern analysis to see how product names are processed
docker compose run --rm pattern-analysis-pipeline
```

This generates examples showing how product names like:

- `Kong Classic Dog Toy 2-Pack` → Base: `Kong Classic Dog Toy`, Variant: `2-Pack`
- `Hills Science Diet 5 lb` → Base: `Hills Science Diet`, Variant: `5-Lb`

### 3. Test Your Own Product Names

```bash
# Test how your specific product names will be processed
docker compose run --rm -e CUSTOM_NAMES="Your Product Name 2-Pack Another Product 5 lb" test-custom-names
```

### 4. Process Test Data

```bash
# Test the complete pipeline with sample data
docker compose run --rm full-pipeline-test
```

🎉 **You're ready to go!** Check the `pattern-analysis/`, `matrixify-ready-products/`, and `matrixify-ready-orders/` directories for results.

## 📋 Project Overview

This project handles the migration of PetPlanet's product and order data to Shopify using the Matrixify import format.

### Key Components

1. **Product Processing** (`products_to_matrixify.py`)

   - Converts product data to Shopify-compatible format
   - Handles variant detection and grouping
   - Fixes duplicate variants automatically

2. **Order Processing** (`orders_to_matrixify.py` + `merge_orders_products_optimized.py`)

   - Merges order data with product information
   - Converts to Matrixify order format
   - Handles multiple regional data files

3. **Pattern Analysis** (`generate_pattern_examples.py` + `validate_pattern_examples.py`)

   - Analyzes how product names are processed
   - Generates validation examples
   - Tests custom product names

4. **Error Analysis** (`analyze_import_errors.py`)
   - Analyzes failed Shopify imports
   - Categorizes error types
   - Provides troubleshooting insights

## 🐳 Docker Services Overview

### Core Processing Services

| Service                   | Purpose                      | Usage                                             |
| ------------------------- | ---------------------------- | ------------------------------------------------- |
| `products-matrixify-test` | Process test products        | `docker compose run --rm products-matrixify-test` |
| `products-matrixify-prod` | Process production products  | `docker compose run --rm products-matrixify-prod` |
| `full-pipeline-test`      | Complete test pipeline       | `docker compose run --rm full-pipeline-test`      |
| `full-pipeline-prod`      | Complete production pipeline | `docker compose run --rm full-pipeline-prod`      |

### Pattern Analysis Services

| Service                     | Purpose                   | Usage                                                             |
| --------------------------- | ------------------------- | ----------------------------------------------------------------- |
| `pattern-analysis-pipeline` | Complete pattern analysis | `docker compose run --rm pattern-analysis-pipeline`               |
| `generate-pattern-examples` | Generate examples         | `docker compose run --rm generate-pattern-examples`               |
| `validate-pattern-examples` | Validate examples         | `docker compose run --rm validate-pattern-examples`               |
| `test-custom-names`         | Test custom names         | `docker compose run --rm -e CUSTOM_NAMES="..." test-custom-names` |

### Utility Services

| Service                 | Purpose                    | Usage                                           |
| ----------------------- | -------------------------- | ----------------------------------------------- |
| `analyze-import-errors` | Analyze failed imports     | `docker compose run --rm analyze-import-errors` |
| `orders-merge-test`     | Merge test orders/products | `docker compose run --rm orders-merge-test`     |
| `orders-matrixify-test` | Convert test orders        | `docker compose run --rm orders-matrixify-test` |

## 📁 Directory Structure

```
pp-data-migration/
├── datasource/                    # Input data
│   ├── test-data/                # Small test datasets
│   │   ├── products.xlsx         # ~500 test products
│   │   └── orders.xlsx           # ~1,000 test orders
│   └── original-data/            # Production data
│       ├── products.xlsx         # Full product catalog
│       └── Sales_By_Customer_*.xlsx # Regional order files
│
├── matrixify-ready-products/      # Product output (Shopify import ready)
├── matrixify-ready-orders/        # Order output (Shopify import ready)
├── pattern-analysis/              # Pattern analysis results
├── error-analysis/                # Import error analysis
├── logs/                          # Processing logs
├── error-rows/                    # Failed/ignored records
│
├── products_to_matrixify.py       # Main product processor
├── orders_to_matrixify.py         # Order converter
├── merge_orders_products_optimized.py # Order/product merger
├── generate_pattern_examples.py   # Pattern example generator
├── validate_pattern_examples.py   # Pattern validator
└── analyze_import_errors.py       # Error analyzer
```

## 🛠️ Common Workflows

### 1. Understanding Product Processing

Before processing your data, understand how product names are handled:

```bash
# See comprehensive examples
docker compose run --rm pattern-analysis-pipeline

# Test your specific product names
docker compose run --rm -e CUSTOM_NAMES="Kong Dog Toy 2-Pack Hills Diet 5 lb Blue Buffalo Large" test-custom-names

# Review results
ls -la pattern-analysis/
```

### 2. Processing Test Data

Always test with sample data first:

```bash
# Process test products
docker compose run --rm products-matrixify-test

# Process test orders (complete pipeline)
docker compose run --rm full-pipeline-test

# Check results
ls -la matrixify-ready-products/
ls -la matrixify-ready-orders/
```

### 3. Processing Production Data

For production data:

```bash
# Set up environment (optional)
echo "ORDERS_FILE=Sales_By_Customer_Beddington.xlsx" > .env

# Process products
docker compose run --rm products-matrixify-prod

# Process orders for specific region
docker compose run --rm full-pipeline-prod

# Check results and logs
ls -la matrixify-ready-products/
ls -la logs/
```

### 4. Analyzing Import Failures

If Shopify imports fail:

```bash
# Place failed import CSV files in import-results/
# Then analyze errors
docker compose run --rm analyze-import-errors

# Review error analysis
ls -la error-analysis/
```

## 📊 Understanding the Output

### Product Files

- **Raw**: `products_matrixify_raw_*.csv` - Basic Matrixify format
- **Fixed**: `products_matrixify_fixed_*.csv` - With duplicate variants resolved

### Order Files

- **Merged**: `*_order_line_items_with_product_codes.xlsx` - Orders merged with product data
- **Matrixify**: `*_matrixify_orders_*.csv` - Shopify-ready format

### Pattern Analysis

- **Examples**: `product_name_pattern_examples_corrected.csv` - How names are processed
- **Custom Tests**: `custom_product_names_validation_*.csv` - Your custom name tests

### Error Analysis

- **Error Summary**: `*_error_summary.csv` - Detailed error breakdown
- **Error Types**: `error_type_summary.csv` - High-level error categories

## 🔧 Development Setup

### Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run scripts directly
python3 generate_pattern_examples.py
python3 products_to_matrixify.py --test
```

### Docker Development

```bash
# Rebuild services after code changes
docker compose build

# Run with volume mounts for live editing
docker compose run --rm products-matrixify-test
```

## 📈 Monitoring and Logs

### Log Files

All processing generates detailed logs in `logs/`:

- `products_matrixify_*.log` - Product processing
- `data_merger_*.log` - Order/product merging
- `matrixify_converter_*.log` - Order conversion

### Processing Statistics

Each run generates summary files in `processed/`:

- Processing counts and success rates
- Performance metrics
- Error statistics

### Error Tracking

Failed records are saved in `error-rows/` for manual review:

- Detailed error reasons
- Source data for troubleshooting
- Batch processing information

## 🚨 Troubleshooting

### Common Issues

**Docker not starting?**

```bash
# Check Docker is running
docker --version
docker compose --version

# Rebuild if needed
docker compose build
```

**Import errors?**

```bash
# Check Python path
docker compose run --rm products-matrixify-test python -c "import products_to_matrixify; print('✅ Import OK')"

# Check file permissions
ls -la datasource/test-data/
```

**No output files?**

```bash
# Check logs for errors
docker compose run --rm products-matrixify-test
cat logs/products_matrixify_test.log
```

**Pattern analysis failing?**

```bash
# Test pattern detection
docker compose run --rm -e CUSTOM_NAMES="Test Product 2-Pack" test-custom-names
```

### Getting Help

1. **Check logs** in `logs/` directory
2. **Review error files** in `error-rows/`
3. **Run pattern analysis** to understand processing
4. **Use test mode** before production processing

## 🎯 Best Practices

### 1. Always Test First

```bash
# Test with sample data before production
docker compose run --rm products-matrixify-test
docker compose run --rm full-pipeline-test
```

### 2. Understand Your Data

```bash
# Analyze how your product names will be processed
docker compose run --rm pattern-analysis-pipeline
```

### 3. Monitor Processing

```bash
# Check logs during processing
tail -f logs/products_matrixify_production.log
```

### 4. Validate Results

```bash
# Check output file structure
head -5 matrixify-ready-products/products_matrixify_fixed_*.csv
```

### 5. Handle Errors Gracefully

```bash
# Analyze any import failures
docker compose run --rm analyze-import-errors
```

## 📚 Additional Resources

- **[PATTERN_SCRIPTS_USAGE.md](PATTERN_SCRIPTS_USAGE.md)** - Detailed pattern analysis guide
- **[PRODUCT_NAME_PATTERNS_ANALYSIS.md](PRODUCT_NAME_PATTERNS_ANALYSIS.md)** - Pattern processing reference
- **[PRODUCTS_PROCESSING_README.md](PRODUCTS_PROCESSING_README.md)** - Product processing details
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete implementation overview
- **[ERROR_ANALYSIS_README.md](ERROR_ANALYSIS_README.md)** - Error analysis guide

## 🤝 Contributing

### Making Changes

1. Test your changes with sample data
2. Update documentation if needed
3. Ensure Docker services still work
4. Add pattern examples for new functionality

### Adding New Pattern Types

1. Update `extract_base_name_and_size()` function
2. Add examples to `generate_pattern_examples.py`
3. Test with `validate_pattern_examples.py`
4. Update documentation

---

**Welcome to the team! 🎉**

Start with the Quick Start section above, and don't hesitate to explore the pattern analysis tools to understand how the data processing works. The Docker services make it easy to get started without complex setup.
