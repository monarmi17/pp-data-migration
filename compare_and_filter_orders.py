#!/usr/bin/env python3
"""
compare_and_filter_orders.py

Compares a FranPOS Sales_By_Customer_*.xlsx file against a Shopify orders
export to find every order that differs, then produces a re-import ready
FranPOS file containing only those differing orders plus orders that carry
any of the ~400 No Scan SKUs.

HOW IT WORKS
============
FranPOS is the source of truth.  The Shopify file is what is currently live.
We want to identify every order where Shopify differs from FranPOS so we can
re-import the correct version.

Differences detected (per order):
  - missing_in_shopify     : FranPOS order absent from Shopify
  - lineitem_missing        : FranPOS line item (SKU) not in Shopify order
  - extra_lineitem          : Shopify has a line item the FranPOS order lacks
  - quantity_mismatch       : same SKU, different quantity
  - price_mismatch          : same SKU, different unit price (>$0.01 tolerance)
  - total_mismatch          : order total differs (>$0.01 tolerance)
  - unmapped_barcode        : FranPOS barcode not found in Products.csv

MATCHING
========
  FranPOS  `Ticket number`  ↔  Shopify `Name`
  FranPOS  `Product` (barcode) → Products.csv `Variant Barcode`→`Variant SKU`
                               ↔  Shopify `Lineitem sku`

OUTPUTS
=======
  comparison-reports/{name}_reimport.xlsx        – FranPOS rows to re-import
  datasource/original-data/{name}_reimport.xlsx  – identical copy (same bytes)
  comparison-reports/{name}_reimport_log.json    – per-order issue log

  Example: Sales_By_Customer_Aspen_May.xlsx ->
            Sales_By_Customer_Aspen_May_reimport.xlsx

Usage:
  py compare_and_filter_orders.py \\
      --franpos-file Sales_By_Customer_Aspen_Un.xlsx \\
      --shopify-file shopify-orders/orders_export_Aspen_Shopify_May.csv

  py compare_and_filter_orders.py \\
      --franpos-file  Sales_By_Customer_Aspen_Un.xlsx \\
      --shopify-file  shopify-orders/orders_export_Aspen_Shopify_May.csv \\
      --no-scans-file Shopify_Launch_No_Scans.csv \\
      --products-file datasource/original-data/Products.csv \\
      --output-dir    comparison-reports \\
      --dry-run
"""

import argparse
import json
import logging
import re
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

ORIGINAL_DATA_DIR  = Path("datasource/original-data")
DEFAULT_OUTPUT_DIR = Path("comparison-reports")
DEFAULT_NO_SCANS   = Path("Shopify_Launch_No_Scans.csv")
DEFAULT_PRODUCTS   = Path("datasource/original-data/Products.csv")
FRANPOS_SKIPROWS   = 2
PRICE_TOLERANCE    = 0.01   # exact penny-level unit price comparison
TOTAL_TOLERANCE    = 0.01   # exact penny-level order total comparison

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _norm_id(value) -> str | None:
    """Normalise order/ticket id — strip #, remove .0 decimals."""
    if pd.isna(value):
        return None
    s = str(value).strip().lstrip("#")
    if s.endswith(".0"):
        s = s[:-2]
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return s or None


