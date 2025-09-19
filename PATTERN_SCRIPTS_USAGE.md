# Product Name Pattern Analysis Scripts Usage Guide

This guide explains how to use the product name pattern analysis scripts to generate and validate product name pattern examples. The scripts can be run both directly with Python and through Docker Compose services.

## Scripts Overview

### 1. `generate_product_name_pattern_examples.py`

Generates comprehensive examples of all product name patterns that the `products_to_matrixify.py` script can process.

### 2. `validate_product_name_pattern_examples.py`

Validates generated examples against the actual function to ensure accuracy.

## Quick Start (Docker - Recommended)

### Prerequisites

- Docker and Docker Compose installed
- Clone this repository

### Run Complete Pattern Analysis Pipeline

```bash
# Complete pipeline (generate + validate)
docker compose run --rm product-name-pattern-analysis-pipeline
```

This will:

1. Generate 75+ pattern examples
2. Validate them against the actual function
3. Save results to `product-name-pattern-analysis/` directory

## Docker Usage (Individual Services)

### Generate Pattern Examples

```bash
# Generate examples using Docker
docker compose run --rm generate-product-name-pattern-examples

# Generate with custom filename
docker compose run --rm generate-product-name-pattern-examples python generate_product_name_pattern_examples.py --output-file product-name-pattern-analysis/custom_patterns.csv
```

### Validate Examples

```bash
# Validate generated examples
docker compose run --rm validate-product-name-pattern-examples

# Validate custom file
docker compose run --rm validate-product-name-pattern-examples python validate_product_name_pattern_examples.py --input-file product-name-pattern-analysis/custom_patterns.csv
```

### Test Custom Product Names

```bash
# Test specific product names
docker compose run --rm -e CUSTOM_NAMES="Kong Dog Toy 2-Pack Hills Diet 5 lb Blue Buffalo Large" test-custom-product-names

# Alternative syntax
CUSTOM_NAMES="Kong Dog Toy 2-Pack Hills Diet 5 lb" docker compose run --rm test-custom-product-names
```

## Direct Python Usage (Advanced)

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Generate Pattern Examples

```bash
# Generate examples with default filename (product-name-pattern-analysis/product_name_pattern_examples.csv)
python3 generate_product_name_pattern_examples.py

# Generate with custom output filename
python3 generate_product_name_pattern_examples.py --output-file product-name-pattern-analysis/my_patterns.csv
```

**Output**: Creates a CSV file with 75+ examples across 10 pattern types.

### Validate Examples

```bash
# Validate default file
python3 validate_pattern_examples.py

# Validate custom file
python3 validate_pattern_examples.py --input-file pattern-analysis/my_patterns.csv --output-corrected pattern-analysis/my_corrected.csv
```

**Output**:

- Validation statistics
- Corrected CSV file with actual function results
- Mismatch file (if any discrepancies found)

### Validate Custom Product Names

```bash
# Test specific product names
python3 validate_pattern_examples.py --custom-names "Kong Dog Toy 2-Pack" "Hill's Diet 5 lb" "Blue Buffalo Large"
```

**Output**: CSV file with validation results for your custom names.

## Onboarding Workflow

### For New Team Members

1. **Clone and Setup**:

   ```bash
   git clone <repository-url>
   cd pp-data-migration
   ```

2. **Run Pattern Analysis** (Docker - No Python setup needed):

   ```bash
   docker compose run --rm pattern-analysis-pipeline
   ```

3. **Review Results**:

   - Check `pattern-analysis/product_name_pattern_examples_corrected.csv`
   - Review the validation statistics in the console output

4. **Test Your Own Product Names**:
   ```bash
   docker compose run --rm -e CUSTOM_NAMES="Your Product Name 2-Pack Another Product 5 lb" test-custom-names
   ```

### For Development

1. **Setup Python Environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run Scripts Directly**:
   ```bash
   python3 generate_pattern_examples.py
   python3 validate_pattern_examples.py
   ```

## Output Structure

### Directory Layout

```
pp-data-migration/
├── pattern-analysis/              # All pattern analysis outputs (gitignored)
│   ├── product_name_pattern_examples.csv
│   ├── product_name_pattern_examples_corrected.csv
│   ├── pattern_validation_mismatches_YYYYMMDD_HHMMSS.csv (if any)
│   └── custom_product_names_validation_YYYYMMDD_HHMMSS.csv
├── generate_pattern_examples.py   # Pattern generator script
├── validate_pattern_examples.py   # Validation script
└── Dockerfile.pattern-analysis    # Docker image for pattern scripts
```

### Generated Files

