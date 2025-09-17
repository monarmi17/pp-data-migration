#!/usr/bin/env python3
"""
Orders to Matrixify CSV Converter

This script converts processed orders from orders.xlsx to Matrixify CSV format.
Each row represents a line item grouped by Product Code, with proper timestamps
and all required Matrixify fields.

Column Mapping:
- Name -> Ticket Number
- Command -> Always 'NEW'
- Processed At -> Generated timestamp based on Date
- Customer: Email -> Email
- Line: Type -> Always 'Line Item'
- Line: SKU -> Product Code
- Line: Quantity -> Product quantity
- Line: Price -> Price ($)
- Line: Grams -> Always 0 (as per template)
- Line: Requires Shipping -> Always TRUE
- Line: Vendor -> Empty (as per template)
- Transaction: Kind -> Always 'sale'
- Transaction: Processed At -> Same as Processed At
- Transaction: Amount -> Price ($)
- Payment: Status -> Always 'paid'
- Fulfillment: Status -> Always 'success'
- Fulfillment: Processed At -> Same as Processed At
- Fulfillment: Tracking Number -> Empty
- Fulfillment: Shipment Status -> Always 'delivered'

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('matrixify_converter.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def generate_timestamp_from_date(date_str):
    """
    Generate a logical timestamp based on the date string.
    Adds random hours/minutes to make it look realistic.
    """
    try:
        # Parse the date string (assuming format like "2024-01-15" or similar)
        if pd.isna(date_str) or date_str == '':
            # Default to today if date is missing
            base_date = datetime.now()
        else:
            # Try to parse various date formats
            date_str = str(date_str).strip()
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        base_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format matches, try pandas parsing
                    base_date = pd.to_datetime(date_str)
            except:
                logger.warning(f"Could not parse date '{date_str}', using current date")
                base_date = datetime.now()
        
        # Add random hours (9-17 for business hours) and minutes
        random_hour = random.randint(9, 17)
        random_minute = random.randint(0, 59)
        
        # Create final timestamp
        final_datetime = base_date.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
        
        # Format as M/D/YYYY H:MM (matching template format)
        return final_datetime.strftime('%-m/%-d/%Y %-H:%M')
    
    except Exception as e:
        logger.warning(f"Error generating timestamp for date '{date_str}': {e}")
        # Fallback to current time
        return datetime.now().strftime('%-m/%-d/%Y %-H:%M')


def load_processed_orders():
    """Load the processed orders data."""
    try:
        orders_path = Path("processed/orders.xlsx")
        if not orders_path.exists():
            raise FileNotFoundError(f"Processed orders file not found: {orders_path}")
        
        logger.info("Loading processed orders data...")
        start_time = time.time()
        
        # Load the processed orders
        orders_df = pd.read_excel(orders_path, engine='openpyxl')
        
        load_time = time.time() - start_time
        logger.info(f"Loaded orders data: {len(orders_df):,} records in {load_time:.2f} seconds")
        
        # Validate required columns
        required_columns = [
            'Ticket number', 'Date', 'Email', 'Product Code', 
            'Product quantity', 'Price ($)'
        ]
        
        missing_columns = [col for col in required_columns if col not in orders_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logger.info(f"Available columns: {list(orders_df.columns)}")
        return orders_df
    
    except Exception as e:
        logger.error(f"Error loading processed orders: {e}")
        sys.exit(1)


def convert_to_matrixify_format(orders_df):
    """Convert orders data to Matrixify CSV format."""
    try:
        logger.info("Converting to Matrixify format...")
        start_time = time.time()
        
        # Filter out rows where Product Code is NaN (unmapped products)
        initial_count = len(orders_df)
        orders_df = orders_df.dropna(subset=['Product Code'])
        filtered_count = len(orders_df)
        
        if filtered_count < initial_count:
            logger.warning(f"Filtered out {initial_count - filtered_count} rows with missing Product Code")
        
        # Create the Matrixify DataFrame
        matrixify_data = []
        
        logger.info("Processing orders for Matrixify format...")
        
        for index, row in orders_df.iterrows():
            # Generate timestamp from date
            processed_at = generate_timestamp_from_date(row['Date'])
            
            # Create Matrixify row
            matrixify_row = {
                'Name': str(int(row['Ticket number'])),  # Convert to string, ensure no decimals
                'Command': 'NEW',
                'Processed At': processed_at,
                'Customer: Email': str(row['Email']).strip(),
                'Line: Type': 'Line Item',
                'Line: SKU': str(int(row['Product Code'])).zfill(12),  # Ensure 12-digit format
                'Line: Quantity': int(row['Product quantity']),
                'Line: Price': float(row['Price ($)']),
                'Line: Grams': 0,
                'Line: Requires Shipping': 'TRUE',
                'Line: Vendor': '',  # Empty as per template
                'Transaction: Kind': 'sale',
                'Transaction: Processed At': processed_at,
                'Transaction: Amount': float(row['Price ($)']),
                'Payment: Status': 'paid',
                'Fulfillment: Status': 'success',
                'Fulfillment: Processed At': processed_at,
                'Fulfillment: Tracking Number': '',  # Empty as per template
                'Fulfillment: Shipment Status': 'delivered'
            }
            
            matrixify_data.append(matrixify_row)
            
            # Log progress for large datasets
            if (index + 1) % 10000 == 0:
                logger.info(f"Processed {index + 1:,} records...")
        
        # Create DataFrame
        matrixify_df = pd.DataFrame(matrixify_data)
        
        conversion_time = time.time() - start_time
        logger.info(f"Conversion completed: {len(matrixify_df):,} records in {conversion_time:.2f} seconds")
        
        return matrixify_df
    
    except Exception as e:
        logger.error(f"Error converting to Matrixify format: {e}")
        raise


def save_matrixify_csv(matrixify_df, output_filename="matrixify_orders.csv"):
    """Save the Matrixify DataFrame to CSV."""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
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
            'Name', 'Command', 'Processed At', 'Customer: Email',
            'Line: Type', 'Line: SKU', 'Line: Quantity', 'Line: Price',
            'Line: Grams', 'Line: Requires Shipping', 'Line: Vendor',
            'Transaction: Kind', 'Transaction: Processed At', 'Transaction: Amount',
            'Payment: Status', 'Fulfillment: Status', 'Fulfillment: Processed At',
            'Fulfillment: Tracking Number', 'Fulfillment: Shipment Status'
        ]
        
        missing_columns = [col for col in expected_columns if col not in sample_df.columns]
        if missing_columns:
            logger.warning(f"Missing expected columns: {missing_columns}")
        else:
            logger.info("✓ All expected columns present")
        
        # Validate some key fields
        if 'Command' in sample_df.columns:
            unique_commands = sample_df['Command'].unique()
            if len(unique_commands) == 1 and unique_commands[0] == 'NEW':
                logger.info("✓ Command field correctly set to 'NEW'")
            else:
                logger.warning(f"Unexpected Command values: {unique_commands}")
        
        if 'Line: Type' in sample_df.columns:
            unique_types = sample_df['Line: Type'].unique()
            if len(unique_types) == 1 and unique_types[0] == 'Line Item':
                logger.info("✓ Line: Type field correctly set to 'Line Item'")
            else:
                logger.warning(f"Unexpected Line: Type values: {unique_types}")
        
        logger.info("Validation completed")
        
    except Exception as e:
        logger.warning(f"Could not validate output file: {e}")


def main():
    """Main function to orchestrate the conversion process."""
    start_time = time.time()
    
    logger.info("="*60)
    logger.info("Starting Orders to Matrixify CSV Conversion")
    logger.info("="*60)
    
    try:
        # Load processed orders
        orders_df = load_processed_orders()
        
        # Convert to Matrixify format
        matrixify_df = convert_to_matrixify_format(orders_df)
        
        # Save to CSV
        output_path = save_matrixify_csv(matrixify_df)
        
        # Validate output
        validate_output(output_path)
        
        # Final summary
        total_time = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Conversion completed successfully!")
        logger.info(f"Input records: {len(orders_df):,}")
        logger.info(f"Output records: {len(matrixify_df):,}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
