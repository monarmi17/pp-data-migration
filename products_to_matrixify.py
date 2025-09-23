#!/usr/bin/env python3
"""
Products to Matrixify CSV Converter with Variant Fixing and Error Analysis

This script processes product data to create Matrixify-compatible CSV files.
It combines variant fixing functionality (resolving duplicate variants) with 
error analysis capabilities for failed imports.

Supports test mode and production mode:
- Test mode: Processes datasource/test-data/products.xlsx
- Production mode: Processes datasource/original-data/products.xlsx

Main Functions:
1. Clean Variant Fixing: Resolves duplicate variants by splitting handles with color/identifier suffixes
2. Error Analysis: Analyzes failed import results and creates error summaries
3. Matrixify Format: Outputs clean CSV files ready for Shopify import

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import os
import sys
import time
import glob
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any, Optional

# Configure logging (will be updated in main() based on mode)
logger = logging.getLogger(__name__)


class CleanVariantFixer:
    """Handles fixing duplicate product variants by splitting handles."""
    
    def __init__(self):
        self.fixed_count = 0
        
    def extract_color_from_name(self, product_name):
        """Extract color information from product name"""
        if pd.isna(product_name):
            return None
            
        # Common color patterns
        color_patterns = [
            r'\b(black|white|red|blue|green|yellow|orange|purple|pink|brown|gray|grey|silver|gold|tan|beige|cream|ivory)\b',
            r'\b(midnight|royal|navy|forest|crimson|emerald|amber|rose|chocolate|charcoal|burgundy|maroon|turquoise)\b',
            r'\b(light|dark|bright|deep|pale)\s+(black|white|red|blue|green|yellow|orange|purple|pink|brown|gray|grey)\b'
        ]
        
        for pattern in color_patterns:
            match = re.search(pattern, product_name.lower())
            if match:
                color = match.group(0).title()
                return color.replace(' ', '-')  # Convert "Light Blue" to "Light-Blue"
        
        return None
    
    def check_sequential_skus(self, skus):
        """Check if SKUs are sequential"""
        try:
            numeric_parts = []
            for sku in skus:
                numbers = re.findall(r'\d+', str(sku))
                if numbers:
                    numeric_parts.append(int(numbers[-1]))
            
            if len(numeric_parts) >= 2:
                sorted_nums = sorted(numeric_parts)
                return all(sorted_nums[i] + 1 == sorted_nums[i + 1] for i in range(len(sorted_nums) - 1))
        except:
            pass
        return False
    
    def fix_duplicate_variants_only(self, enhanced_df, original_df):
        """Fix ONLY the duplicate variants by splitting handles - NO new columns"""
        logger.info("Fixing duplicate variants by splitting handles (NO new columns)...")
        
        fixed_df = enhanced_df.copy()
        
        # Find duplicate groups
        variant_groups = enhanced_df.groupby(['Handle', 'Option1 Value']).size().reset_index(name='count')
        duplicate_sizes = variant_groups[variant_groups['count'] > 1]
        
        logger.info(f"Found {len(duplicate_sizes)} duplicate groups to fix")
        
        for _, row in duplicate_sizes.iterrows():
            handle = row['Handle']
            size = row['Option1 Value']
            count = row['count']
            
            # Get the variants
            variants = enhanced_df[
                (enhanced_df['Handle'] == handle) & 
                (enhanced_df['Option1 Value'] == size)
            ]
            
            skus = variants['Variant SKU'].tolist()
            
            # Get original product names for these SKUs
            original_names = []
            colors_detected = []
            
            for sku in skus:
                orig_data = original_df[original_df['SKU'] == sku]
                if not orig_data.empty:
                    orig_name = orig_data['*Product Name*'].iloc[0]
                    original_names.append(orig_name)
                    
                    # Extract color from original name
                    color = self.extract_color_from_name(orig_name)
                    colors_detected.append(color)
                else:
                    original_names.append("Unknown")
                    colors_detected.append(None)
            
            # Split the products by creating separate handles
            self.split_products_by_color_only(fixed_df, handle, size, skus, colors_detected, original_names)
            self.fixed_count += 1
                
            logger.info(f"Fixed: {handle} with {count} variants")
        
        return fixed_df
    
    def split_products_by_color_only(self, df, handle, size, skus, colors, original_names):
        """Split products by creating separate handles with colors - NO new columns"""
        
        # Default colors if none detected
        default_colors = ['Black', 'Brown', 'Red', 'Blue', 'Green', 'Pink', 'Purple', 'Gray', 'White', 'Tan']
        
        for i, sku in enumerate(skus):
            mask = (df['Handle'] == handle) & (df['Variant SKU'] == sku) & (df['Option1 Value'] == size)
            
            if mask.any():
                # Determine identifier for this variant
                if i < len(colors) and colors[i]:
                    # Use detected color
                    identifier = colors[i].lower()
                elif i < len(default_colors):
                    # Use default color
                    identifier = default_colors[i].lower()
                else:
                    # Use variant number
                    identifier = f"variant-{i+1}"
                
                # Create new handle with identifier
                new_handle = f"{handle}-{identifier}"
                df.loc[mask, 'Handle'] = str(new_handle)
                
                # Update title if it's empty
                current_title = df.loc[mask, 'Title'].iloc[0]
                
                if pd.isna(current_title) or current_title == '':
                    # Use original name if available
                    if i < len(original_names) and original_names[i] != "Unknown":
                        new_title = original_names[i]
                    else:
                        # Create title from handle
                        base_title = handle.replace('-', ' ').title()
                        new_title = f"{base_title} - {identifier.title()}"
                    
                    df.loc[mask, 'Title'] = str(new_title)
                else:
                    # Add identifier to existing title if not already present
                    if identifier.lower() not in current_title.lower():
                        new_title = f"{current_title} - {identifier.title()}"
                        df.loc[mask, 'Title'] = str(new_title)


class ImportErrorAnalyzer:
    """Analyzes import errors and groups them by generic error types."""
    
    def __init__(self, import_results_dir: str = "import-results", output_dir: str = "error-analysis"):
        self.import_results_dir = import_results_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Error pattern definitions
        self.error_patterns = {
            # Orders error patterns
            'duplicate_sku_variants': {
                'pattern': r'Found \[(\d+)\] Variants with the same SKU \[([^\]]+)\]',
                'description': 'Duplicate SKU variants found',
                'file_type': 'orders'
            },
            'missing_line_item_fields': {
                'pattern': r'Line Items: Name can\'t be blank, Title can\'t be blank',
                'description': 'Missing required line item fields (Name/Title)',
                'file_type': 'orders'
            },
            'invalid_line_items': {
                'pattern': r'Order: Line items is invalid',
                'description': 'Invalid line items structure',
                'file_type': 'orders'
            },
            
            # Products error patterns
            'inconsistent_title': {
                'pattern': r'"Title" differs in each row',
                'description': 'Inconsistent product titles across variants',
                'file_type': 'products'
            },
            'inconsistent_body_html': {
                'pattern': r'"Body HTML" differs in each row',
                'description': 'Inconsistent product descriptions across variants',
                'file_type': 'products'
            },
            'missing_required_fields': {
                'pattern': r'can\'t be blank',
                'description': 'Missing required product fields',
                'file_type': 'products'
            },
            
            # Generic patterns
            'validation_error': {
                'pattern': r'validation|invalid|error',
                'description': 'General validation errors',
                'file_type': 'both'
            },
            'duplicate_identifier': {
                'pattern': r'duplicate|already exists|taken',
                'description': 'Duplicate identifiers',
                'file_type': 'both'
            }
        }
    
    def load_failed_records(self, file_path: str) -> pd.DataFrame:
        """Load only failed records from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            failed_df = df[df['Import Result'] == 'Failed'].copy()
            logger.info(f"Loaded {len(failed_df)} failed records from {os.path.basename(file_path)}")
            return failed_df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def extract_error_details(self, comment: str) -> Dict[str, Any]:
        """Extract structured error details from import comment."""
        error_details = {
            'raw_comment': comment,
            'error_type': 'unknown',
            'error_description': 'Unknown error',
            'extracted_values': {}
        }
        
        # Check each error pattern
        for error_key, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            if re.search(pattern, comment, re.IGNORECASE):
                error_details['error_type'] = error_key
                error_details['error_description'] = error_config['description']
                
                # Extract specific values using regex groups
                match = re.search(pattern, comment, re.IGNORECASE)
                if match and match.groups():
                    error_details['extracted_values'] = {
                        f'group_{i+1}': group for i, group in enumerate(match.groups())
                    }
                break
        
        return error_details
    
    def get_key_identifiers(self, row: pd.Series, file_type: str) -> Dict[str, Any]:
        """Extract key identifiers for backtracking issues."""
        identifiers = {}
        
        if file_type == 'orders':
            identifiers.update({
                'order_name': row.get('Name', ''),
                'sku': row.get('Line: SKU', ''),
                'customer_email': row.get('Customer: Email', ''),
                'processed_at': row.get('Processed At', ''),
                'transaction_amount': row.get('Transaction: Amount', ''),
                'payment_status': row.get('Payment: Status', ''),
                'fulfillment_status': row.get('Fulfillment: Status', '')
            })
        elif file_type == 'products':
            identifiers.update({
                'handle': row.get('Handle', ''),
                'variant_sku': row.get('Variant SKU', ''),
                'title': row.get('Title', ''),
                'vendor': row.get('Vendor', ''),
                'status': row.get('Status', ''),
                'variant_price': row.get('Variant Price', ''),
                'cost_per_item': row.get('Cost per item', '')
            })
        
        return identifiers
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze failed imports from a single file."""
        filename = os.path.basename(file_path)
        file_type = 'orders' if 'orders' in filename.lower() else 'products'
        
        logger.info(f"Analyzing {filename}...")
        
        # Load failed records
        failed_df = self.load_failed_records(file_path)
        if failed_df.empty:
            logger.info(f"No failed records found in {filename}")
            return {}
        
        # Analyze each failed record
        analysis_results = []
        error_counts = Counter()
        
        for idx, row in failed_df.iterrows():
            # Extract error details
            error_details = self.extract_error_details(row['Import Comment'])
            
            # Get key identifiers
            identifiers = self.get_key_identifiers(row, file_type)
            
            # Create analysis record
            analysis_record = {
                'file_type': file_type,
                'row_index': idx,
                'error_type': error_details['error_type'],
                'error_description': error_details['error_description'],
                'raw_comment': error_details['raw_comment'],
                **identifiers,
                **error_details['extracted_values']
            }
            
            analysis_results.append(analysis_record)
            error_counts[error_details['error_type']] += 1
        
        # Create summary
        summary = {
            'file_type': file_type,
            'total_failed_records': len(failed_df),
            'error_counts': dict(error_counts),
            'analysis_results': analysis_results
        }
        
        logger.info(f"Found {len(failed_df)} failed records with {len(error_counts)} error types")
        for error_type, count in error_counts.most_common():
            logger.info(f"  - {error_type}: {count} records")
        
        return summary
    
    def create_summary_csv(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create summary CSV files for each file type."""
        
        for analysis in all_analyses:
            if not analysis:
                continue
                
            file_type = analysis['file_type']
            results_df = pd.DataFrame(analysis['analysis_results'])
            
            # Create summary filename (no timestamp)
            summary_filename = f"{file_type}_error_summary.csv"
            summary_path = os.path.join(self.output_dir, summary_filename)
            
            # Select only significant columns for analysis
            if file_type == 'orders':
                significant_columns = [
                    'error_type', 'error_description', 'order_name', 'sku', 
                    'customer_email', 'processed_at', 'transaction_amount',
                    'payment_status', 'fulfillment_status', 'raw_comment'
                ]
            else:  # products
                significant_columns = [
                    'error_type', 'error_description', 'handle', 'variant_sku',
                    'title', 'vendor', 'status', 'variant_price', 'cost_per_item',
                    'raw_comment'
                ]
            
            # Filter to available columns
            available_columns = [col for col in significant_columns if col in results_df.columns]
            summary_df = results_df[available_columns].copy()
            
            # Sort by error type for better analysis
            summary_df = summary_df.sort_values(['error_type', 'error_description'])
            
            # Save summary
            summary_df.to_csv(summary_path, index=False)
            logger.info(f"Created summary: {summary_path}")
    
    def create_error_type_summary(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create a high-level error type summary."""
        
        # Combine all error counts
        total_error_counts = Counter()
        file_type_counts = defaultdict(Counter)
        
        for analysis in all_analyses:
            if not analysis:
                continue
                
            file_type = analysis['file_type']
            error_counts = analysis['error_counts']
            
            for error_type, count in error_counts.items():
                total_error_counts[error_type] += count
                file_type_counts[file_type][error_type] += count
        
        # Create summary DataFrame
        summary_data = []
        for error_type, total_count in total_error_counts.most_common():
            summary_data.append({
                'error_type': error_type,
                'total_count': total_count,
                'orders_count': file_type_counts['orders'].get(error_type, 0),
                'products_count': file_type_counts['products'].get(error_type, 0),
                'description': self.error_patterns.get(error_type, {}).get('description', 'Unknown error')
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Save error type summary (no timestamp)
        summary_filename = "error_type_summary.csv"
        summary_path = os.path.join(self.output_dir, summary_filename)
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Created error type summary: {summary_path}")
        
        # Print summary to console
        logger.info(f"\n{'='*60}")
        logger.info("ERROR ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total failed records analyzed: {sum(total_error_counts.values())}")
        logger.info(f"Unique error types found: {len(total_error_counts)}")
        logger.info(f"\nTop error types:")
        for _, row in summary_df.head(10).iterrows():
            logger.info(f"  {row['error_type']}: {row['total_count']} records ({row['description']})")
    
    def run_analysis(self) -> None:
        """Run the complete error analysis."""
        logger.info("Running Import Error Analysis...")
        logger.info(f"Import results directory: {self.import_results_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Find CSV files in import-results directory
        csv_files = []
        if os.path.exists(self.import_results_dir):
            for file in os.listdir(self.import_results_dir):
                if file.endswith('.csv'):
                    csv_files.append(os.path.join(self.import_results_dir, file))
        
        if not csv_files:
            logger.info(f"No CSV files found in {self.import_results_dir}")
            return
        
        logger.info(f"Found CSV files: {[os.path.basename(f) for f in csv_files]}")
        
        # Analyze each file
        all_analyses = []
        for csv_file in csv_files:
            analysis = self.analyze_file(csv_file)
            all_analyses.append(analysis)
        
        # Create summary files
        self.create_summary_csv(all_analyses)
        self.create_error_type_summary(all_analyses)
        
        logger.info(f"Analysis complete! Results saved to: {self.output_dir}")


def find_products_file(test_mode=False):
    """Find the appropriate products file based on mode."""
    try:
        if test_mode:
            # Look for test file
            products_path = Path("datasource/test-data/products.xlsx")
            if not products_path.exists():
                raise FileNotFoundError(f"Test products file not found: {products_path}")
            return products_path, "test"
        else:
            # Look for production file
            products_path = Path("datasource/original-data/products.xlsx")
            if not products_path.exists():
                raise FileNotFoundError(f"Production products file not found: {products_path}")
            return products_path, "production"
    
    except Exception as e:
        logger.error(f"Error finding products file: {e}")
        sys.exit(1)


def load_products_data(products_path):
    """Load products data from Excel file."""
    try:
        logger.info(f"Loading products data from {products_path}...")
        products_df = pd.read_excel(products_path, engine='openpyxl')
        
        if products_df.empty:
            raise ValueError(f"Products file is empty: {products_path}")
        
        logger.info(f"Loaded {len(products_df)} product records")
        logger.info(f"Columns: {list(products_df.columns)}")
        
        return products_df
    
    except Exception as e:
        logger.error(f"Error loading products data: {e}")
        raise


def safe_str(value):
    """Safely convert a value to string, handling NaN and None values."""
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()


def convert_to_matrixify_format(products_df, mode="test"):
    """Convert products data to Matrixify format with proper variant grouping."""
    try:
        logger.info("Converting products to Matrixify format with variant grouping...")
        
        # First, create individual records with extracted base names and sizes
        temp_records = []
        
        for _, row in products_df.iterrows():
            # Extract key data from the input row with proper null handling
            product_name = safe_str(row.get('*Product Name*', ''))
            sku = safe_str(row.get('SKU', ''))
            price = row.get('*Price*', 0) if not pd.isna(row.get('*Price*', 0)) else 0
            cost = row.get('Cost', 0) if not pd.isna(row.get('Cost', 0)) else 0
            stock_qty = row.get('Stock Quantity', 0) if not pd.isna(row.get('Stock Quantity', 0)) else 0
            category = safe_str(row.get('*Category*', ''))
            vendor = safe_str(row.get('Vendor Name', ''))
            brand = safe_str(row.get('Brand name', ''))
            description = safe_str(row.get('Long Description', ''))
            image_url = safe_str(row.get('Image Url', ''))
            weight = row.get('Weight', 0) if not pd.isna(row.get('Weight', 0)) else 0
            
            # Extract base product name (without size) and size info
            base_name, size_info = extract_base_name_and_size(product_name)
            
            # Create handle from base product name
            handle = create_handle_from_name(base_name)
            
            # Store record with base name and extracted size
            temp_record = {
                'original_name': product_name,
                'base_name': base_name,
                'handle': handle,
                'size': size_info,
                'sku': sku,
                'price': float(price) if price else 0,
                'cost': float(cost) if cost else 0,
                'stock_qty': int(stock_qty) if stock_qty else 0,
                'category': category,
                'vendor': vendor or brand or '',
                'description': description,
                'image_url': image_url,
                'weight': weight
            }
            
            temp_records.append(temp_record)
        
        # Group records by handle (base product) and remove duplicates
        grouped_products = {}
        seen_combinations = set()  # Track handle+sku combinations to prevent duplicates
        
        for record in temp_records:
            handle = record['handle']
            sku = record['sku']
            
            # Skip if we've already seen this handle+sku combination
            combination_key = f"{handle}_{sku}"
            if combination_key in seen_combinations:
                logger.warning(f"Skipping duplicate combination: {handle} with SKU {sku}")
                continue
            
            seen_combinations.add(combination_key)
            
            if handle not in grouped_products:
                grouped_products[handle] = []
            grouped_products[handle].append(record)
        
        logger.info(f"Grouped {len(temp_records)} individual products into {len(grouped_products)} product groups (removed duplicates)")
        
        # Create Matrixify records with proper variant structure
        matrixify_data = []
        
        for handle, variants in grouped_products.items():
            # Remove variants with duplicate sizes within the same product
            unique_variants = []
            seen_sizes = set()
            
            # Sort variants by size for consistent ordering first
            variants.sort(key=lambda x: extract_numeric_size(x['size']))
            
            for variant in variants:
                size_key = f"{handle}_{variant['size']}"
                if size_key not in seen_sizes:
                    unique_variants.append(variant)
                    seen_sizes.add(size_key)
                else:
                    logger.warning(f"Skipping duplicate size '{variant['size']}' for handle '{handle}'")
            
            variants = unique_variants
            
            # Ensure we have a consistent base name across all variants
            # Use the most complete base name (longest non-empty one)
            base_names = [safe_str(v['base_name']) for v in variants if safe_str(v['base_name'])]
            if base_names:
                # Use the longest base name as the canonical one
                canonical_base_name = max(base_names, key=len)
            else:
                canonical_base_name = handle.replace('-', ' ').title()
            
            # Get the best description and vendor from available variants
            descriptions = [safe_str(v['description']) for v in variants if safe_str(v['description'])]
            canonical_description = descriptions[0] if descriptions else ''
            
            vendors = [safe_str(v['vendor']) for v in variants if safe_str(v['vendor'])]
            canonical_vendor = vendors[0] if vendors else ''
            
            categories = [safe_str(v['category']) for v in variants if safe_str(v['category'])]
            canonical_category = categories[0] if categories else ''
            
            for i, variant in enumerate(variants):
                # Only the first variant gets the full product info, others get blanks
                is_first_variant = (i == 0)
                
                # Ensure first variant always has a title
                title_value = canonical_base_name if is_first_variant else ''
                if is_first_variant and (not title_value or not str(title_value).strip()):
                    title_value = handle.replace('-', ' ').title()
                
                matrixify_record = {
                    'Handle': handle,
                    'Command': 'NEW' if is_first_variant else '',
                    'Title': title_value,
                    'Body HTML': clean_html_description(canonical_description) if is_first_variant else '',
                    'Vendor': canonical_vendor if is_first_variant else '',
                    'Metafield: custom.categories [single_line_text_field]': canonical_category if is_first_variant else '',
                    'Type': 'Pet Supplies' if is_first_variant else '',
                    'Tags': '',
                    'Published': 'TRUE' if is_first_variant else '',
                    'Option1 Name': 'Size' if is_first_variant else '',
                    'Option1 Value': variant['size'],
                    'Option2 Name': '',
                    'Option2 Value': '',
                    'Option3 Name': '',
                    'Option3 Value': '',
                    'Variant SKU': variant['sku'],
                    'Variant Grams': convert_weight_to_grams(variant['weight']),
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Qty': variant['stock_qty'],
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': variant['price'],
                    'Variant Compare At Price': '',
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'Variant Barcode': '',
                    'Image Src': variant['image_url'] if is_first_variant else '',
                    'Image Position': '1' if is_first_variant and variant['image_url'] else '',
                    'Image Alt Text': canonical_base_name if is_first_variant and variant['image_url'] else '',
                    'Gift Card': 'FALSE' if is_first_variant else '',
                    'SEO Title': canonical_base_name if is_first_variant else '',
                    'SEO Description': create_seo_description(canonical_base_name, canonical_description) if is_first_variant else '',
                    'Google Shopping / Google Product Category': '',
                    'Google Shopping / Gender': '',
                    'Google Shopping / Age Group': '',
                    'Google Shopping / MPN': '',
                    'Google Shopping / Condition': 'new' if is_first_variant else '',
                    'Google Shopping / Custom Product': 'TRUE' if is_first_variant else '',
                    'Variant Image': variant['image_url'],
                    'Variant Weight Unit': 'g',
                    'Variant Tax Code': '',
                    'Cost per item': variant['cost'],
                    'Status': 'active' if is_first_variant else ''
                }
                
                matrixify_data.append(matrixify_record)
        
        # Create DataFrame
        matrixify_df = pd.DataFrame(matrixify_data)
        
        logger.info(f"Created {len(matrixify_df)} variant records from {len(grouped_products)} products")
        logger.info(f"Created columns: {list(matrixify_df.columns)}")
        
        return matrixify_df
    
    except Exception as e:
        logger.error(f"Error converting to Matrixify format: {e}")
        raise


def extract_base_name_and_size(product_name):
    """Extract base product name and variant/size from full product name.
    
    This function extracts variants from anywhere in the title, not just at the end.
    For example: 'Kong - Cat Cat Sport Balls 2-Pk Assorted' becomes:
    - base_name: 'Kong - Cat Cat Sport Balls Assorted' 
    - size: '2-Pk'
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


def extract_numeric_size(size_str):
    """Extract numeric value from size string for sorting."""
    if not size_str:
        return 0
    
    # Extract first number found
    numbers = re.findall(r'\d+(?:\.\d+)?', str(size_str))
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    
    # Default ordering for non-numeric sizes
    size_order = {'small': 1, 'medium': 2, 'large': 3, 'xl': 4, 'xxl': 5, 'standard': 10}
    return size_order.get(str(size_str).lower(), 999)


def create_handle_from_name(product_name):
    """Create a Shopify handle from product name."""
    if not product_name:
        return 'unknown-product'
    
    # Convert to lowercase and replace spaces/special chars with hyphens
    handle = re.sub(r'[^\w\s-]', '', str(product_name).lower())
    handle = re.sub(r'[-\s]+', '-', handle)
    handle = handle.strip('-')
    
    return handle or 'unknown-product'


def extract_size_from_name(product_name):
    """Extract size information from product name.
    
    This function is kept for backward compatibility but now uses the
    improved extract_base_name_and_size function.
    """
    if not product_name:
        return 'Standard'
    
    _, size_info = extract_base_name_and_size(product_name)
    return size_info


def clean_html_description(description):
    """Clean and format HTML description for Matrixify."""
    if not description or pd.isna(description):
        return ''
    
    # Convert to string and clean up
    desc_str = str(description).strip()
    
    # If it's already HTML, return as is
    if '<' in desc_str and '>' in desc_str:
        return desc_str
    
    # Otherwise, wrap in paragraph tags
    return f'<p>{desc_str}</p>'


def create_seo_description(title, description):
    """Create SEO description from title and description."""
    if not title:
        return ''
    
    # Use first part of description or just title
    if description and not pd.isna(description):
        desc_text = re.sub(r'<[^>]+>', '', str(description))  # Strip HTML
        desc_text = desc_text.strip()[:150]  # Limit to 150 chars
        return f"{title} - {desc_text}..."
    
    return title


def convert_weight_to_grams(weight):
    """Convert weight to grams."""
    if not weight or pd.isna(weight):
        return 0
    
    try:
        weight_val = float(weight)
        # Assume weight is in some unit, convert to grams
        # This is a placeholder - you might need to adjust based on your data
        return int(weight_val * 1000) if weight_val > 0 else 0
    except:
        return 0


def save_matrixify_csv(matrixify_df, mode="test", stage="raw"):
    """Save the Matrixify DataFrame to CSV with appropriate naming."""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("matrixify-ready-products")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename based on mode and stage
        if mode == "test":
            output_filename = f"test_products_matrixify_{stage}.csv"
        else:
            timestamp = datetime.now().strftime('%Y_%m_%d_%H%M%S')
            output_filename = f"products_matrixify_{stage}_{timestamp}.csv"
        
        output_path = output_dir / output_filename
        
        logger.info(f"Saving Matrixify CSV to {output_path}...")
        start_time = time.time()
        
        # Save to CSV with proper formatting
        matrixify_df.to_csv(output_path, index=False)
        
        save_time = time.time() - start_time
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        
        logger.info(f"Successfully saved {len(matrixify_df):,} records to {output_path}")
        logger.info(f"File size: {file_size_mb:.2f} MB")
        logger.info(f"Save time: {save_time:.2f} seconds")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error saving Matrixify CSV: {e}")
        raise


def save_error_rows(error_rows_list, mode, step_name):
    """Save error/ignored rows to a separate file for manual review."""
    try:
        if not error_rows_list:
            return
        
        # Create error-rows directory
        error_dir = Path("error-rows")
        error_dir.mkdir(exist_ok=True)
        
        # Combine all error rows
        all_error_rows = pd.concat(error_rows_list, ignore_index=True)
        
        # Create timestamped filename following naming convention
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        error_filename = f"{mode}_{step_name}_error_rows_{timestamp}.csv"
        error_path = error_dir / error_filename
        
        # Save error rows to CSV file
        all_error_rows.to_csv(error_path, index=False)
        
        logger.info(f"Saved {len(all_error_rows):,} error/ignored rows to: {error_path}")
        
    except Exception as e:
        logger.warning(f"Could not save error rows: {e}")


def validate_output(output_path):
    """Validate the generated Matrixify CSV."""
    try:
        logger.info("Validating output file...")
        
        # Read first few rows to validate structure
        sample_df = pd.read_csv(output_path, nrows=5)
        
        logger.info(f"Output columns: {list(sample_df.columns)}")
        logger.info("Sample of Matrixify data:")
        logger.info(f"\n{sample_df.head()}")
        
        # Check for expected columns from template
        expected_columns = [
            'Handle', 'Title', 'Variant SKU', 'Status'
        ]
        
        missing_columns = [col for col in expected_columns if col not in sample_df.columns]
        if missing_columns:
            logger.warning(f"Missing expected columns: {missing_columns}")
        else:
            logger.info("✓ All expected columns present")
        
        logger.info("Validation completed")
        
    except Exception as e:
        logger.warning(f"Could not validate output file: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process products data to Matrixify CSV format with variant fixing and error analysis')
    parser.add_argument('--test', action='store_true', help='Run in test mode (uses test-data)')
    parser.add_argument('--analyze-errors', action='store_true', help='Run error analysis on import results')
    parser.add_argument('--skip-variant-fixing', action='store_true', help='Skip variant fixing step')
    parser.add_argument('--input-file', type=str, help='Custom input file path (overrides test/prod mode)')
    return parser.parse_args()


def setup_logging(test_mode=False):
    """Setup logging configuration based on mode."""
    mode_name = "test" if test_mode else "production"
    log_filename = f"logs/products_matrixify_{mode_name}.log"
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function to orchestrate the products processing."""
    start_time = time.time()
    
    # Parse arguments
    args = parse_arguments()
    
    try:
        # Handle error analysis if requested (special case)
        if args.analyze_errors and not args.input_file and not args.test:
            # Setup logging for error analysis only
            setup_logging(test_mode=True)
            
            logger.info("="*60)
            logger.info("Starting Import Error Analysis")
            logger.info("="*60)
            
            analyzer = ImportErrorAnalyzer()
            analyzer.run_analysis()
            
            logger.info("Error analysis completed.")
            return
        
        # Setup logging for normal processing
        setup_logging(args.test)
        
        logger.info("="*60)
        logger.info("Starting Products to Matrixify CSV Processing")
        if args.test:
            logger.info("Running in TEST MODE")
        else:
            logger.info("Running in PRODUCTION MODE")
        logger.info("="*60)
        
        # Handle error analysis if requested alongside processing
        if args.analyze_errors:
            logger.info("Running error analysis...")
            analyzer = ImportErrorAnalyzer()
            analyzer.run_analysis()
        
        # Find and load products data
        if args.input_file:
            products_path = Path(args.input_file)
            mode = "custom"
            if not products_path.exists():
                logger.error(f"Custom input file not found: {products_path}")
                sys.exit(1)
        else:
            products_path, mode = find_products_file(args.test)
        
        logger.info(f"Processing file: {products_path}")
        
        # Load products data
        products_df = load_products_data(products_path)
        
        # Convert to basic Matrixify format first
        matrixify_df = convert_to_matrixify_format(products_df, mode)
        
        # Save raw version
        raw_output_path = save_matrixify_csv(matrixify_df, mode, "raw")
        
        # Apply variant fixing if not skipped
        if not args.skip_variant_fixing:
            logger.info("Applying variant fixing...")
            
            # Initialize variant fixer
            fixer = CleanVariantFixer()
            
            # Check if we have the required columns for variant fixing
            required_variant_columns = ['Handle', 'Option1 Value', 'Variant SKU']
            if all(col in matrixify_df.columns for col in required_variant_columns):
                # Apply variant fixes
                fixed_df = fixer.fix_duplicate_variants_only(matrixify_df, products_df)
                
                # Save fixed version
                fixed_output_path = save_matrixify_csv(fixed_df, mode, "fixed")
                
                # Validate the fixed output
                validate_output(fixed_output_path)
                
                # Create summary report
                variant_groups_before = matrixify_df.groupby(['Handle', 'Option1 Value']).size().reset_index(name='count')
                duplicates_before = variant_groups_before[variant_groups_before['count'] > 1]
                
                variant_groups_after = fixed_df.groupby(['Handle', 'Option1 Value']).size().reset_index(name='count')
                duplicates_after = variant_groups_after[variant_groups_after['count'] > 1]
                
                # Save summary report
                summary_dir = Path("processed")
                summary_dir.mkdir(exist_ok=True)
                
                summary_filename = f"{mode}_products_processing_summary.txt"
                summary_path = summary_dir / summary_filename
                
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write("PRODUCTS TO MATRIXIFY PROCESSING SUMMARY\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Mode: {mode.upper()}\n")
                    f.write(f"Input file: {products_path}\n")
                    f.write(f"Total products processed: {len(matrixify_df)}\n\n")
                    f.write("VARIANT FIXING RESULTS:\n")
                    f.write(f"Original duplicate groups: {len(duplicates_before)}\n")
                    f.write(f"Groups processed: {fixer.fixed_count}\n")
                    f.write(f"Remaining duplicate groups: {len(duplicates_after)}\n")
                    if len(duplicates_before) > 0:
                        success_rate = ((len(duplicates_before) - len(duplicates_after)) / len(duplicates_before)) * 100
                        f.write(f"Success rate: {success_rate:.1f}%\n")
                    f.write(f"\nOutput files:\n")
                    f.write(f"Raw: {raw_output_path}\n")
                    f.write(f"Fixed: {fixed_output_path}\n")
                
                logger.info(f"Summary saved to: {summary_path}")
                
                # Final summary
                total_time = time.time() - start_time
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing completed successfully!")
                logger.info(f"Input records: {len(products_df):,}")
                logger.info(f"Output records: {len(fixed_df):,}")
                logger.info(f"Variant groups fixed: {fixer.fixed_count}")
                logger.info(f"Final output file: {fixed_output_path}")
                logger.info(f"Total execution time: {total_time:.2f} seconds")
                logger.info(f"{'='*60}")
                
            else:
                logger.warning(f"Missing required columns for variant fixing: {required_variant_columns}")
                logger.info("Skipping variant fixing step")
                validate_output(raw_output_path)
                
                # Final summary without variant fixing
                total_time = time.time() - start_time
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing completed successfully!")
                logger.info(f"Input records: {len(products_df):,}")
                logger.info(f"Output records: {len(matrixify_df):,}")
                logger.info(f"Output file: {raw_output_path}")
                logger.info(f"Total execution time: {total_time:.2f} seconds")
                logger.info(f"{'='*60}")
        else:
            logger.info("Variant fixing skipped as requested")
            validate_output(raw_output_path)
            
            # Final summary without variant fixing
            total_time = time.time() - start_time
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing completed successfully!")
            logger.info(f"Input records: {len(products_df):,}")
            logger.info(f"Output records: {len(matrixify_df):,}")
            logger.info(f"Output file: {raw_output_path}")
            logger.info(f"Total execution time: {total_time:.2f} seconds")
            logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