- `product_name_pattern_examples.csv` - Generated examples
- `product_name_pattern_examples_corrected.csv` - Validated/corrected examples
- `pattern_validation_mismatches_YYYYMMDD_HHMMSS.csv` - Any mismatches found
- `custom_product_names_validation_YYYYMMDD_HHMMSS.csv` - Custom name validation results

### CSV Structure

```
Pattern_Type,Original_Product_Name,Base_Name,Handle,Extracted_Variant,Base_Name_Length,Handle_Length,Has_Variant,Variant_Extracted
Pack/Count Variants,Kong Classic Dog Toy 2-Pack,Kong Classic Dog Toy,kong-classic-dog-toy,2-Pack,20,20,True,True
```

## Pattern Types Generated

1. **Pack/Count Variants** (10 examples) - `2-Pack`, `12 Count`, `6-Pk`
2. **Weight Variants** (10 examples) - `5 lb`, `2.5 kg`, `3 ounces`
3. **Size Variants** (10 examples) - `Small`, `Large`, `XL`
4. **Color Variants** (10 examples) - `Red`, `Black`, `Blue`
5. **Measurement Variants** (6 examples) - `36 inch`, `30 inches`
6. **Multi-pack Descriptors** (6 examples) - `Variety Pack`, `Assorted`
7. **Specific Product Variants** (5 examples) - `3-Way`, `4-Speed`
8. **Combined Patterns** (6 examples) - Multiple patterns with priority
9. **Complex Real-world** (6 examples) - Long, complex product names
10. **No Variants** (6 examples) - Products with no detectable variants

## Docker Services Reference

| Service                     | Purpose                   | Usage                                                             |
| --------------------------- | ------------------------- | ----------------------------------------------------------------- |
| `pattern-analysis-pipeline` | Complete pipeline         | `docker compose run --rm pattern-analysis-pipeline`               |
| `generate-pattern-examples` | Generate examples only    | `docker compose run --rm generate-pattern-examples`               |
| `validate-pattern-examples` | Validate examples only    | `docker compose run --rm validate-pattern-examples`               |
| `test-custom-names`         | Test custom product names | `docker compose run --rm -e CUSTOM_NAMES="..." test-custom-names` |

## Understanding the Results

### Key Columns

- **Pattern_Type**: Category of pattern detected
- **Original_Product_Name**: Input product name
- **Base_Name**: What becomes the Shopify product title
- **Handle**: URL-friendly product identifier
- **Extracted_Variant**: What becomes the size/variant option
- **Has_Variant**: Whether a variant was detected

### Pattern Behavior

- **Removed from base name**: Pack counts, weights, measurements
- **Kept in base name**: Colors, sizes (when alone), descriptors
- **Priority order**: Pack/Count → Weight → Size → Other

## Troubleshooting

### Docker Issues

```bash
# Rebuild images if needed
docker compose build pattern-analysis-pipeline

# Check container logs
docker compose logs generate-pattern-examples
```

### Import Errors (Python Direct Usage)

If you get import errors:

```bash
# Make sure you're in the correct directory
cd /path/to/pp-data-migration
python3 validate_pattern_examples.py
```

### File Not Found

If CSV file not found:

```bash
# Generate examples first
docker compose run --rm generate-pattern-examples
# Then validate
docker compose run --rm validate-pattern-examples
```

### Custom Testing Examples

```bash
# Test pack variants
docker compose run --rm -e CUSTOM_NAMES="Product 2-Pack Item 5-Pk Food 12 Count" test-custom-names

# Test weight variants
docker compose run --rm -e CUSTOM_NAMES="Dog Food 5 lb Cat Treats 2.5 kg Bird Seed 8 oz" test-custom-names

# Test combined patterns
docker compose run --rm -e CUSTOM_NAMES="Premium Dog Food Large Breed 30 lb 2-Pack" test-custom-names
```

## Integration with Main Pipeline

These scripts help you understand how the main `products_to_matrixify.py` script will process your product names. Use them to:

1. **Preview processing** - See how your product names will be split
2. **Validate logic** - Ensure the pattern detection works as expected
3. **Test new patterns** - Add new product name formats to test
4. **Debug issues** - Understand why certain products aren't processing correctly
5. **Onboard new team members** - Quick understanding of pattern processing

The generated examples serve as a reference for manual verification of your actual Shopify import data.

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Pattern Analysis
  run: docker compose run --rm pattern-analysis-pipeline

- name: Upload Pattern Analysis Results
  uses: actions/upload-artifact@v3
  with:
    name: pattern-analysis-results
    path: pattern-analysis/
```

### Automated Testing

```bash
# Run as part of your test suite
docker compose run --rm pattern-analysis-pipeline
if [ $? -eq 0 ]; then
  echo "✅ Pattern analysis passed"
else
  echo "❌ Pattern analysis failed"
  exit 1
fi
```
