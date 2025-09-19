# Product Name Pattern Analysis Services

This document provides a reference for the product name pattern analysis services and scripts.

## 📁 Files and Directories

### Scripts

- `generate_product_name_pattern_examples.py` - Generates pattern examples
- `validate_product_name_pattern_examples.py` - Validates examples against actual function

### Docker Files

- `Dockerfile.product-name-pattern-analysis` - Docker image for pattern analysis services

### Directories

- `product-name-pattern-analysis/` - Output directory for all pattern analysis results (gitignored)

## 🐳 Docker Services

### Core Services

| Service                                  | Purpose                   | Usage                                                                     |
| ---------------------------------------- | ------------------------- | ------------------------------------------------------------------------- |
| `generate-product-name-pattern-examples` | Generate pattern examples | `docker compose run --rm generate-product-name-pattern-examples`          |
| `validate-product-name-pattern-examples` | Validate examples         | `docker compose run --rm validate-product-name-pattern-examples`          |
| `test-custom-product-names`              | Test custom product names | `docker compose run --rm -e CUSTOM_NAMES="..." test-custom-product-names` |
| `product-name-pattern-analysis-pipeline` | Complete pipeline         | `docker compose run --rm product-name-pattern-analysis-pipeline`          |

## 🔧 Direct Python Usage

### Generate Examples

```bash
python3 generate_product_name_pattern_examples.py
python3 generate_product_name_pattern_examples.py --output-file product-name-pattern-analysis/custom.csv
```

### Validate Examples

```bash
python3 validate_product_name_pattern_examples.py
python3 validate_product_name_pattern_examples.py --custom-names "Product 1" "Product 2"
```

## 📋 Output Files

All files are saved to `product-name-pattern-analysis/`:

- `product_name_pattern_examples.csv` - Generated examples
- `product_name_pattern_examples_corrected.csv` - Validated examples
- `pattern_validation_mismatches_*.csv` - Any validation mismatches
- `custom_product_names_validation_*.csv` - Custom name test results

## 🎯 Purpose

These services help understand how the main `products_to_matrixify.py` script processes product names by:

1. Generating comprehensive examples of pattern detection
2. Validating the pattern extraction logic
3. Testing custom product names to preview processing
4. Providing reference data for manual verification

## 📚 Related Documentation

- **[PATTERN_SCRIPTS_USAGE.md](PATTERN_SCRIPTS_USAGE.md)** - Detailed usage guide
- **[PRODUCT_NAME_PATTERNS_ANALYSIS.md](PRODUCT_NAME_PATTERNS_ANALYSIS.md)** - Pattern analysis reference
- **[products_to_matrixify.py](products_to_matrixify.py)** - Main product processing script
