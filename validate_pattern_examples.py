#!/usr/bin/env python3
"""
Validate Pattern Examples using the actual products_to_matrixify.py function

This script validates the generated pattern examples by testing them
against the actual extract_base_name_and_size function from the 
products_to_matrixify.py script.

Usage:
    python3 validate_pattern_examples.py [--input-file INPUT_FILE] [--output-corrected OUTPUT_FILE]

Author: AI Assistant
Date: 2024
"""

import sys
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime

# Import the actual functions from products_to_matrixify.py
try:
    from products_to_matrixify import extract_base_name_and_size, create_handle_from_name
except ImportError:
    print("❌ Error: Could not import functions from products_to_matrixify.py")
    print("   Make sure this script is in the same directory as products_to_matrixify.py")
    sys.exit(1)

def validate_examples(input_file, output_corrected_file):
    """Validate the generated examples against the actual function."""
    
    # Read the generated CSV
    csv_path = Path(input_file)
    if not csv_path.exists():
        print(f"❌ CSV file not found: {input_file}")
        print("   Please run generate_pattern_examples.py first.")
        return None, None
    
    df = pd.read_csv(csv_path)
    
    print(f"🔍 Validating {len(df)} pattern examples...")
    
    validation_results = []
    mismatches = []
    
    for idx, row in df.iterrows():
        original_name = row['Original_Product_Name']
        expected_base = row.get('Base_Name', '')
        expected_variant = row.get('Extracted_Variant', '')
        expected_handle = row.get('Handle', '')
        
        # Test with actual function
        actual_base, actual_variant = extract_base_name_and_size(original_name)
        actual_handle = create_handle_from_name(actual_base)
        
        # Check for matches
        base_match = actual_base == expected_base
        variant_match = actual_variant == expected_variant
        handle_match = actual_handle == expected_handle
        
        validation_results.append({
            'Index': idx,
            'Pattern_Type': row.get('Pattern_Type', 'Unknown'),
            'Original_Product_Name': original_name,
            'Expected_Base_Name': expected_base,
            'Actual_Base_Name': actual_base,
            'Base_Match': base_match,
            'Expected_Variant': expected_variant,
            'Actual_Variant': actual_variant,
            'Variant_Match': variant_match,
            'Expected_Handle': expected_handle,
            'Actual_Handle': actual_handle,
            'Handle_Match': handle_match,
            'All_Match': base_match and variant_match and handle_match
        })
        
        if not (base_match and variant_match and handle_match):
            mismatches.append({
                'Index': idx,
                'Pattern_Type': row.get('Pattern_Type', 'Unknown'),
                'Original_Product_Name': original_name,
                'Base_Name_Expected': expected_base,
                'Base_Name_Actual': actual_base,
                'Variant_Expected': expected_variant,
                'Variant_Actual': actual_variant,
                'Handle_Expected': expected_handle,
                'Handle_Actual': actual_handle
            })
    
    # Create validation results DataFrame
    validation_df = pd.DataFrame(validation_results)
    
    # Calculate statistics
    total_examples = len(validation_df)
    perfect_matches = validation_df['All_Match'].sum()
    base_matches = validation_df['Base_Match'].sum()
    variant_matches = validation_df['Variant_Match'].sum()
    handle_matches = validation_df['Handle_Match'].sum()
    
    print(f"\n📊 Validation Results:")
    print(f"  - Total examples: {total_examples}")
    print(f"  - Perfect matches: {perfect_matches} ({perfect_matches/total_examples*100:.1f}%)")
    print(f"  - Base name matches: {base_matches} ({base_matches/total_examples*100:.1f}%)")
    print(f"  - Variant matches: {variant_matches} ({variant_matches/total_examples*100:.1f}%)")
    print(f"  - Handle matches: {handle_matches} ({handle_matches/total_examples*100:.1f}%)")
    
    if mismatches:
        print(f"\n❌ Found {len(mismatches)} mismatches:")
        mismatches_df = pd.DataFrame(mismatches)
        
        # Save mismatches for review
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        mismatches_path = Path(f"pattern-analysis/pattern_validation_mismatches_{timestamp}.csv")
        mismatches_path.parent.mkdir(parents=True, exist_ok=True)
        mismatches_df.to_csv(mismatches_path, index=False)
        print(f"📁 Mismatches saved to: {mismatches_path}")
        
        # Show first few mismatches
        print(f"\nFirst 5 mismatches:")
        for i, mismatch in enumerate(mismatches[:5]):
            print(f"\n{i+1}. {mismatch['Pattern_Type']}: {mismatch['Original_Product_Name']}")
            if mismatch['Base_Name_Expected'] != mismatch['Base_Name_Actual']:
                print(f"   Base Name: '{mismatch['Base_Name_Expected']}' → '{mismatch['Base_Name_Actual']}'")
            if mismatch['Variant_Expected'] != mismatch['Variant_Actual']:
                print(f"   Variant: '{mismatch['Variant_Expected']}' → '{mismatch['Variant_Actual']}'")
            if mismatch['Handle_Expected'] != mismatch['Handle_Actual']:
                print(f"   Handle: '{mismatch['Handle_Expected']}' → '{mismatch['Handle_Actual']}'")
    else:
        print(f"\n✅ All examples validated successfully!")
        mismatches_df = None
    
    # Save corrected validation results
    corrected_path = Path(output_corrected_file)
    corrected_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create corrected DataFrame with actual results
    corrected_data = []
    for result in validation_results:
        corrected_data.append({
            'Pattern_Type': result['Pattern_Type'],
            'Original_Product_Name': result['Original_Product_Name'],
            'Base_Name': result['Actual_Base_Name'],
            'Handle': result['Actual_Handle'],
            'Extracted_Variant': result['Actual_Variant'],
            'Base_Name_Length': len(result['Actual_Base_Name']),
            'Handle_Length': len(result['Actual_Handle']),
            'Has_Variant': result['Actual_Variant'] != 'Standard',
            'Variant_Extracted': result['Actual_Variant'] != 'Standard'
        })
    
    corrected_df = pd.DataFrame(corrected_data)
    corrected_df.to_csv(corrected_path, index=False)
    print(f"📁 Corrected examples saved to: {corrected_path}")
    
    return validation_df, mismatches_df

