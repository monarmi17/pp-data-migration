#!/usr/bin/env python3
"""
Region Orders Import Error Analysis Script

Analyzes failed orders imports from region-specific CSV files in the import-results directory.
Groups errors by generic error types and outputs summary CSV files for analysis.
Works independently of .env configuration and processes all region CSV files found.

Expected file pattern: [region]_matrixify_orders_[timestamp].csv
Example: brentwood_village_matrixify_orders_2025_09_23_164637.csv

Usage:
    python analyze_region_orders_import_errors.py [--output-dir OUTPUT_DIR] [--verbose]

Output:
    - error-analysis/ directory
    - [region]_orders_error_summary.csv files for each region
    - [region]_orders_error_type_summary.csv files for each region
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


class RegionOrdersErrorAnalyzer:
    """Analyzes orders import errors by region and groups them by generic error types."""
    
    def __init__(self, import_results_dir: str = "import-results", output_dir: str = "error-analysis"):
        self.import_results_dir = import_results_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Orders-specific error pattern definitions
        self.error_patterns = {
            'duplicate_sku_variants': {
                'pattern': r'Found \[(\d+)\] Variants with the same SKU \[([^\]]+)\]',
                'description': 'Duplicate SKU variants found',
                'severity': 'high'
            },
            'missing_line_item_fields': {
                'pattern': r'Line Items: Name can\'t be blank, Title can\'t be blank',
                'description': 'Missing required line item fields (Name/Title)',
                'severity': 'high'
            },
            'invalid_line_items': {
                'pattern': r'Order: Line items is invalid',
                'description': 'Invalid line items structure',
                'severity': 'high'
            },
            'missing_customer_info': {
                'pattern': r'Customer: Email can\'t be blank|Customer.*required',
                'description': 'Missing required customer information',
                'severity': 'medium'
            },
            'invalid_date_format': {
                'pattern': r'date.*invalid|invalid.*date|created_at.*invalid',
                'description': 'Invalid date format',
                'severity': 'medium'
            },
            'missing_payment_info': {
                'pattern': r'Payment.*can\'t be blank|Transaction.*required',
                'description': 'Missing payment information',
                'severity': 'medium'
            },
            'invalid_fulfillment_status': {
                'pattern': r'Fulfillment.*invalid|invalid.*fulfillment',
                'description': 'Invalid fulfillment status',
                'severity': 'low'
            },
            'duplicate_order_name': {
                'pattern': r'Order name.*taken|Name.*already exists',
                'description': 'Duplicate order names',
                'severity': 'medium'
            },
            'validation_error': {
                'pattern': r'validation|invalid|error',
                'description': 'General validation errors',
                'severity': 'low'
            },
            'duplicate_identifier': {
                'pattern': r'duplicate|already exists|taken',
                'description': 'Duplicate identifiers',
                'severity': 'medium'
            }
        }
    
    def find_region_csv_files(self) -> Dict[str, str]:
        """Find all region-specific CSV files in import-results directory."""
        region_files = {}
        
        if not os.path.exists(self.import_results_dir):
            logger.warning(f"Import results directory not found: {self.import_results_dir}")
            return region_files
        
        # Look for CSV files that might be region-specific
        for file in os.listdir(self.import_results_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(self.import_results_dir, file)
                
                # Try to determine if this is an orders file
                try:
                    # Read a few rows to check if it's an orders file (suppress warnings for sample)
                    sample_df = pd.read_csv(file_path, nrows=5, low_memory=False)
                    
                    # Check for orders-specific columns
                    orders_columns = ['Name', 'Line: SKU', 'Customer: Email', 'Processed At']
                    if any(col in sample_df.columns for col in orders_columns):
                        # Extract region name from filename
                        region_name = self.extract_region_from_filename(file)
                        region_files[region_name] = file_path
                        logger.info(f"Found orders file for region '{region_name}': {file}")
                    
                except Exception as e:
                    logger.warning(f"Could not analyze file {file}: {e}")
        
        return region_files
    
    def extract_region_from_filename(self, filename: str) -> str:
        """Extract region name from filename."""
        # Remove .csv extension
        base_name = filename.replace('.csv', '')
        
        # Primary pattern: [region]_matrixify_orders_[timestamp]
        # Example: brentwood_village_matrixify_orders_2025_09_23_164637
        matrixify_orders_pattern = r'^(.+)_matrixify_orders_\d{4}_\d{2}_\d{2}_\d{6}$'
        match = re.match(matrixify_orders_pattern, base_name, re.IGNORECASE)
        if match:
            region = match.group(1)
            return region.replace('-', '_').lower()
        
        # Fallback patterns for other order file formats
        fallback_patterns = [
            r'^([^_]+)_.*orders.*',  # region_something_orders
            r'.*orders.*_([^_]+)$',  # something_orders_region
            r'^([^_]+)_.*',          # region_anything
            r'.*_([^_]+)$'           # anything_region
        ]
        
        for pattern in fallback_patterns:
            match = re.match(pattern, base_name, re.IGNORECASE)
            if match:
                region = match.group(1)
                # Clean up common non-region words
                if region.lower() not in ['orders', 'matrixify', 'import', 'results', 'error']:
                    return region.replace('-', '_').lower()
        
        # If no pattern matches, use the base filename
        return base_name.replace('-', '_').lower()
    
    def load_failed_records(self, file_path: str) -> pd.DataFrame:
        """Load only failed records from a CSV file."""
        try:
            # Use low_memory=False to avoid mixed type warnings for large files
            df = pd.read_csv(file_path, low_memory=False)
            
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
            'extracted_values': {}
        }
        
        # Check each error pattern
        for error_key, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            if re.search(pattern, comment, re.IGNORECASE):
                error_details['error_type'] = error_key
                error_details['error_description'] = error_config['description']
                error_details['severity'] = error_config['severity']
                
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
            'order_name': row.get('Name', ''),
            'sku': row.get('Line: SKU', ''),
            'customer_email': row.get('Customer: Email', ''),
            'processed_at': row.get('Processed At', ''),
            'transaction_amount': row.get('Transaction: Amount', ''),
            'payment_status': row.get('Payment: Status', ''),
            'fulfillment_status': row.get('Fulfillment: Status', ''),
            'line_item_name': row.get('Line: Name', ''),
            'line_item_title': row.get('Line: Title', ''),
            'line_item_quantity': row.get('Line: Quantity', ''),
            'line_item_price': row.get('Line: Price', '')
        }
        
        return identifiers
    
    def analyze_region_file(self, region_name: str, file_path: str) -> Dict[str, Any]:
        """Analyze failed imports from a single region file."""
        filename = os.path.basename(file_path)
        
        logger.info(f"Analyzing region '{region_name}' from file: {filename}")
        
        # Load failed records
        failed_df = self.load_failed_records(file_path)
        if failed_df.empty:
            logger.info(f"No failed records found in {filename}")
            return {}
        
        # Analyze each failed record
        analysis_results = []
        error_counts = Counter()
        severity_counts = Counter()
        
        for idx, row in failed_df.iterrows():
            # Extract error details
            error_details = self.extract_error_details(row.get('Import Comment', ''))
            
            # Get key identifiers
            identifiers = self.get_key_identifiers(row)
            
            # Create analysis record
            analysis_record = {
                'region': region_name,
                'row_index': idx,
                'error_type': error_details['error_type'],
                'error_description': error_details['error_description'],
                'severity': error_details['severity'],
                'raw_comment': error_details['raw_comment'],
                **identifiers,
                **error_details['extracted_values']
            }
            
            analysis_results.append(analysis_record)
            error_counts[error_details['error_type']] += 1
            severity_counts[error_details['severity']] += 1
        
        # Create summary
        summary = {
            'region': region_name,
            'total_failed_records': len(failed_df),
            'error_counts': dict(error_counts),
            'severity_counts': dict(severity_counts),
            'analysis_results': analysis_results
        }
        
        logger.info(f"Region '{region_name}': {len(failed_df)} failed records with {len(error_counts)} error types")
        for error_type, count in error_counts.most_common():
            logger.info(f"  - {error_type}: {count} records")
        
        return summary
    
    def create_region_summary_csv(self, region_analysis: Dict[str, Any]) -> None:
        """Create summary CSV files for a specific region."""
        if not region_analysis:
            return
        
        region_name = region_analysis['region']
        results_df = pd.DataFrame(region_analysis['analysis_results'])
        
        # Create detailed orders error summary
        orders_summary_filename = f"{region_name}_orders_error_summary.csv"
        orders_summary_path = os.path.join(self.output_dir, orders_summary_filename)
        
        # Select significant columns for orders analysis
        significant_columns = [
            'error_type', 'error_description', 'severity', 'order_name', 'sku', 
            'customer_email', 'processed_at', 'transaction_amount',
            'payment_status', 'fulfillment_status', 'line_item_name', 
            'line_item_title', 'line_item_quantity', 'line_item_price', 'raw_comment'
        ]
        
        # Filter to available columns
        available_columns = [col for col in significant_columns if col in results_df.columns]
        summary_df = results_df[available_columns].copy()
        
        # Sort by severity and error type for better analysis
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        summary_df['severity_order'] = summary_df['severity'].map(severity_order)
        summary_df = summary_df.sort_values(['severity_order', 'error_type', 'error_description'])
        summary_df = summary_df.drop('severity_order', axis=1)
        
        # Save detailed summary
        summary_df.to_csv(orders_summary_path, index=False)
        logger.info(f"Created orders error summary: {orders_summary_path}")
        
        # Create error type summary for this region
        error_type_summary_data = []
        for error_type, count in region_analysis['error_counts'].items():
            error_config = self.error_patterns.get(error_type, {})
            error_type_summary_data.append({
                'region': region_name,
                'error_type': error_type,
                'count': count,
                'severity': error_config.get('severity', 'unknown'),
                'description': error_config.get('description', 'Unknown error')
            })
        
        error_type_df = pd.DataFrame(error_type_summary_data)
        
        # Sort by severity and count
        severity_order = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}
        error_type_df['severity_order'] = error_type_df['severity'].map(severity_order)
        error_type_df = error_type_df.sort_values(['severity_order', 'count'], ascending=[True, False])
        error_type_df = error_type_df.drop('severity_order', axis=1)
        
        # Save error type summary
        error_type_summary_filename = f"{region_name}_orders_error_type_summary.csv"
        error_type_summary_path = os.path.join(self.output_dir, error_type_summary_filename)
        error_type_df.to_csv(error_type_summary_path, index=False)
        logger.info(f"Created error type summary: {error_type_summary_path}")
    
    def create_consolidated_summary(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create a consolidated summary across all regions."""
        if not all_analyses:
            return
        
        # Combine all error counts by region
        consolidated_data = []
        total_error_counts = Counter()
        
        for analysis in all_analyses:
            if not analysis:
                continue
            
            region_name = analysis['region']
            error_counts = analysis['error_counts']
            severity_counts = analysis['severity_counts']
            
            for error_type, count in error_counts.items():
                error_config = self.error_patterns.get(error_type, {})
                consolidated_data.append({
                    'region': region_name,
                    'error_type': error_type,
                    'count': count,
                    'severity': error_config.get('severity', 'unknown'),
                    'description': error_config.get('description', 'Unknown error')
                })
                total_error_counts[error_type] += count
        
        if consolidated_data:
            consolidated_df = pd.DataFrame(consolidated_data)
            
            # Save consolidated summary
            consolidated_path = os.path.join(self.output_dir, "all_regions_orders_error_summary.csv")
            consolidated_df.to_csv(consolidated_path, index=False)
            logger.info(f"Created consolidated summary: {consolidated_path}")
            
            # Print summary to console
            logger.info(f"\n{'='*60}")
            logger.info("REGION ORDERS ERROR ANALYSIS SUMMARY")
            logger.info(f"{'='*60}")
            
            total_failed = sum(analysis.get('total_failed_records', 0) for analysis in all_analyses if analysis)
            logger.info(f"Total failed records across all regions: {total_failed}")
            logger.info(f"Total regions analyzed: {len([a for a in all_analyses if a])}")
            logger.info(f"Unique error types found: {len(total_error_counts)}")
            
            logger.info(f"\nTop error types across all regions:")
            for error_type, total_count in total_error_counts.most_common(10):
                description = self.error_patterns.get(error_type, {}).get('description', 'Unknown error')
                severity = self.error_patterns.get(error_type, {}).get('severity', 'unknown')
                logger.info(f"  {error_type}: {total_count} records ({severity} severity - {description})")
            
            logger.info(f"\nBy region:")
            for analysis in all_analyses:
                if analysis:
                    region_name = analysis['region']
                    failed_count = analysis['total_failed_records']
                    error_types = len(analysis['error_counts'])
                    logger.info(f"  {region_name}: {failed_count} failed records, {error_types} error types")
    
    def run_analysis(self) -> None:
        """Run the complete region orders error analysis."""
        logger.info("Starting Region Orders Import Error Analysis...")
        logger.info(f"Import results directory: {self.import_results_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Find region CSV files
        region_files = self.find_region_csv_files()
        
        if not region_files:
            logger.warning(f"No region orders CSV files found in {self.import_results_dir}")
            return
        
        logger.info(f"Found region files: {list(region_files.keys())}")
        
        # Analyze each region file
        all_analyses = []
        for region_name, file_path in region_files.items():
            analysis = self.analyze_region_file(region_name, file_path)
            if analysis:
                all_analyses.append(analysis)
                # Create region-specific summary files
                self.create_region_summary_csv(analysis)
        
        # Create consolidated summary
        self.create_consolidated_summary(all_analyses)
        
        logger.info(f"\nAnalysis complete! Results saved to: {self.output_dir}")


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    log_filename = f"logs/region_orders_error_analysis.log"
    
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
        description="Analyze failed orders imports from region-specific CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze_region_orders_import_errors.py
    python analyze_region_orders_import_errors.py --output-dir custom-analysis
    python analyze_region_orders_import_errors.py --verbose
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
        analyzer = RegionOrdersErrorAnalyzer(
            import_results_dir=args.import_results_dir,
            output_dir=args.output_dir
        )
        
        analyzer.run_analysis()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
