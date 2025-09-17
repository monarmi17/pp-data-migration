## **Orders Dataset \- Technical Specification**

### **Dataset Structure**

* **Type**: Shopify order line items dataset  
* **Granularity**: Line item level (not order level)  
* **Records**: 21 line items across 16 unique orders  
* **Format**: CSV with 15 columns

### **Key Identifiers**

* **Primary Key**: Combination of `Ticket number` \+ `Product` (SKU)  
* **Order Grouping**: `Ticket number` (unique per order)  
* **Product Linking**: `Product` column contains SKU values that map to `SKU` column in products-context-data.csv

### **Schema**

Full name (str), Address (str), Email (str), Lead source (str),   
Ticket number (int), Location (str), Date (str, DD/MM/YYYY),   
Product name (str), Product (str, SKU), Product quantity (int),   
Price ($) (float), Subtotal ($) (float), Discount ($) (float),   
Tax ($) (float), Net sales ($) (float)

### **Data Characteristics**

* **Orders**: 16 unique ticket numbers (84785001-84785016)  
* **Products**: All 9 SKUs from product catalog represented  
* **Multi-line orders**: 4 orders contain multiple line items  
* **Date range**: March-May 2024  
* **Monetary calculations**: Subtotal \= Price × Quantity, Net sales \= Subtotal \- Discount \+ Tax

### **Analysis Considerations**

* Group by `Ticket number` for order-level analysis  
* Join on `Product` (orders) \= `SKU` (products) for product details  
* Use `Product quantity` for volume analysis  
* `Net sales ($)` represents final revenue per line item