def validate_custom_names(product_names):
    """Validate a list of custom product names."""
    print(f"\n🔍 Validating {len(product_names)} custom product names...")
    
    results = []
    for name in product_names:
        base_name, variant = extract_base_name_and_size(name)
        handle = create_handle_from_name(base_name)
        
        results.append({
            'Original_Product_Name': name,
            'Base_Name': base_name,
            'Handle': handle,
            'Extracted_Variant': variant,
            'Has_Variant': variant != 'Standard'
        })
    
    results_df = pd.DataFrame(results)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(f"pattern-analysis/custom_product_names_validation_{timestamp}.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_path, index=False)
    
    print(f"📁 Custom validation results saved to: {output_path}")
    
    # Show results
    print(f"\n📋 Custom Validation Results:")
    for i, result in enumerate(results[:10]):  # Show first 10
        print(f"{i+1:2d}. {result['Original_Product_Name']}")
        print(f"     → Base: {result['Base_Name']}")
        print(f"     → Handle: {result['Handle']}")
        print(f"     → Variant: {result['Extracted_Variant']}")
    
    if len(results) > 10:
        print(f"     ... and {len(results) - 10} more (see CSV file)")
    
    return results_df

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Validate product name pattern examples against actual function')
    parser.add_argument('--input-file', type=str, 
                        default='pattern-analysis/product_name_pattern_examples.csv',
                        help='Input CSV file to validate (default: pattern-analysis/product_name_pattern_examples.csv)')
    parser.add_argument('--output-corrected', type=str,
                        default='pattern-analysis/product_name_pattern_examples_corrected.csv',
                        help='Output file for corrected examples (default: pattern-analysis/product_name_pattern_examples_corrected.csv)')
    parser.add_argument('--custom-names', type=str, nargs='+',
                        help='Validate custom product names (space-separated)')
    return parser.parse_args()

def main():
    """Main validation function."""
    args = parse_arguments()
    
    print("🔍 Product Name Pattern Validation Tool")
    print("=" * 50)
    
    try:
        if args.custom_names:
            # Validate custom product names
            validate_custom_names(args.custom_names)
        else:
            # Validate generated examples
            print(f"📂 Input file: {args.input_file}")
            print(f"📂 Output file: {args.output_corrected}")
            
            validation_df, mismatches_df = validate_examples(args.input_file, args.output_corrected)
            
            if validation_df is not None:
                print(f"\n✨ Validation complete!")
                
                if mismatches_df is None:
                    print(f"🎉 All patterns validated successfully!")
                else:
                    print(f"⚠️  Found some mismatches - check the generated mismatch file for details")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
