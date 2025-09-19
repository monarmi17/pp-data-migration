# Pattern Analysis Scripts Usage Guide

This guide explains how to use the pattern analysis scripts to generate and validate product name pattern examples.

## Scripts Overview

### 1. `generate_pattern_examples.py`

Generates comprehensive examples of all product name patterns that the `products_to_matrixify.py` script can process.

### 2. `validate_pattern_examples.py`

Validates generated examples against the actual function to ensure accuracy.

## Basic Usage

### Generate Pattern Examples

```bash
# Generate examples with default filename
python3 generate_pattern_examples.py

# Generate with custom output filename
python3 generate_pattern_examples.py --output-file my_patterns.csv
```

**Output**: Creates a CSV file with 75+ examples across 10 pattern types.

### Validate Examples

```bash
# Validate default file
python3 validate_pattern_examples.py

# Validate custom file
python3 validate_pattern_examples.py --input-file my_patterns.csv --output-corrected my_corrected.csv
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

## Typical Workflow

### 1. Generate Fresh Examples

```bash
python3 generate_pattern_examples.py --output-file patterns_$(date +%Y%m%d).csv
```

### 2. Validate Against Actual Function

```bash
python3 validate_pattern_examples.py --input-file patterns_$(date +%Y%m%d).csv
```

### 3. Review Results

- Check validation statistics (should be 100% matches)
- Review the corrected CSV file
- Examine any mismatch files if generated

## Advanced Usage

### Testing New Product Names

If you have new product names to test:

```bash
# Create a text file with product names (one per line)
echo "ACME Pet Food Super Premium 15 lb Bag" > test_names.txt
echo "FurBuddy Deluxe Collar Medium Black" >> test_names.txt
echo "PetCare Pro Treats Variety Pack 24 Count" >> test_names.txt

# Test them
python3 validate_pattern_examples.py --custom-names $(cat test_names.txt)
```

### Batch Processing

```bash
# Generate and validate in one go
python3 generate_pattern_examples.py && python3 validate_pattern_examples.py
```

## Output Files

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

### Import Errors

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
python3 generate_pattern_examples.py
# Then validate
python3 validate_pattern_examples.py
```

### Custom Testing

To test specific patterns:

```bash
# Test pack variants
python3 validate_pattern_examples.py --custom-names "Product 2-Pack" "Item 5-Pk" "Food 12 Count"

# Test weight variants
python3 validate_pattern_examples.py --custom-names "Dog Food 5 lb" "Cat Treats 2.5 kg" "Bird Seed 8 oz"

# Test combined patterns
python3 validate_pattern_examples.py --custom-names "Premium Dog Food Large Breed 30 lb 2-Pack"
```

## Integration with Main Pipeline

These scripts help you understand how the main `products_to_matrixify.py` script will process your product names. Use them to:

1. **Preview processing** - See how your product names will be split
2. **Validate logic** - Ensure the pattern detection works as expected
3. **Test new patterns** - Add new product name formats to test
4. **Debug issues** - Understand why certain products aren't processing correctly

The generated examples serve as a reference for manual verification of your actual Shopify import data.
