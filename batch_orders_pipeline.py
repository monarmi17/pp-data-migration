#!/usr/bin/env python3
"""
Batch Orders Pipeline — automate merge + Matrixify for all order files.

For each Sales_By_Customer_*.xlsx file in datasource/original-data/, runs:
  1. merge_orders_products_optimized.py --orders-file <filename>
  2. mapped_orders_to_matrixify.py --region <region_name>

With --filter-no-scans, an extra filter step runs first:
  0. filter_orders_by_no_scans.py --orders-file <filename>
  1. merge_orders_products_optimized.py (reads from filtered-orders-no-scans/)
  2. mapped_orders_to_matrixify.py --region <filtered_region_name>

Files are processed one at a time; each step starts only after the prior one finishes.
Intended for smaller order files — use the individual scripts for large datasets.

Usage:
  py batch_orders_pipeline.py
  py batch_orders_pipeline.py --dry-run
  py batch_orders_pipeline.py --continue-on-error
  py batch_orders_pipeline.py --file Sales_By_Customer_Chestermere_Station.xlsx
  py batch_orders_pipeline.py --filter-no-scans
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ORDERS_FILE_PATTERN = re.compile(r"^Sales_By_Customer_(.+)\.xlsx$", re.IGNORECASE)
FILTERED_SUFFIX = "_no_scans_filtered"
ORIGINAL_DATA_DIR = Path("datasource/original-data")
FILTERED_ORDERS_DIR = Path("filtered-orders-no-scans")
MERGE_SCRIPT = "merge_orders_products_optimized.py"
MATRIXIFY_SCRIPT = "mapped_orders_to_matrixify.py"
FILTER_SCRIPT = "filter_orders_by_no_scans.py"


def extract_region_from_filename(filename: str) -> str:
    """Extract region slug from Sales_By_Customer_<Region>.xlsx."""
    match = ORDERS_FILE_PATTERN.match(filename)
    if not match:
        raise ValueError(f"Not a valid orders file name: {filename}")

    region = match.group(1)
    return region.replace(" ", "_").replace("-", "_").lower()


def filtered_orders_filename(original_filename: str) -> str:
    """Build the filtered output filename for a source orders file."""
    stem = Path(original_filename).stem
    return f"{stem}{FILTERED_SUFFIX}.xlsx"


def discover_order_files(single_file: str | None = None) -> list[Path]:
    """Find order files to process, sorted alphabetically."""
    if not ORIGINAL_DATA_DIR.is_dir():
        raise FileNotFoundError(f"Directory not found: {ORIGINAL_DATA_DIR}")

    if single_file:
        path = ORIGINAL_DATA_DIR / single_file
        if not path.is_file():
            raise FileNotFoundError(f"Orders file not found: {path}")
        if not ORDERS_FILE_PATTERN.match(path.name):
            raise ValueError(
                f"File must match Sales_By_Customer_<name>.xlsx: {single_file}"
            )
        return [path]

    files = sorted(
        path
        for path in ORIGINAL_DATA_DIR.glob("Sales_By_Customer_*.xlsx")
        if path.is_file() and FILTERED_SUFFIX not in path.stem
    )
    return files


def run_step(command: list[str], dry_run: bool) -> int:
    """Run a pipeline step and return the exit code."""
    display = " ".join(command)
    print(f"  $ {display}")

    if dry_run:
        return 0

    result = subprocess.run(command, cwd=Path.cwd())
    return result.returncode


def process_file(
    orders_path: Path,
    python_executable: str,
    dry_run: bool,
    filter_no_scans: bool,
) -> tuple[bool, str | None]:
    """Run pipeline steps for one orders file. Returns (success, error_message)."""
    filename = orders_path.name
    region = extract_region_from_filename(filename)
    file_size_mb = orders_path.stat().st_size / (1024 * 1024)

    print(f"\n{'=' * 60}")
    print(f"Processing: {filename}")
    print(f"Region:     {region}")
    print(f"Size:       {file_size_mb:.1f} MB")
    if filter_no_scans:
        print(f"Mode:       No Scan filter enabled")
    print(f"{'=' * 60}")

    merge_filename = filename
    merge_region = region
    merge_orders_dir = str(ORIGINAL_DATA_DIR)
    step = 1

    if filter_no_scans:
        filter_cmd = [
            python_executable,
            FILTER_SCRIPT,
            "--orders-file",
            filename,
        ]
        print(f"\nStep {step} — Filter orders with No Scan products")
        filter_code = run_step(filter_cmd, dry_run)
        if filter_code != 0:
            return False, f"Filter step failed with exit code {filter_code}"

        merge_filename = filtered_orders_filename(filename)
        merge_region = extract_region_from_filename(merge_filename)
        merge_orders_dir = str(FILTERED_ORDERS_DIR)
        step += 1

    merge_cmd = [
        python_executable,
        MERGE_SCRIPT,
        "--orders-file",
        merge_filename,
        "--orders-dir",
        merge_orders_dir,
    ]
    print(f"\nStep {step} — Merge orders with products")
    print(f"  Source: {merge_orders_dir}/{merge_filename}")
    merge_code = run_step(merge_cmd, dry_run)
    if merge_code != 0:
        return False, f"Merge step failed with exit code {merge_code}"

    step += 1
    matrixify_cmd = [python_executable, MATRIXIFY_SCRIPT, "--region", merge_region]
    print(f"\nStep {step} — Convert to Matrixify format")
    print(f"  Region: {merge_region}")
    matrixify_code = run_step(matrixify_cmd, dry_run)
    if matrixify_code != 0:
        return False, f"Matrixify step failed with exit code {matrixify_code}"

    print(f"\nCompleted: {filename}")
    return True, None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run merge + Matrixify pipeline for each Sales_By_Customer_*.xlsx "
            "file in datasource/original-data/."
        )
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process a single orders file (e.g. Sales_By_Customer_Chestermere_Station.xlsx)",
    )
    parser.add_argument(
        "--filter-no-scans",
        action="store_true",
        help=(
            "Run filter_orders_by_no_scans.py first and merge from "
            "filtered-orders-no-scans/ instead of original-data/"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running them",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with remaining files if one file fails",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    project_root = Path(__file__).resolve().parent

    # Ensure we run from the project root where the other scripts live.
    if Path.cwd().resolve() != project_root:
        print(f"Changing working directory to: {project_root}")
        os.chdir(project_root)

    start_time = time.time()
    python_executable = sys.executable

    print("Batch Orders Pipeline")
    print(f"Python:     {python_executable}")
    print(f"Data dir:   {ORIGINAL_DATA_DIR}")
    if args.filter_no_scans:
        print(f"Filter:     enabled ({FILTERED_ORDERS_DIR})")
    if args.dry_run:
        print("Mode:       DRY RUN (no commands executed)")

    try:
        order_files = discover_order_files(args.file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not order_files:
        print(f"No Sales_By_Customer_*.xlsx files found in {ORIGINAL_DATA_DIR}")
        return 0

    print(f"\nFound {len(order_files)} file(s) to process:")
    for path in order_files:
        region = extract_region_from_filename(path.name)
        if args.filter_no_scans:
            filtered_name = filtered_orders_filename(path.name)
            filtered_region = extract_region_from_filename(filtered_name)
            print(
                f"  - {path.name}  ->  filter  ->  merge/matrixify region: {filtered_region}"
            )
        else:
            print(f"  - {path.name}  ->  region: {region}")

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []

    for orders_path in order_files:
        ok, error = process_file(
            orders_path,
            python_executable,
            args.dry_run,
            args.filter_no_scans,
        )
        if ok:
            succeeded.append(orders_path.name)
        else:
            failed.append((orders_path.name, error or "Unknown error"))
            print(f"\nFAILED: {orders_path.name} — {error}", file=sys.stderr)
            if not args.continue_on_error:
                break

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("Batch summary")
    print(f"{'=' * 60}")
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed:    {len(failed)}")
    print(f"Elapsed:   {elapsed:.1f}s")

    if succeeded:
        print("\nSuccessful:")
        for name in succeeded:
            print(f"  - {name}")

    if failed:
        print("\nFailed:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
