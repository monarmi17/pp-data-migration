#!/usr/bin/env python3
"""
Products Import Error Analysis Script

Analyzes failed products imports from CSV files in the import-results directory.
Groups errors by generic error types and outputs summary CSV files for analysis.
Focuses specifically on product-related import errors.

Usage:
    python analyze_products_import_errors.py [--output-dir OUTPUT_DIR] [--verbose]

Output:
    - error-analysis/ directory
    - products_error_type_summary.csv
    - products_error_summary.csv
"""

import pandas as pd
import re
import os
import argparse
import logging
import sys
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class ProductsErrorAnalyzer:
    """Analyzes products import errors and groups them by generic error types."""
    
    def __init__(self, import_results_dir: str = "import-results", output_dir: str = "error-analysis"):
        self.import_results_dir = import_results_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Products-specific error pattern definitions
        self.error_patterns = {
            'inconsistent_title': {
                'pattern': r'"Title" differs in each row|title.*inconsistent|inconsistent.*title',
                'description': 'Inconsistent product titles across variants',
                'severity': 'high',
                'category': 'data_consistency'
            },
            'inconsistent_body_html': {
                'pattern': r'"Body HTML" differs in each row|description.*inconsistent|inconsistent.*description',
                'description': 'Inconsistent product descriptions across variants',
                'severity': 'medium',
                'category': 'data_consistency'
            },
            'inconsistent_vendor': {
                'pattern': r'"Vendor" differs in each row|vendor.*inconsistent|inconsistent.*vendor',
                'description': 'Inconsistent vendor information across variants',
                'severity': 'medium',
                'category': 'data_consistency'
            },
            'missing_required_fields': {
                'pattern': r'can\'t be blank|required.*missing|missing.*required',
                'description': 'Missing required product fields',
                'severity': 'high',
                'category': 'missing_data'
            },
            'missing_title': {
                'pattern': r'Title.*can\'t be blank|title.*required',
                'description': 'Missing product title',
                'severity': 'high',
                'category': 'missing_data'
            },
            'missing_handle': {
                'pattern': r'Handle.*can\'t be blank|handle.*required',
                'description': 'Missing product handle',
                'severity': 'high',
                'category': 'missing_data'
            },
            'missing_sku': {
                'pattern': r'SKU.*can\'t be blank|sku.*required|variant.*sku.*required',
                'description': 'Missing variant SKU',
                'severity': 'high',
                'category': 'missing_data'
            },
            'duplicate_handle': {
                'pattern': r'Handle.*taken|handle.*already exists|duplicate.*handle',
                'description': 'Duplicate product handles',
                'severity': 'high',
                'category': 'duplicates'
            },
            'duplicate_sku': {
                'pattern': r'SKU.*taken|sku.*already exists|duplicate.*sku',
                'description': 'Duplicate product SKUs',
                'severity': 'high',
                'category': 'duplicates'
            },
            'invalid_price': {
                'pattern': r'price.*invalid|invalid.*price|price.*format',
                'description': 'Invalid price format or value',
                'severity': 'medium',
                'category': 'data_format'
            },
            'invalid_weight': {
                'pattern': r'weight.*invalid|invalid.*weight|weight.*format',
                'description': 'Invalid weight format or value',
                'severity': 'low',
                'category': 'data_format'
            },
            'invalid_inventory': {
                'pattern': r'inventory.*invalid|invalid.*inventory|stock.*invalid',
                'description': 'Invalid inventory quantity',
                'severity': 'medium',
                'category': 'data_format'
            },
            'invalid_option_values': {
                'pattern': r'option.*invalid|invalid.*option|variant.*option',
                'description': 'Invalid option values for variants',
                'severity': 'medium',
                'category': 'variant_issues'
            },
            'too_many_variants': {
                'pattern': r'too many variants|variant.*limit|maximum.*variants',
                'description': 'Too many variants for a single product',
                'severity': 'medium',
                'category': 'variant_issues'
            },
            'image_upload_error': {
                'pattern': r'image.*error|invalid.*image|image.*upload',
                'description': 'Image upload or processing errors',
                'severity': 'low',
                'category': 'media'
            },
            'metafield_error': {
                'pattern': r'metafield.*error|invalid.*metafield|metafield.*format',
                'description': 'Metafield validation errors',
                'severity': 'low',
                'category': 'metadata'
            },
            'validation_error': {
                'pattern': r'validation|invalid|error',
                'description': 'General validation errors',
                'severity': 'low',
                'category': 'general'
            },
            'duplicate_identifier': {
                'pattern': r'duplicate|already exists|taken',
                'description': 'General duplicate identifiers',
                'severity': 'medium',
                'category': 'duplicates'
            }
        }
    
    def find_products_csv_files(self) -> List[str]:
        """Find all products-related CSV files in import-results directory."""
        products_files = []
        
        if not os.path.exists(self.import_results_dir):
            logger.warning(f"Import results directory not found: {self.import_results_dir}")
            return products_files
        
        # Look for CSV files that might be products-related
        for file in os.listdir(self.import_results_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(self.import_results_dir, file)
                
                # Try to determine if this is a products file
                try:
                    # Read a few rows to check if it's a products file
                    sample_df = pd.read_csv(file_path, nrows=5)
                    
                    # Check for products-specific columns
                    products_columns = ['Handle', 'Title', 'Variant SKU', 'Vendor', 'Option1 Name']
                    if any(col in sample_df.columns for col in products_columns):
                        products_files.append(file_path)
                        logger.info(f"Found products file: {file}")
                    
                except Exception as e:
                    logger.warning(f"Could not analyze file {file}: {e}")
        
        return products_files
    
    def load_failed_records(self, file_path: str) -> pd.DataFrame:
        """Load only failed records from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            
            # Check if Import Result column exists
            if 'Import Result' not in df.columns:
                logger.warning(f"No 'Import Result' column found in {os.path.basename(file_path)}")
                return pd.DataFrame()
            
            failed_df = df[df['Import Result'] == 'Failed'].copy()
            logger.info(f"Loaded {len(failed_df)} failed records from {os.path.basename(file_path)}")
            return failed_df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def extract_error_details(self, comment: str) -> Dict[str, Any]:
        """Extract structured error details from import comment."""
        if pd.isna(comment):
            comment = ""
        
        error_details = {
            'raw_comment': comment,
            'error_type': 'unknown',
            'error_description': 'Unknown error',
            'severity': 'low',
            'category': 'general',
            'extracted_values': {}
        }
        
        # Check each error pattern (in order of specificity)
        for error_key, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            if re.search(pattern, comment, re.IGNORECASE):
                error_details['error_type'] = error_key
                error_details['error_description'] = error_config['description']
                error_details['severity'] = error_config['severity']
                error_details['category'] = error_config['category']
                
                # Extract specific values using regex groups
                match = re.search(pattern, comment, re.IGNORECASE)
                if match and match.groups():
                    error_details['extracted_values'] = {
                        f'group_{i+1}': group for i, group in enumerate(match.groups())
                    }
                break
        
        return error_details
    
    def get_key_identifiers(self, row: pd.Series) -> Dict[str, Any]:
        """Extract key identifiers for backtracking issues."""
        identifiers = {
            'handle': row.get('Handle', ''),
            'variant_sku': row.get('Variant SKU', ''),
            'title': row.get('Title', ''),
            'vendor': row.get('Vendor', ''),
            'status': row.get('Status', ''),
            'variant_price': row.get('Variant Price', ''),
            'cost_per_item': row.get('Cost per item', ''),
            'option1_name': row.get('Option1 Name', ''),
            'option1_value': row.get('Option1 Value', ''),
            'option2_name': row.get('Option2 Name', ''),
            'option2_value': row.get('Option2 Value', ''),
            'variant_inventory_qty': row.get('Variant Inventory Qty', ''),
            'variant_weight': row.get('Variant Grams', ''),
            'product_type': row.get('Type', ''),
            'tags': row.get('Tags', '')
        }
        
        return identifiers
    
    def analyze_products_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze failed imports from a single products file."""
        filename = os.path.basename(file_path)
        
        logger.info(f"Analyzing products file: {filename}")
        
        # Load failed records
        failed_df = self.load_failed_records(file_path)
        if failed_df.empty:
            logger.info(f"No failed records found in {filename}")
            return {}
        
        # Analyze each failed record
        analysis_results = []
        error_counts = Counter()
        severity_counts = Counter()
        category_counts = Counter()
        
        for idx, row in failed_df.iterrows():
            # Extract error details
            error_details = self.extract_error_details(row.get('Import Comment', ''))
            
            # Get key identifiers
            identifiers = self.get_key_identifiers(row)
            
            # Create analysis record
            analysis_record = {
                'file_name': filename,
                'row_index': idx,
                'error_type': error_details['error_type'],
                'error_description': error_details['error_description'],
                'severity': error_details['severity'],
                'category': error_details['category'],
                'raw_comment': error_details['raw_comment'],
                **identifiers,
                **error_details['extracted_values']
            }
            
            analysis_results.append(analysis_record)
            error_counts[error_details['error_type']] += 1
            severity_counts[error_details['severity']] += 1
            category_counts[error_details['category']] += 1
        
        # Create summary
        summary = {
            'file_name': filename,
            'total_failed_records': len(failed_df),
            'error_counts': dict(error_counts),
            'severity_counts': dict(severity_counts),
            'category_counts': dict(category_counts),
            'analysis_results': analysis_results
        }
        
        logger.info(f"File '{filename}': {len(failed_df)} failed records with {len(error_counts)} error types")
        for error_type, count in error_counts.most_common():
            logger.info(f"  - {error_type}: {count} records")
        
        return summary
    
    def create_products_summary_csv(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create summary CSV files for products analysis."""
        if not all_analyses:
            return
        
        # Combine all analysis results
        all_results = []
        for analysis in all_analyses:
            if analysis and 'analysis_results' in analysis:
                all_results.extend(analysis['analysis_results'])
        
        if not all_results:
            return
        
        results_df = pd.DataFrame(all_results)
        
        # Create detailed products error summary
        products_summary_filename = "products_error_summary.csv"
        products_summary_path = os.path.join(self.output_dir, products_summary_filename)
        
        # Select significant columns for products analysis
        significant_columns = [
            'error_type', 'error_description', 'severity', 'category', 
            'handle', 'variant_sku', 'title', 'vendor', 'status', 
            'variant_price', 'cost_per_item', 'option1_name', 'option1_value',
            'option2_name', 'option2_value', 'variant_inventory_qty', 
            'variant_weight', 'product_type', 'tags', 'raw_comment'
        ]
        
        # Filter to available columns
        available_columns = [col for col in significant_columns if col in results_df.columns]
        summary_df = results_df[available_columns].copy()
        
        # Sort by severity, category, and error type for better analysis
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        summary_df['severity_order'] = summary_df['severity'].map(severity_order)
        summary_df = summary_df.sort_values(['severity_order', 'category', 'error_type', 'error_description'])
        summary_df = summary_df.drop('severity_order', axis=1)
        
        # Save detailed summary
        summary_df.to_csv(products_summary_path, index=False)
        logger.info(f"Created products error summary: {products_summary_path}")
        
        # Create error type summary
        self.create_error_type_summary(all_analyses)
    
    def create_error_type_summary(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create a high-level error type summary for products."""
        
        # Combine all error counts
        total_error_counts = Counter()
        total_severity_counts = Counter()
        total_category_counts = Counter()
        
        for analysis in all_analyses:
            if not analysis:
                continue
            
            error_counts = analysis.get('error_counts', {})
            severity_counts = analysis.get('severity_counts', {})
            category_counts = analysis.get('category_counts', {})
            
            for error_type, count in error_counts.items():
                total_error_counts[error_type] += count
            
            for severity, count in severity_counts.items():
                total_severity_counts[severity] += count
            
            for category, count in category_counts.items():
                total_category_counts[category] += count
        
        # Create error type summary DataFrame
        error_type_summary_data = []
        for error_type, total_count in total_error_counts.most_common():
            error_config = self.error_patterns.get(error_type, {})
            error_type_summary_data.append({
                'error_type': error_type,
                'count': total_count,
                'severity': error_config.get('severity', 'unknown'),
                'category': error_config.get('category', 'unknown'),
                'description': error_config.get('description', 'Unknown error')
            })
        
        error_type_df = pd.DataFrame(error_type_summary_data)
        
        # Sort by severity and count
        severity_order = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}
        error_type_df['severity_order'] = error_type_df['severity'].map(severity_order)
        error_type_df = error_type_df.sort_values(['severity_order', 'count'], ascending=[True, False])
        error_type_df = error_type_df.drop('severity_order', axis=1)
        
        # Save error type summary
        error_type_summary_filename = "products_error_type_summary.csv"
        error_type_summary_path = os.path.join(self.output_dir, error_type_summary_filename)
        error_type_df.to_csv(error_type_summary_path, index=False)
        logger.info(f"Created products error type summary: {error_type_summary_path}")
        
        # Print summary to console
        logger.info(f"\n{'='*60}")
        logger.info("PRODUCTS IMPORT ERROR ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        
        total_failed = sum(analysis.get('total_failed_records', 0) for analysis in all_analyses if analysis)
        logger.info(f"Total failed product records: {total_failed}")
        logger.info(f"Total files analyzed: {len([a for a in all_analyses if a])}")
        logger.info(f"Unique error types found: {len(total_error_counts)}")
        
        logger.info(f"\nTop error types:")
        for error_type, total_count in total_error_counts.most_common(10):
            error_config = self.error_patterns.get(error_type, {})
            description = error_config.get('description', 'Unknown error')
            severity = error_config.get('severity', 'unknown')
            category = error_config.get('category', 'unknown')
            logger.info(f"  {error_type}: {total_count} records ({severity} severity, {category} category)")
            logger.info(f"    {description}")
        
        logger.info(f"\nBy severity:")
        for severity, count in total_severity_counts.most_common():
            logger.info(f"  {severity}: {count} records")
        
        logger.info(f"\nBy category:")
        for category, count in total_category_counts.most_common():
            logger.info(f"  {category}: {count} records")
    
    def run_analysis(self) -> None:
        """Run the complete products error analysis."""
        logger.info("Starting Products Import Error Analysis...")
        logger.info(f"Import results directory: {self.import_results_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Find products CSV files
        products_files = self.find_products_csv_files()
        
        if not products_files:
            logger.warning(f"No products CSV files found in {self.import_results_dir}")
            return
        
        logger.info(f"Found products files: {[os.path.basename(f) for f in products_files]}")
        
        # Analyze each products file
        all_analyses = []
        for file_path in products_files:
            analysis = self.analyze_products_file(file_path)
            if analysis:
                all_analyses.append(analysis)
        
        # Create summary files
        self.create_products_summary_csv(all_analyses)
        
        logger.info(f"\nAnalysis complete! Results saved to: {self.output_dir}")


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    log_filename = f"logs/products_error_analysis.log"
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Analyze failed products imports from CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze_products_import_errors.py
    python analyze_products_import_errors.py --output-dir custom-analysis
    python analyze_products_import_errors.py --verbose
        """
    )
    
    parser.add_argument(
        '--output-dir',
        default='error-analysis',
        help='Output directory for analysis results (default: error-analysis)'
    )
    
    parser.add_argument(
        '--import-results-dir',
        default='import-results',
        help='Directory containing import result CSV files (default: import-results)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        # Create analyzer and run analysis
        analyzer = ProductsErrorAnalyzer(
            import_results_dir=args.import_results_dir,
            output_dir=args.output_dir
        )
        
        analyzer.run_analysis()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
