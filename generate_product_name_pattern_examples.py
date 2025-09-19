#!/usr/bin/env python3
"""
Generate Pattern Examples for Product Name Processing

This script creates comprehensive examples of all product name patterns 
that the products_to_matrixify.py script can process, showing how each
pattern extracts base names and variants.

Usage:
    python3 generate_pattern_examples.py [--output-file OUTPUT_FILE]

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import re
import argparse
from pathlib import Path
from datetime import datetime

def extract_base_name_and_size(product_name):
    """
    Replicated function from products_to_matrixify.py to test pattern extraction
    """
    if not product_name or pd.isna(product_name):
        return 'Unknown Product', 'Standard'
    
    # Clean up the product name first
    original_name = str(product_name).strip()
    base_name = original_name
    
    # Comprehensive variant patterns that can appear anywhere in the title
    variant_patterns = [
        # Pack/Count variants (most common)
        r'\b(\d+(?:\.\d+)?[-\s]*(?:pk|pack|pks|packs|piece|pieces|pc|pcs|count|ct))\b',
        # Weight variants
        r'\b(\d+(?:\.\d+)?\s*(?:lb|lbs|pound|pounds|kg|kgs|kilogram|kilograms|oz|ounces?|g|grams?))\b',
        # Size variants
        r'\b(small|medium|large|xl|xxl|x-large|mini|tiny|giant|jumbo)\b',
        # Number + unit combinations
        r'\b(\d+[-\s]*(?:in|inch|inches|cm|mm|ft|feet))\b',
        # Color variants (when they appear as distinct variants)
        r'\b(black|brown|red|blue|green|white|gray|grey|pink|purple|yellow|orange)\b',
        # Multi-pack descriptors
        r'\b(assorted|mixed|variety|multi[-\s]*pack)\b',
        # Specific product variants
        r'\b(\d+[-\s]*(?:way|ways|speed|speeds|level|levels))\b',
    ]
    
    extracted_variants = []
    
    # Extract variants found in the title, but be selective about what to remove
    for i, pattern in enumerate(variant_patterns):
        matches = re.findall(pattern, base_name, re.IGNORECASE)
        for match in matches:
            # Normalize the variant
            variant = match.strip().replace(' ', '-')
            if variant and variant not in extracted_variants:
                extracted_variants.append(variant)
                
                # Only remove certain types of variants from the base name
                # Pack/count variants and weights should be removed, but colors and sizes should stay
                should_remove = False
                
                if i == 0:  # Pack/Count variants - remove these
                    should_remove = True
                elif i == 1:  # Weight variants - remove these
                    should_remove = True
                elif i == 2 and len(extracted_variants) > 1:  # Size variants - only remove if we have other variants
                    should_remove = True
                # Colors and other descriptors stay in the base name
                
                if should_remove:
                    # Remove this variant from the base name
                    base_name = re.sub(re.escape(match), '', base_name, flags=re.IGNORECASE)
    
    # Clean up the base name after removing variants
    base_name = re.sub(r'\s+', ' ', base_name).strip()
    base_name = re.sub(r'[-\s,]+$', '', base_name).strip()
    base_name = re.sub(r'^[-\s,]+', '', base_name).strip()
    base_name = re.sub(r'\s*-\s*-\s*', ' - ', base_name)  # Fix double dashes
    base_name = re.sub(r'\s+', ' ', base_name).strip()
    
    # If we extracted variants, use the first/most significant one
    if extracted_variants:
        # Prioritize pack/count variants, then weight, then size
        primary_variant = None
        
        # Look for pack/count variants first
        for variant in extracted_variants:
            if re.search(r'\d+.*(?:pk|pack|piece|count|ct)', variant, re.IGNORECASE):
                primary_variant = variant
                break
        
        # If no pack variant, look for weight
        if not primary_variant:
            for variant in extracted_variants:
                if re.search(r'\d+.*(?:lb|kg|oz|gram)', variant, re.IGNORECASE):
                    primary_variant = variant
                    break
        
        # Otherwise use the first variant found
        if not primary_variant:
            primary_variant = extracted_variants[0]
        
        extracted_size = primary_variant.title()
    else:
        extracted_size = 'Standard'
    
    # Ensure we have a valid base name
    if not base_name or len(base_name.strip()) < 2:
        base_name = original_name
        extracted_size = 'Standard'
    
    # Final cleanup of base name
    base_name = base_name.strip()
    if base_name.endswith(' -'):
        base_name = base_name[:-2].strip()
    if base_name.startswith('- '):
        base_name = base_name[2:].strip()
    
    return base_name, extracted_size

def create_handle_from_name(product_name):
    """Create a Shopify handle from product name."""
    if not product_name:
        return 'unknown-product'
    
    # Convert to lowercase and replace spaces/special chars with hyphens
    handle = re.sub(r'[^\w\s-]', '', str(product_name).lower())
    handle = re.sub(r'[-\s]+', '-', handle)
    handle = handle.strip('-')
    
    return handle or 'unknown-product'

def generate_pattern_examples():
    """Generate comprehensive examples for all supported patterns."""
    
    examples = []
    
    # Pattern 1: Pack/Count variants (most common, removed from base name)
    pack_examples = [
        "Kong Classic Dog Toy 2-Pack",
        "Hill's Science Diet Adult 3 Pack",
        "Purina Pro Plan Treats 6-Pk",
        "Royal Canin Kitten Food 12 Packs",
        "Wellness Core Wet Food 24-Pk",
        "Blue Buffalo Treats 5 Piece Set",
        "Iams Adult Dog Food 8 Pieces",
        "Fancy Feast Cat Food 12 Pcs",
        "Pedigree Dentastix 28 Count",
        "Whiskas Temptations 6 Ct"
    ]
    
    for name in pack_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Pack/Count Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Removed from base name'
        })
    
    # Pattern 2: Weight variants (removed from base name)
    weight_examples = [
        "Hills Prescription Diet 5 lb Bag",
        "Purina ONE SmartBlend 16.5 lbs",
        "Blue Buffalo Life Protection 30 lb",
        "Royal Canin Medium Adult 2.5 kg",
        "Wellness CORE Natural 4 kg",
        "Iams ProActive Health 15 pounds",
        "Science Diet Small Bites 3.5 pound",
        "Nutro Ultra Adult 12 oz Can",
        "Friskies Pate 5.5 oz",
        "Fancy Feast Grilled 3 ounces"
    ]
    
    for name in weight_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Weight Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Removed from base name'
        })
    
    # Pattern 3: Size variants (kept in base name unless other variants exist)
    size_examples = [
        "Kong Classic Dog Toy Small",
        "Petmate Kennel Medium Size",
        "FURminator Brush Large",
        "Nylabone Chew Toy XL",
        "PetSafe Collar XXL",
        "Hartz Toy Mini",
        "Flexi Leash Tiny",
        "Wellness Treats Giant",
        "Blue Buffalo Jumbo Bones",
        "Hill's Science Diet X-Large"
    ]
    
    for name in size_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Size Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Kept in base name (single variant)'
        })
    
    # Pattern 4: Measurement variants (removed from base name)
    measurement_examples = [
        "Petmate Crate 36 inch",
        "Midwest Dog Kennel 42 in",
        "PetSafe Gate 30 inches",
        "Carlson Pet Gate 28-inch",
        "Regalo Baby Gate 49 in",
        "North States Gate 62 inches"
    ]
    
    for name in measurement_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Measurement Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Removed from base name'
        })
    
    # Pattern 5: Color variants (kept in base name)
    color_examples = [
        "Kong Classic Red Dog Toy",
        "Petmate Kennel Black",
        "FURminator Blue Brush",
        "Nylabone White Chew",
        "PetSafe Brown Collar",
        "Hartz Pink Toy",
        "Flexi Green Leash",
        "Wellness Gray Treats",
        "Blue Buffalo Purple Bowl",
        "Hill's Orange Feeder"
    ]
    
    for name in color_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Color Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Kept in base name'
        })
    
    # Pattern 6: Multi-pack descriptors (kept in base name)
    multipack_examples = [
        "Fancy Feast Variety Pack",
        "Purina Mixed Flavors",
        "Blue Buffalo Assorted Treats",
        "Hill's Multi-Pack Cans",
        "Wellness Variety Selection",
        "Iams Mixed Protein Pack"
    ]
    
    for name in multipack_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Multi-pack Descriptors',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Kept in base name'
        })
    
    # Pattern 7: Specific product variants (kept in base name)
    specific_examples = [
        "PetSafe 3-Way Dog Door",
        "SureFlap 4-Way Cat Flap",
        "Petmate 2-Speed Fan",
        "Midwest 5-Level Tower",
        "North States 6-Way Gate"
    ]
    
    for name in specific_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Specific Product Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Kept in base name'
        })
    
    # Pattern 8: Combined patterns (priority: pack > weight > size)
    combined_examples = [
        "Kong Classic Red Small 2-Pack",  # Should prioritize 2-Pack
        "Hill's Science Diet 5 lb Large Breed",  # Should prioritize 5 lb
        "Blue Buffalo Large Breed 30 lb 3-Pack",  # Should prioritize 3-Pack
        "Purina Pro Plan Small Bites 6 oz 12 Count",  # Should prioritize 12 Count
        "Royal Canin Medium Adult 2.5 kg Variety Pack",  # Should prioritize 2.5 kg
        "Wellness CORE Large Breed 26 lb Multi-Pack"  # Should prioritize 26 lb
    ]
    
    for name in combined_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Combined Patterns',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Prioritized extraction'
        })
    
    # Pattern 9: No variants (Standard)
    no_variant_examples = [
        "Kong Classic Dog Toy",
        "Hill's Science Diet",
        "Blue Buffalo Life Protection",
        "Purina Pro Plan",
        "Royal Canin Adult",
        "Wellness CORE Natural"
    ]
    
    for name in no_variant_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'No Variants',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Default to Standard'
        })
    
    # Pattern 10: Complex real-world examples
    complex_examples = [
        "Kong - Cat Cat Sport Balls 2-Pk Assorted",  # From the docstring example
        "Hill's Prescription Diet c/d Multicare Stress Urinary Care with Chicken 8.5 lb",
        "Blue Buffalo Wilderness High Protein Grain Free Natural Adult Large Breed Dry Dog Food Salmon 24 lb",
        "Purina Pro Plan Focus Adult Small Breed Formula Dry Dog Food 6 lb Bag",
        "Royal Canin Size Health Nutrition Medium Adult Dry Dog Food 30 lb",
        "Wellness Complete Health Natural Dry Small Breed Dog Food Turkey & Oatmeal 12 lb"
    ]
    
    for name in complex_examples:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        examples.append({
            'Pattern_Type': 'Complex Real-world',
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Behavior': 'Complex processing'
        })
    
    return examples

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate product name pattern examples for manual verification')
    parser.add_argument('--output-file', type=str, 
                        default='product-name-pattern-analysis/product_name_pattern_examples.csv',
                        help='Output CSV file name (default: product-name-pattern-analysis/product_name_pattern_examples.csv)')
    return parser.parse_args()

def main():
    """Generate the pattern examples CSV file."""
    args = parse_arguments()
    
    print("🔍 Generating product name pattern examples...")
    
    # Generate all examples
    examples = generate_pattern_examples()
    
    # Create DataFrame
    df = pd.DataFrame(examples)
    
    # Add some analysis columns
    df['Base_Name_Length'] = df['Base_Name'].str.len()
    df['Handle_Length'] = df['Handle'].str.len()
    df['Has_Variant'] = df['Extracted_Variant'] != 'Standard'
    df['Variant_Extracted'] = df['Extracted_Variant'] != 'Standard'
    
    # Sort by pattern type and original name
    df = df.sort_values(['Pattern_Type', 'Original_Product_Name'])
    
    # Ensure output directory exists
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    
    # Add timestamp to filename for tracking
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"✅ Generated {len(df)} pattern examples")
    print(f"📁 Saved to: {output_path}")
    print(f"🕒 Generated on: {timestamp}")
    
    # Print summary
    print(f"\n📊 Pattern Summary:")
    pattern_counts = df['Pattern_Type'].value_counts()
    for pattern, count in pattern_counts.items():
        print(f"  - {pattern}: {count} examples")
    
    print(f"\n🔍 Variant Analysis:")
    print(f"  - Products with variants: {df['Has_Variant'].sum()}")
    print(f"  - Products without variants: {(~df['Has_Variant']).sum()}")
    
    print(f"\n📋 Column Information:")
    print(f"  - Pattern_Type: Category of pattern detected")
    print(f"  - Original_Product_Name: Input product name")
    print(f"  - Base_Name: Extracted base product name")
    print(f"  - Handle: Generated Shopify handle")
    print(f"  - Extracted_Variant: Primary variant extracted")
    print(f"  - Behavior: How the pattern is processed")
    
    print(f"\n💡 Next Steps:")
    print(f"  - Review the generated CSV for accuracy")
    print(f"  - Run validate_pattern_examples.py to verify against actual function")
    print(f"  - Use the examples to understand pattern processing behavior")
    
    print(f"\n✨ Ready for manual verification!")

if __name__ == "__main__":
    main()
