#!/usr/bin/env python3
"""
Orders and Products Data Merger - Optimized for Large Datasets

This script merges the orders.xlsx and products.xlsx files to add Product Code
information to the orders data. Optimized for handling large datasets (500k+ orders).

Key optimizations:
- Memory-efficient chunked processing
- Progress tracking and logging
- Optimized data types
- Efficient file I/O operations

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import os
import sys
import time
import gc
from pathlib import Path
from datetime import datetime
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_merger.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration for large dataset processing
CHUNK_SIZE = 50000  # Process orders in chunks of 50k rows
PROGRESS_INTERVAL = 10000  # Show progress every 10k rows


def load_products_data():
    """Load and optimize products data for efficient lookups."""
    try:
        products_path = Path("datasource/products.xlsx")
        if not products_path.exists():
            raise FileNotFoundError(f"Products file not found: {products_path}")
        
        logger.info("Loading products data...")
        start_time = time.time()
        
        # Load only required columns to save memory
        products_df = pd.read_excel(
            products_path, 
            usecols=['SKU', 'Product Code'],
            engine='openpyxl'
        )
        
        load_time = time.time() - start_time
        logger.info(f"Loaded products data: {len(products_df):,} records in {load_time:.2f} seconds")
        
        # Check for required columns
        if 'SKU' not in products_df.columns:
            raise ValueError("'SKU' column not found in products data")
        if 'Product Code' not in products_df.columns:
            raise ValueError("'Product Code' column not found in products data")
        
        # Remove any duplicate SKUs and keep first occurrence
        initial_count = len(products_df)
        products_df = products_df.drop_duplicates(subset=['SKU'], keep='first')
        if len(products_df) < initial_count:
            logger.warning(f"Removed {initial_count - len(products_df)} duplicate SKUs from products data")
        
        # Create optimized mapping dictionary
        logger.info("Creating SKU to Product Code mapping...")
        sku_to_product_code = dict(zip(products_df['SKU'], products_df['Product Code']))
        
        # Clean up products DataFrame to free memory
        del products_df
        gc.collect()
        
        logger.info(f"Created SKU mapping with {len(sku_to_product_code):,} entries")
        return sku_to_product_code
    
    except Exception as e:
        logger.error(f"Error loading products data: {e}")
        sys.exit(1)


def get_orders_info():
    """Get basic information about orders file without loading all data."""
    try:
        orders_path = Path("datasource/orders.xlsx")
        if not orders_path.exists():
            raise FileNotFoundError(f"Orders file not found: {orders_path}")
        
        # Read just the first few rows to get column info and estimate size
        sample_df = pd.read_excel(orders_path, nrows=100, engine='openpyxl')
        
        # Get total row count efficiently
        logger.info("Analyzing orders file structure...")
        
        # Check for required columns
        if 'Product' not in sample_df.columns:
            raise ValueError("'Product' column not found in orders data")
        
        return orders_path, sample_df.columns.tolist()
    
    except Exception as e:
        logger.error(f"Error analyzing orders file: {e}")
        sys.exit(1)


def process_orders_chunk(chunk_df, sku_mapping, chunk_num, total_chunks):
    """Process a single chunk of orders data."""
    try:
        # Add Product Code column using vectorized mapping
        chunk_df['Product Code'] = chunk_df['Product'].map(sku_mapping)
        
        # Count successful mappings in this chunk
        mapped_count = chunk_df['Product Code'].notna().sum()
        unmapped_count = len(chunk_df) - mapped_count
        
        if unmapped_count > 0:
            unmapped_skus = chunk_df[chunk_df['Product Code'].isna()]['Product'].unique()
            logger.warning(f"Chunk {chunk_num}/{total_chunks}: {unmapped_count} unmapped SKUs found")
            # Log first few unmapped SKUs for debugging
            if len(unmapped_skus) <= 5:
                logger.warning(f"Unmapped SKUs: {list(unmapped_skus)}")
            else:
                logger.warning(f"First 5 unmapped SKUs: {list(unmapped_skus[:5])}")
        
        logger.info(f"Chunk {chunk_num}/{total_chunks}: Processed {len(chunk_df):,} records, "
                   f"{mapped_count:,} mapped, {unmapped_count:,} unmapped")
        
        return chunk_df, mapped_count, unmapped_count
    
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_num}: {e}")
        raise


def reorder_columns(df):
    """Reorder columns to place Product Code right after Product."""
    columns = list(df.columns)
    if 'Product Code' in columns and 'Product' in columns:
        product_index = columns.index('Product')
        columns.remove('Product Code')
        columns.insert(product_index + 1, 'Product Code')
        return df[columns]
    return df


def merge_data_simple(orders_path, columns, sku_mapping):
    """
    Simple merge for small datasets - loads entire file into memory.
    """
    try:
        logger.info("Loading orders data for simple processing...")
        start_time = time.time()
        
        # Load entire orders file
        orders_df = pd.read_excel(orders_path, engine='openpyxl')
        
        # Add Product Code column using vectorized mapping
        orders_df['Product Code'] = orders_df['Product'].map(sku_mapping)
        
        # Count mappings
        total_mapped = orders_df['Product Code'].notna().sum()
        total_unmapped = len(orders_df) - total_mapped
        
        if total_unmapped > 0:
            unmapped_skus = orders_df[orders_df['Product Code'].isna()]['Product'].unique()
            logger.warning(f"{total_unmapped} unmapped SKUs found")
            if len(unmapped_skus) <= 10:
                logger.warning(f"Unmapped SKUs: {list(unmapped_skus)}")
            else:
                logger.warning(f"First 10 unmapped SKUs: {list(unmapped_skus[:10])}")
        
        # Reorder columns
        orders_df = reorder_columns(orders_df)
        
        # Create processed directory and save
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)
        output_path = processed_dir / "orders.xlsx"
        
        # Save to Excel file
        orders_df.to_excel(output_path, index=False, engine='openpyxl')
        
        processing_time = time.time() - start_time
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Simple processing completed successfully!")
        logger.info(f"Total records processed: {len(orders_df):,}")
        logger.info(f"Successfully mapped: {total_mapped:,} ({total_mapped/len(orders_df)*100:.1f}%)")
        logger.info(f"Unmapped records: {total_unmapped:,} ({total_unmapped/len(orders_df)*100:.1f}%)")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Output file: {output_path}")
        logger.info(f"{'='*60}")
        
        return len(orders_df), total_mapped, total_unmapped
    
    except Exception as e:
        logger.error(f"Error in simple processing: {e}")
        sys.exit(1)


def merge_data_chunked(orders_path, columns, sku_mapping):
    """
    Merge orders and products data using chunked processing for memory efficiency.
    Since pd.read_excel doesn't support chunksize, we'll convert to CSV first and then process in chunks.
    """
    try:
        logger.info(f"Starting chunked processing with chunk size: {CHUNK_SIZE:,}")
        logger.info("Note: Converting Excel to CSV first for chunked processing...")
        
        # Create temporary CSV file for chunked processing
        temp_csv_path = Path("temp_orders.csv")
        
        # Convert Excel to CSV first
        logger.info("Converting Excel file to CSV for chunked processing...")
        conversion_start = time.time()
        
        # Read Excel file and save as CSV
        orders_df_full = pd.read_excel(orders_path, engine='openpyxl')
        orders_df_full.to_csv(temp_csv_path, index=False)
        total_records = len(orders_df_full)
        
        # Clean up the full dataframe to free memory
        del orders_df_full
        gc.collect()
        
        conversion_time = time.time() - conversion_start
        logger.info(f"Conversion completed in {conversion_time:.2f} seconds. Total records: {total_records:,}")
        
        # Initialize counters
        total_processed = 0
        total_mapped = 0
        total_unmapped = 0
        chunk_num = 0
        
        # Create processed directory
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)
        output_path = processed_dir / "orders.xlsx"
        
        # Initialize list to store processed chunks
        processed_chunks = []
        
        start_time = time.time()
        
        # Calculate total chunks
        total_chunks = (total_records + CHUNK_SIZE - 1) // CHUNK_SIZE
        logger.info(f"Will process {total_chunks} chunks of up to {CHUNK_SIZE:,} records each")
        
        # Process CSV file in chunks
        for chunk_df in pd.read_csv(temp_csv_path, chunksize=CHUNK_SIZE):
            chunk_num += 1
            
            # Process the chunk
            processed_chunk, mapped_count, unmapped_count = process_orders_chunk(
                chunk_df, sku_mapping, chunk_num, total_chunks
            )
            
            # Reorder columns
            processed_chunk = reorder_columns(processed_chunk)
            
            # Store processed chunk
            processed_chunks.append(processed_chunk)
            
            # Update counters
            total_processed += len(processed_chunk)
            total_mapped += mapped_count
            total_unmapped += unmapped_count
            
            # Log progress
            elapsed_time = time.time() - start_time
            if total_processed % PROGRESS_INTERVAL == 0 or total_processed < PROGRESS_INTERVAL:
                rate = total_processed / elapsed_time if elapsed_time > 0 else 0
                logger.info(f"Progress: {total_processed:,} records processed "
                           f"({rate:.0f} records/sec)")
            
            # Clean up chunk to free memory
            del chunk_df, processed_chunk
            gc.collect()
        
        # Clean up temporary CSV file
        if temp_csv_path.exists():
            temp_csv_path.unlink()
            logger.info("Cleaned up temporary CSV file")
        
        # Combine all processed chunks and save to Excel
        logger.info("Combining processed chunks and saving to Excel...")
        
        if len(processed_chunks) == 1:
            # Single chunk - save directly
            final_df = processed_chunks[0]
        else:
            # Multiple chunks - combine them
            final_df = pd.concat(processed_chunks, ignore_index=True)
        
        # Save to Excel file with explicit engine specification
        try:
            final_df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"Successfully saved {len(final_df):,} records to Excel file")
        except Exception as excel_error:
            logger.warning(f"Excel save failed with openpyxl: {excel_error}")
            logger.info("Trying alternative save method...")
            # Fallback to xlsxwriter if available
            try:
                final_df.to_excel(output_path, index=False, engine='xlsxwriter')
                logger.info(f"Successfully saved {len(final_df):,} records using xlsxwriter")
            except Exception as fallback_error:
                logger.error(f"All Excel save methods failed: {fallback_error}")
                # Save as CSV as last resort
                csv_path = output_path.with_suffix('.csv')
                final_df.to_csv(csv_path, index=False)
                logger.info(f"Saved as CSV instead: {csv_path}")
                output_path = csv_path
        
        # Clean up
        del processed_chunks, final_df
        gc.collect()
        
        processing_time = time.time() - start_time
        total_time_with_conversion = processing_time + conversion_time
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing completed successfully!")
        logger.info(f"Total records processed: {total_processed:,}")
        logger.info(f"Successfully mapped: {total_mapped:,} ({total_mapped/total_processed*100:.1f}%)")
        logger.info(f"Unmapped records: {total_unmapped:,} ({total_unmapped/total_processed*100:.1f}%)")
        logger.info(f"Processing time (excl. conversion): {processing_time:.2f} seconds")
        logger.info(f"Total time (incl. conversion): {total_time_with_conversion:.2f} seconds")
        logger.info(f"Processing rate: {total_processed/processing_time:.0f} records/second")
        logger.info(f"Output file: {output_path}")
        logger.info(f"{'='*60}")
        
        return total_processed, total_mapped, total_unmapped
    
    except Exception as e:
        logger.error(f"Error in chunked processing: {e}")
        # Clean up temporary file on error
        temp_csv_path = Path("temp_orders.csv")
        if temp_csv_path.exists():
            temp_csv_path.unlink()
        sys.exit(1)


def validate_output(output_path, expected_records):
    """Validate the output file."""
    try:
        logger.info("Validating output file...")
        
        # Quick validation by reading just the first few rows
        sample_df = pd.read_excel(output_path, nrows=10, engine='openpyxl')
        
        logger.info(f"Output file columns: {list(sample_df.columns)}")
        logger.info("Sample of merged data:")
        
        # Show sample with relevant columns
        display_cols = ['Product', 'Product Code']
        if 'Product name' in sample_df.columns:
            display_cols.append('Product name')
        if 'Product quantity' in sample_df.columns:
            display_cols.append('Product quantity')
        
        available_cols = [col for col in display_cols if col in sample_df.columns]
        if available_cols:
            logger.info(f"\n{sample_df[available_cols].head()}")
        
        # Get file size
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Output file size: {file_size_mb:.1f} MB")
        
    except Exception as e:
        logger.warning(f"Could not validate output file: {e}")


def main():
    """Main function to orchestrate the data merging process."""
    start_time = time.time()
    
    logger.info("="*60)
    logger.info("Starting Orders and Products Data Merger (Optimized)")
    logger.info("="*60)
    
    # Load products data and create mapping
    sku_mapping = load_products_data()
    
    # Get orders file information
    orders_path, columns = get_orders_info()
    
    # Check file size to determine processing method
    file_size_mb = orders_path.stat().st_size / (1024 * 1024)
    logger.info(f"Orders file size: {file_size_mb:.1f} MB")
    
    if file_size_mb < 10:  # Small file - use simple approach
        logger.info("Small dataset detected - using simple processing method")
        total_processed, total_mapped, total_unmapped = merge_data_simple(
            orders_path, columns, sku_mapping
        )
    else:  # Large file - use chunked processing
        logger.info("Large dataset detected - using chunked processing method")
        total_processed, total_mapped, total_unmapped = merge_data_chunked(
            orders_path, columns, sku_mapping
        )
    
    # Validate output
    output_path = Path("processed/orders.xlsx")
    if not output_path.exists():
        output_path = Path("processed/orders.csv")
    
    validate_output(output_path, total_processed)
    
    # Final summary
    total_time = time.time() - start_time
    logger.info(f"\nTotal execution time: {total_time:.2f} seconds")
    logger.info("Data merging completed successfully!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