def _norm_barcode(value) -> str | None:
    """Normalise barcode for lookup — same rules as merge_orders_products_optimized."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    if text.endswith(".0"):
        text = text[:-2]
    try:
        return str(int(float(text))).zfill(12)
    except (ValueError, OverflowError):
        return text


def _barcode_lookup_key(variant_barcode) -> str | None:
    """Lookup key from Variant Barcode; part before '-' when dash present."""
    if pd.isna(variant_barcode):
        return None
    text = str(variant_barcode).strip()
    if not text or text.lower() == "nan":
        return None
    if "-" in text:
        text = text.split("-", 1)[0].strip()
    return _norm_barcode(text)


def _canonical_line_key(sku: str | None, barcode_norm: str | None = None) -> str | None:
    """
    Canonical key for line-item matching across SKU label variants.
    e.g. ANPF44780 and 44780 -> sku:44780; 69963003-X and 69963003 -> sku:69963003
    """
    if sku:
        text = sku.strip()
        if re.search(r"-[A-Za-z0-9]{1,4}$", text):
            base = text.rsplit("-", 1)[0]
            if base:
                text = base
        match = re.search(r"(\d{4,})$", text)
        if match:
            return f"sku:{match.group(1)}"
        return f"sku:{text}"
    if barcode_norm:
        return f"bc:{barcode_norm}"
    return None


def _norm_sku(value) -> str | None:
    """Strip leading apostrophe (Excel text prefix) and whitespace from SKU."""
    if pd.isna(value):
        return None
    s = str(value).strip().lstrip("'")
    return s or None


def _norm_float(value) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Products.csv loader  (barcode → Shopify SKU)
# ---------------------------------------------------------------------------

def load_barcode_to_sku(products_path: Path) -> dict[str, str]:
    """
    Build {barcode_lookup_key: variant_sku} from Products.csv.
    Uses dash-preference logic aligned with merge_orders_products_optimized.py.
    """
    if not products_path.is_file():
        raise FileNotFoundError(f"Products file not found: {products_path}")

    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(
                products_path,
                usecols=["Variant SKU", "Variant Barcode"],
                dtype=str,
                encoding=enc,
            )
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"Cannot decode {products_path}")

    mapping: dict[str, str] = {}
    dash_barcode_flags: dict[str, bool] = {}

    for _, row in df.iterrows():
        lookup_key = _barcode_lookup_key(row["Variant Barcode"])
        sku = _norm_sku(row["Variant SKU"])
        if not lookup_key or not sku:
            continue

        variant_barcode = str(row["Variant Barcode"]).strip()
        has_dash = "-" in variant_barcode

        if lookup_key not in mapping:
            mapping[lookup_key] = sku
            dash_barcode_flags[lookup_key] = has_dash
        elif has_dash and not dash_barcode_flags.get(lookup_key, False):
            mapping[lookup_key] = sku
            dash_barcode_flags[lookup_key] = True

    logger.info("Products map: %s barcode-to-SKU entries", f"{len(mapping):,}")
    return mapping


# ---------------------------------------------------------------------------
# No Scans loader
# ---------------------------------------------------------------------------

def load_no_scan_catalog(no_scans_path: Path) -> tuple[set[str], set[str]]:
    """Return (Variant SKUs, normalised Variant Barcodes) from the No Scans catalog."""
    if not no_scans_path.is_file():
        logger.warning("No Scans file not found, skipping: %s", no_scans_path)
        return set(), set()

    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(
                no_scans_path,
                usecols=["Variant SKU", "Variant Barcode"],
                dtype=str,
                encoding=enc,
            )
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"Cannot decode {no_scans_path}")

    skus = {_norm_sku(v) for v in df["Variant SKU"] if _norm_sku(v)}
    barcodes = {
        b for b in (_barcode_lookup_key(v) for v in df["Variant Barcode"]) if b
    }
    logger.info("No Scan catalog: %s SKUs, %s barcodes", len(skus), len(barcodes))
    return skus, barcodes


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def load_shopify_orders(path: Path) -> dict[str, dict[str, dict]]:
    """
    Load Shopify orders CSV.
    Returns {order_id: {sku: {qty, price}, ..., '__total__': float}}
    """
    if not path.is_file():
        raise FileNotFoundError(f"Shopify orders file not found: {path}")

    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"Cannot decode {path}")

    orders: dict[str, dict] = {}
    # Forward-fill order-level Total (only on first row of each order)
    df["_order_id"] = df["Name"].map(_norm_id)
    if "Total" in df.columns:
        df["_total_filled"] = (
            df[["_order_id", "Total"]]
            .groupby("_order_id", sort=False)["Total"]
            .transform("first")
        )
    else:
        df["_total_filled"] = None

    for _, row in df.iterrows():
        oid = row["_order_id"]
        if not oid:
            continue
        if oid not in orders:
            orders[oid] = {"__total__": _norm_float(row["_total_filled"])}

        sku = _norm_sku(row.get("Lineitem sku"))
        qty = _norm_float(row.get("Lineitem quantity"))
        price = _norm_float(row.get("Lineitem price"))
        line_key = _canonical_line_key(sku)
        if line_key:
            if line_key not in orders[oid]:
                orders[oid][line_key] = {"qty": 0.0, "price": price, "sku": sku}
            orders[oid][line_key]["qty"] = round(
                (orders[oid][line_key].get("qty") or 0) + (qty or 0), 4
            )

    logger.info("Shopify: %s orders", f"{len(orders):,}")
    return orders


def find_no_location_shopify_path(shopify_path: Path) -> Path | None:
    """Resolve companion no-location export next to the location Shopify file."""
    match = re.match(
        r"^orders_export_.+(_Shopify_.+\.csv)$",
        shopify_path.name,
        re.IGNORECASE,
    )
    if not match:
        return None
    parent = shopify_path.parent
    for slug in (NO_LOCATION_SHOPIFY_SLUG, "no-location"):
        candidate = parent / f"orders_export_{slug}{match.group(1)}"
        if candidate.is_file():
            return candidate
    return None


NO_LOCATION_SHOPIFY_SLUG = "no_location"


def load_franpos_orders(
    path: Path,
    barcode_to_sku: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict]]:
    """
    Load FranPOS file.
    Returns:
        header_df   – first 2 metadata rows (for output file reconstruction)
        data_df     – data rows with added `_order_id` and `_sku` columns
        order_map   – {order_id: {sku: {qty, price, rows_idx}, ..., '__total__': float}}
    """
    if not path.is_file():
        raise FileNotFoundError(f"FranPOS file not found: {path}")

    header_df = pd.read_excel(
        path, header=None, nrows=FRANPOS_SKIPROWS, engine="openpyxl"
    )
    data_df = pd.read_excel(
        path, skiprows=FRANPOS_SKIPROWS, engine="openpyxl"
    )

    required = {"Ticket number", "Product"}
    missing = required - set(data_df.columns)
    if missing:
        raise ValueError(f"FranPOS file missing columns: {missing}")

    data_df["_order_id"] = data_df["Ticket number"].map(_norm_id)
    # Drop footer/summary rows that have no ticket number
    data_df = data_df[data_df["_order_id"].notna()].copy()
    data_df["_barcode_norm"] = data_df["Product"].map(_barcode_lookup_key)
    data_df["_sku"] = data_df["_barcode_norm"].map(
        lambda b: barcode_to_sku.get(b) if b else None
    )
    data_df["_line_key"] = data_df.apply(
        lambda r: _canonical_line_key(r["_sku"], r["_barcode_norm"]),
        axis=1,
    )
    data_df["_unmapped"] = data_df["_sku"].isna() & data_df["_barcode_norm"].notna()
    data_df["_qty"] = data_df.get("Product quantity", pd.Series(dtype=float)).map(
        _norm_float
    )
    data_df["_price"] = data_df.get("Price ($)", pd.Series(dtype=float)).map(
        _norm_float
    )
    data_df["_tax"] = data_df.get("Tax ($)", pd.Series(dtype=float)).map(_norm_float)
    data_df["_discount"] = data_df.get("Discount ($)", pd.Series(dtype=float)).map(
        _norm_float
    )

    # Build order map
    order_map: dict[str, dict] = {}
    for idx, row in data_df.iterrows():
        oid = row["_order_id"]
        if not oid:
            continue
        if oid not in order_map:
            order_map[oid] = {"__rows__": []}
        order_map[oid]["__rows__"].append(idx)

        line_key = row["_line_key"]
        sku = row["_sku"]
        if line_key:
            if line_key not in order_map[oid]:
                order_map[oid][line_key] = {
                    "qty": 0.0,
                    "price": row["_price"],
                    "sku": sku,
                    "unmapped": bool(row["_unmapped"]),
                }
            order_map[oid][line_key]["qty"] = round(
                order_map[oid][line_key].get("qty", 0) + (row["_qty"] or 0), 4
            )
            if row["_unmapped"]:
                order_map[oid][line_key]["unmapped"] = True

    # Compute FranPOS order total: sum(qty*price) - discount + tax
    for oid, info in order_map.items():
        rows = data_df.loc[info["__rows__"]]
        qty  = rows["_qty"].fillna(1)
        price = rows["_price"].fillna(0)
        disc  = rows["_discount"].fillna(0)
        tax   = rows["_tax"].fillna(0)
        info["__total__"] = round(
            (qty * price).sum() - disc.sum() + tax.sum(), 2
        )

    logger.info(
        "FranPOS: %s line items across %s orders",
        f"{len(data_df):,}",
        f"{len(order_map):,}",
    )
    return header_df, data_df, order_map


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _compare_single_order(
    oid: str,
    fp: dict,
    sh: dict,
    issues: dict[str, list[dict]],
    diff_order_ids: set[str],
) -> None:
    """Compare one FranPOS order against a Shopify order map entry."""
    fp_keys = {k for k in fp if not k.startswith("__")}
    sh_keys = {k for k in sh if not k.startswith("__")}

    for key in fp_keys:
        if fp[key].get("unmapped"):
            issues[oid].append({
                "issue_type": "unmapped_barcode",
                "line_key": key,
                "sku": fp[key].get("sku"),
                "franpos_qty": fp[key]["qty"],
                "franpos_price": fp[key]["price"],
                "description": (
                    f"FranPOS line {key} has a barcode not found in Products.csv."
                ),
                "resolution": "Verify barcode mapping or add product to Products.csv.",
            })
            diff_order_ids.add(oid)

    for key in fp_keys - sh_keys:
        issues[oid].append({
            "issue_type": "lineitem_missing",
            "line_key": key,
            "sku": fp[key].get("sku"),
            "franpos_qty": fp[key]["qty"],
            "franpos_price": fp[key]["price"],
            "description": (
                f"Line {key} (qty={fp[key]['qty']}) is in FranPOS "
                f"but missing from Shopify order {oid}."
            ),
            "resolution": f"Re-import line item {key} for order {oid}.",
        })
        diff_order_ids.add(oid)

    for key in sh_keys - fp_keys:
        issues[oid].append({
            "issue_type": "extra_lineitem",
            "line_key": key,
            "sku": sh[key].get("sku"),
            "shopify_qty": sh[key]["qty"],
            "shopify_price": sh[key]["price"],
            "description": (
                f"Line {key} is in Shopify order {oid} but not in FranPOS."
            ),
            "resolution": "Verify if this item was added manually in Shopify.",
        })
        diff_order_ids.add(oid)

    for key in fp_keys & sh_keys:
        fp_qty = fp[key]["qty"] or 0
        sh_qty = sh[key]["qty"] or 0
        fp_price = fp[key]["price"]
        sh_price = sh[key]["price"]
        sku = fp[key].get("sku") or sh[key].get("sku")

        if abs(fp_qty - sh_qty) > 0.001:
            issues[oid].append({
                "issue_type": "quantity_mismatch",
                "line_key": key,
                "sku": sku,
                "franpos_qty": fp_qty,
                "shopify_qty": sh_qty,
                "description": (
                    f"Line {key}: FranPOS qty {fp_qty} != Shopify qty {sh_qty}."
                ),
                "resolution": f"Update Shopify order {oid} line {key} qty to {fp_qty}.",
            })
            diff_order_ids.add(oid)

        if fp_price is not None and sh_price is not None:
            if abs(fp_price - sh_price) > PRICE_TOLERANCE:
                issues[oid].append({
                    "issue_type": "price_mismatch",
                    "line_key": key,
                    "sku": sku,
                    "franpos_price": fp_price,
                    "shopify_price": sh_price,
                    "description": (
                        f"Line {key}: FranPOS price ${fp_price} != Shopify ${sh_price}."
                    ),
                    "resolution": f"Review price for line {key} on order {oid}.",
                })
                diff_order_ids.add(oid)

    fp_total = fp.get("__total__")
    sh_total = sh.get("__total__")
    if fp_total is not None and sh_total is not None:
        if abs(fp_total - sh_total) > TOTAL_TOLERANCE:
            issues[oid].append({
                "issue_type": "total_mismatch",
                "franpos_total": fp_total,
                "shopify_total": sh_total,
                "difference": round(fp_total - sh_total, 2),
                "description": (
                    f"Order total: FranPOS ${fp_total} != Shopify ${sh_total}."
                ),
                "resolution": f"Re-import order {oid} to correct the total.",
            })
            diff_order_ids.add(oid)


def find_differences(
    fp_order_map: dict[str, dict],
    sh_order_map: dict[str, dict],
    no_scan_skus: set[str],
    no_scan_barcodes: set[str],
    data_df: pd.DataFrame,
    no_location_sh_map: dict[str, dict] | None = None,
) -> tuple[dict[str, list[dict]], set[str], set[str]]:
    """
    Returns:
        issues         – {order_id: [issue_dict, ...]}
        diff_order_ids – orders with any difference
        ns_order_ids   – orders with at least one No Scan SKU
    """
    issues: dict[str, list[dict]] = defaultdict(list)
    diff_order_ids: set[str] = set()
    ns_order_ids: set[str] = set()

    fp_ids = set(fp_order_map.keys())
    sh_ids = set(sh_order_map.keys())
    no_loc_ids = set(no_location_sh_map.keys()) if no_location_sh_map else set()

    # ── FranPOS orders absent from this location's Shopify export ───────────
    for oid in fp_ids - sh_ids:
        if no_location_sh_map and oid in no_loc_ids:
            issues[oid].append({
                "issue_type": "found_in_no_location",
                "description": (
                    f"Order {oid} is not in this location's Shopify export "
                    f"but exists in the no-location export."
                ),
                "resolution": (
                    "Verify fulfillment location on Shopify; compare details "
                    "below against the no-location export."
                ),
            })
            _compare_single_order(
                oid,
                fp_order_map[oid],
                no_location_sh_map[oid],
                issues,
                diff_order_ids,
            )
        else:
            issues[oid].append({
                "issue_type": "missing_in_shopify",
                "description": (
                    f"Order {oid} exists in FranPOS but is absent from the "
                    f"location Shopify export and the no-location export."
                ),
                "resolution": "Full order needs to be (re-)imported to Shopify.",
            })
            diff_order_ids.add(oid)

    # ── Per-order comparison for orders present in location export ───────────
    for oid in fp_ids & sh_ids:
        _compare_single_order(
            oid,
            fp_order_map[oid],
            sh_order_map[oid],
            issues,
            diff_order_ids,
        )

    # ── No Scan detection (SKU or barcode) across all FranPOS orders ────────
    if no_scan_skus or no_scan_barcodes:
        for _, row in data_df.iterrows():
            oid = row.get("_order_id")
            if not oid:
                continue
            sku = row.get("_sku")
            bc = row.get("_barcode_norm")
            if sku and sku in no_scan_skus:
                ns_order_ids.add(oid)
            elif bc and bc in no_scan_barcodes:
                ns_order_ids.add(oid)

    # ── Safety pass: penny-level total check on orders not yet flagged ──────
    for oid in fp_ids & sh_ids:
        if oid in diff_order_ids:
            continue
        fp_total = fp_order_map[oid].get("__total__")
        sh_total = sh_order_map[oid].get("__total__")
        if fp_total is not None and sh_total is not None:
            if abs(fp_total - sh_total) > TOTAL_TOLERANCE:
                issues[oid].append({
                    "issue_type": "total_mismatch",
                    "franpos_total": fp_total,
                    "shopify_total": sh_total,
                    "difference": round(fp_total - sh_total, 2),
                    "description": (
                        f"Order total: FranPOS ${fp_total} != Shopify ${sh_total}."
                    ),
                    "resolution": f"Re-import order {oid} to correct the total.",
                })
                diff_order_ids.add(oid)

    logger.info(
        "Found %s orders with differences, %s orders with No Scan items",
        f"{len(diff_order_ids):,}",
        f"{len(ns_order_ids):,}",
    )
    return dict(issues), diff_order_ids, ns_order_ids


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def build_reimport_df(
    data_df: pd.DataFrame,
    order_ids: set[str],
) -> pd.DataFrame:
    """Return FranPOS data rows for the given order IDs (original columns only)."""
    private_cols = [c for c in data_df.columns if c.startswith("_")]
    result = data_df[data_df["_order_id"].isin(order_ids)].copy()
    result = result.drop(columns=private_cols)
    return result.reset_index(drop=True)


def reimport_output_filename(franpos_file: str) -> str:
    """e.g. Sales_By_Customer_Aspen_May.xlsx -> Sales_By_Customer_Aspen_May_reimport.xlsx"""
    path = Path(franpos_file)
    return f"{path.stem}_reimport{path.suffix}"


def write_reimport_excel(
    header_df: pd.DataFrame,
    reimport_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write the re-import file preserving the original 2 metadata header rows."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        header_df.to_excel(writer, index=False, header=False, startrow=0)
        reimport_df.to_excel(
            writer, index=False, header=True, startrow=FRANPOS_SKIPROWS
        )
    logger.info("Re-import file saved: %s  (%s rows)", output_path, len(reimport_df))


def save_reimport_excel_copies(
    header_df: pd.DataFrame,
    reimport_df: pd.DataFrame,
    franpos_file: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    """
    Write re-import Excel to comparison-reports and copy byte-identical file
    to datasource/original-data/ (no re-encoding).
    """
    filename = reimport_output_filename(franpos_file)
    reports_path = output_dir / filename
    original_data_path = ORIGINAL_DATA_DIR / filename

    write_reimport_excel(header_df, reimport_df, reports_path)
    original_data_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reports_path, original_data_path)
    logger.info("Re-import file copied: %s", original_data_path)
    return reports_path, original_data_path


def write_json_log(
    issues: dict[str, list[dict]],
    diff_order_ids: set[str],
    ns_order_ids: set[str],
    output_path: Path,
    meta: dict,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_ids = diff_order_ids | ns_order_ids
    records = []
    for oid in sorted(all_ids):
        records.append({
            "order_id": oid,
            "reason_for_reimport": _classify_reasons(oid, issues, ns_order_ids),
            "has_no_scan_items": oid in ns_order_ids,
            "has_differences": oid in diff_order_ids,
            "issue_count": len(issues.get(oid, [])),
            "issues": issues.get(oid, []),
        })

    issue_counts: dict[str, int] = defaultdict(int)
    for issue_list in issues.values():
        for issue in issue_list:
            issue_counts[issue["issue_type"]] += 1

    log = {
        "generated_at": datetime.now().isoformat(),
        "meta": meta,
        "summary": {
            "total_reimport_orders": len(all_ids),
            "orders_with_differences": len(diff_order_ids),
            "orders_with_no_scan_items": len(ns_order_ids),
            "issue_type_counts": dict(issue_counts),
        },
        "orders": records,
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, default=str)
    logger.info("JSON log saved: %s", output_path)


def _classify_reasons(
    oid: str,
    issues: dict[str, list[dict]],
    ns_order_ids: set[str],
) -> list[str]:
    reasons = []
    if oid in ns_order_ids:
        reasons.append("contains_no_scan_sku")
    for issue in issues.get(oid, []):
        r = issue["issue_type"]
        if r not in reasons:
            reasons.append(r)
    return reasons


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare FranPOS orders with Shopify export, find all differences "
            "and No Scan orders, and produce a re-import ready FranPOS file."
        )
    )
    parser.add_argument(
        "--franpos-file",
        required=True,
        help="FranPOS file in datasource/original-data/ "
             "(e.g. Sales_By_Customer_Aspen_Un.xlsx)",
    )
    parser.add_argument(
        "--shopify-file",
        required=True,
        help="Shopify orders export CSV "
             "(e.g. shopify-orders/orders_export_Aspen_Shopify_May.csv)",
    )
    parser.add_argument(
        "--no-scans-file",
        default=str(DEFAULT_NO_SCANS),
        help=f"No Scans catalog CSV (default: {DEFAULT_NO_SCANS})",
    )
    parser.add_argument(
        "--products-file",
        default=str(DEFAULT_PRODUCTS),
        help=f"Products CSV for barcode→SKU mapping (default: {DEFAULT_PRODUCTS})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for output files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run comparison and print summary without writing output files",
    )
    return parser.parse_args()


def setup_logging(log_dir: Path, region: str) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir / f"compare_orders_{region}.log", encoding="utf-8"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    args = parse_arguments()
    start = time.time()

    franpos_path = ORIGINAL_DATA_DIR / args.franpos_file
    shopify_path = Path(args.shopify_file)
    no_scans_path = Path(args.no_scans_file)
    products_path = Path(args.products_file)
    output_dir = Path(args.output_dir)

    m = re.search(r"Sales_By_Customer_(.+)\.xlsx", args.franpos_file, re.IGNORECASE)
    region = m.group(1).replace(" ", "_").lower() if m else "unknown"

    setup_logging(Path("logs"), region)

    logger.info("=" * 60)
    logger.info("FranPOS vs Shopify Comparison")
    logger.info("FranPOS:  %s", franpos_path)
    logger.info("Shopify:  %s", shopify_path)
    logger.info("Products: %s", products_path)
    logger.info("No Scans: %s", no_scans_path)
    logger.info("=" * 60)

    try:
        barcode_to_sku = load_barcode_to_sku(products_path)
        no_scan_skus, no_scan_barcodes = load_no_scan_catalog(no_scans_path)
        sh_order_map   = load_shopify_orders(shopify_path)
        no_location_path = find_no_location_shopify_path(shopify_path)
        no_location_sh_map = None
        if no_location_path:
            no_location_sh_map = load_shopify_orders(no_location_path)
            logger.info(
                "No-location Shopify: %s (%s orders)",
                no_location_path,
                f"{len(no_location_sh_map):,}",
            )
        else:
            logger.warning(
                "No-location Shopify file not found beside %s — "
                "run split_shopify_orders_by_location.py first",
                shopify_path.parent,
            )

        header_df, data_df, fp_order_map = load_franpos_orders(
            franpos_path, barcode_to_sku
        )

        issues, diff_order_ids, ns_order_ids = find_differences(
            fp_order_map,
            sh_order_map,
            no_scan_skus,
            no_scan_barcodes,
            data_df,
            no_location_sh_map,
        )

        all_reimport_ids = diff_order_ids | ns_order_ids

        # Console summary
        logger.info("")
        logger.info("=== SUMMARY ===")
        logger.info("FranPOS orders:                  %s", f"{len(fp_order_map):,}")
        logger.info("Shopify orders:                  %s", f"{len(sh_order_map):,}")
        logger.info("Orders with differences:         %s", f"{len(diff_order_ids):,}")
        logger.info("Orders with No Scan SKUs:        %s", f"{len(ns_order_ids):,}")
        logger.info("Total orders to re-import:       %s", f"{len(all_reimport_ids):,}")

        issue_counts: dict[str, int] = defaultdict(int)
        for issue_list in issues.values():
            for issue in issue_list:
                issue_counts[issue["issue_type"]] += 1
        for itype, count in sorted(issue_counts.items()):
            logger.info("  %-32s %s", itype + ":", f"{count:,}")

        if args.dry_run:
            logger.info("Dry run — no files written.")
            return 0

        if not all_reimport_ids:
            logger.info("No differences or No Scan orders found. Nothing to export.")
            return 0

        reimport_name = reimport_output_filename(args.franpos_file)
        json_path = output_dir / f"{Path(reimport_name).stem}_log.json"

        reimport_df = build_reimport_df(data_df, all_reimport_ids)
        excel_path, original_data_path = save_reimport_excel_copies(
            header_df, reimport_df, args.franpos_file, output_dir
        )

        meta = {
            "franpos_file":   args.franpos_file,
            "shopify_file":   args.shopify_file,
            "no_location_shopify_file": (
                str(no_location_path) if no_location_path else None
            ),
            "products_file":  args.products_file,
            "no_scans_file":  args.no_scans_file,
            "region":         region,
            "reimport_file":  reimport_name,
            "franpos_orders": len(fp_order_map),
            "shopify_orders": len(sh_order_map),
            "elapsed_seconds": round(time.time() - start, 2),
        }
        write_json_log(issues, diff_order_ids, ns_order_ids, json_path, meta)

        logger.info("")
        logger.info("Re-import file: %s", excel_path)
        logger.info("Re-import copy: %s", original_data_path)
        logger.info("JSON log:       %s", json_path)
        logger.info("Completed in %.1f seconds", time.time() - start)
        return 0

    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
