## **Orders Dataset - Technical Specification**

### **Dataset Structure**

- **Type**: Shopify order line items dataset
- **Granularity**: Line item level (not order level)
- **Records**: 548,542 line items across 211,017 unique orders
- **Format**: Excel (.xlsx) with 15 columns
- **File**: Sales_By_Customer_Beddington.xlsx
- **Header**: Starts at row 3 (first 2 rows skipped)

### **Key Identifiers**

- **Primary Key**: Combination of `Ticket number` + `Product` (SKU)
- **Order Grouping**: `Ticket number` (unique per order)
- **Product Linking**: `Product` column contains SKU values that map to `SKU` column in products-context-data.csv
- **Customer Identification**: `Full name` + `Email` combination for customer analysis

### **Schema**

| Column           | Type    | Description                   | Completeness | Unique Values  |
| ---------------- | ------- | ----------------------------- | ------------ | -------------- |
| Full name        | str     | Customer full name            | 100.0%       | 11,429         |
| Address          | str     | Customer address              | 0.4%         | 42             |
| Email            | str     | Customer email address        | 55.9%        | 5,604          |
| Lead source      | str     | Customer acquisition source   | 100.0%       | 6              |
| Ticket number    | float64 | Unique order identifier       | 100.0%       | 211,017        |
| Location         | str     | Store location                | 100.0%       | 1 (Beddington) |
| Date             | str     | Transaction date (DD/MM/YYYY) | 100.0%       | 2,490          |
| Product name     | str     | Human-readable product name   | 100.0%       | 12,444         |
| Product          | float64 | Product SKU/UPC code          | 100.0%       | 9,422          |
| Product quantity | float64 | Quantity purchased            | 100.0%       | 205            |
| Price ($)        | float64 | Unit price                    | 100.0%       | 1,069          |
| Subtotal ($)     | float64 | Price × Quantity              | 100.0%       | 3,259          |
| Discount ($)     | float64 | Discount amount               | 100.0%       | 2,165          |
| Tax ($)          | float64 | Tax amount                    | 100.0%       | 1,064          |
| Net sales ($)    | float64 | Final revenue amount          | 100.0%       | 5,133          |

### **Data Characteristics**

- **Orders**: 211,017 unique ticket numbers (40,846,446 - 111,399,857)
- **Products**: 9,422 unique SKUs represented
- **Customers**: 11,429 unique customers (by name), 5,604 unique emails
- **Date range**: January 2018 - December 2025 (7+ years of data)
- **Location**: Single location (Beddington)
- **Lead Sources**: 6 different acquisition channels
- **Monetary calculations**:
  - Subtotal = Price × Quantity
  - Net sales = Subtotal - Discount + Tax
  - Total revenue: $18,302,327.04
  - Average order value: $33.37

### **Data Quality Observations**

- **Missing Data**:

  - Address: 99.6% missing (546,313 null values)
  - Email: 44.1% missing (241,778 null values)
  - Only 2 records have completely null identifiers

- **Data Anomalies**:

  - Negative quantities: -115 to 850 (likely returns/refunds)
  - Negative prices/discounts: Some refund transactions
  - Very large SKU numbers: Up to 13 digits (UPC format)
  - Duplicate records: 1,393 exact duplicates (0.3%)

- **Date Format**: DD/MM/YYYY string format (not ISO standard)

### **Business Insights**

- **Customer Behavior**:

  - Average customer makes ~48 orders (548,542 ÷ 11,429)
  - Email capture rate: 55.9%
  - Address capture rate: 0.4% (very low)

- **Product Performance**:

  - 9,422 unique SKUs across 12,444 product names
  - Average price: $15.80
  - Quantity range: -115 to 850 (includes returns)

- **Revenue Analysis**:
  - Total revenue: $18.3M over 7+ years
  - Average line item value: $33.37
  - Discount rate: 3.4% ($656K discounts on $19.6M subtotal)

### **Analysis Considerations**

- **Order-Level Analysis**: Group by `Ticket number` for complete order view
- **Customer Analysis**: Use `Full name` + `Email` for customer segmentation
- **Product Analysis**: Join on `Product` (orders) = `SKU` (products) for product details
- **Volume Analysis**: Use `Product quantity` (watch for negative values)
- **Revenue Analysis**: `Net sales ($)` represents final revenue per line item
- **Data Cleaning**: Address missing emails and handle negative quantities
- **Date Processing**: Convert DD/MM/YYYY to proper datetime format

### **Recommended Data Processing Steps**

1. **Date Conversion**: Convert `Date` column to datetime format
2. **SKU Formatting**: Convert `Product` column to string to preserve leading zeros
3. **Missing Data**: Decide on strategy for missing emails/addresses
4. **Duplicate Handling**: Remove or flag 1,393 duplicate records
5. **Negative Quantities**: Investigate and categorize refund/return transactions
6. **Data Validation**: Verify monetary calculations match expected formulas

### **File Structure Notes**

- **Format**: Excel (.xlsx) file, not CSV as originally specified
- **Header Row**: Row 3 (skip first 2 rows when reading)
- **File Size**: ~251 MB in memory
- **Encoding**: UTF-8 compatible
