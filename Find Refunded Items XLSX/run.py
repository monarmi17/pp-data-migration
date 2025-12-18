import pandas as pd
import os

# --- CONFIG ---
input_file = input("Enter Excel filename (e.g., orders.xlsx): ").strip()
base, ext = os.path.splitext(input_file)
output_all = f"{base}_negative_all{ext}"
output_only_neg = f"{base}_negative_only{ext}"

# --- STEP 1: Read preview to locate the header row ---
preview = pd.read_excel(input_file, header=None, dtype=object)

header_row_index = None
for i, row in preview.iterrows():
    if row.astype(str).str.lower().str.strip().eq("product quantity").any():
        header_row_index = i
        break

if header_row_index is None:
    raise ValueError("❌ Could not find a row containing 'Product quantity'.")

print(f"✅ Detected header row at Excel row {header_row_index + 1}")

# --- STEP 2: Extract header and pre-header info ---
pre_header = preview.iloc[:header_row_index, :]
original_header = preview.iloc[header_row_index].astype(object).tolist()
max_cols = preview.shape[1]

# --- STEP 3: Load data normally using header row ---
df = pd.read_excel(input_file, header=header_row_index, dtype=object)
df.columns = df.columns.astype(str)
normalized_cols = [c.strip().lower() for c in df.columns]
df.columns = normalized_cols

# --- STEP 4: Define key columns ---
quantity_column = "product quantity"
order_id_column = "ticket number"

if quantity_column not in df.columns:
    raise ValueError(f"❌ Column '{quantity_column}' not found in header row.")
if order_id_column not in df.columns:
    raise ValueError(f"❌ Column '{order_id_column}' not found in header row.")

# --- STEP 5: Convert quantity column ---
df[quantity_column] = pd.to_numeric(df[quantity_column], errors="coerce")

# --- STEP 6: Identify negative orders and rows ---
df_negative_only = df[df[quantity_column] < 0]
negative_order_ids = df_negative_only[order_id_column].dropna().unique()
df_negative_orders_all = df[df[order_id_column].isin(negative_order_ids)]

print(f"📊 Found {len(negative_order_ids)} orders containing negative line items.")

# --- STEP 7: Prepare column mapping ---
orig_header_norm = [str(x).strip().lower() for x in original_header]
col_to_index = {name: idx for idx, name in enumerate(orig_header_norm) if name}

def build_output(pre_header, data_rows, filename, label):
    """Rebuild Excel layout identical to the original file"""
    output_rows = []

    # Add pre-header rows
    for r in range(0, header_row_index):
        row_values = preview.iloc[r].astype(object).tolist()
        if len(row_values) < max_cols:
            row_values += [""] * (max_cols - len(row_values))
        output_rows.append(row_values)

    # Add header row
    header_row_values = original_header.copy()
    if len(header_row_values) < max_cols:
        header_row_values += [""] * (max_cols - len(header_row_values))
    output_rows.append(header_row_values)

    # Add filtered data rows
    for _, row in data_rows.iterrows():
        out_row = [""] * max_cols
        for col_name, value in row.items():
            if col_name in col_to_index:
                out_row[col_to_index[col_name]] = value
        output_rows.append(out_row)

    # Export file
    output_df = pd.DataFrame(output_rows)
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        output_df.to_excel(writer, index=False, header=False)

    print(f"✅ Exported {len(data_rows)} {label} → {filename}")

# --- STEP 8: Export both variants ---
build_output(pre_header, df_negative_orders_all, output_all, "line items (all for negative orders)")
build_output(pre_header, df_negative_only, output_only_neg, "negative-only line items")

print("\n🎉 Done! Created:")
print(f"   → All items for negative orders: {output_all}")
print(f"   → Negative-only line items:      {output_only_neg}")
