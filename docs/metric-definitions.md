# Metric Definitions

All business metrics in the ERP QA System are centrally defined in the Metric Registry and versioned.

## `outstanding:v1`
- **Definition**: The total gross amount of all invoices for a customer minus the total amount of all payments received from that customer. (In the absence of a `credit_notes` table in the baseline schema, this is the functional definition).
- **Required Data**: `parties`, `invoices`, `payments`

## `on_time_delivery:v1`
- **Definition**: The percentage of fulfilled sales orders where the actual delivery date is less than or equal to the revised delivery date (if available) or the promised delivery date.
- **Required Data**: `sales_orders`

## `stock_in_hand:v1`
- **Definition**: The physical inventory quantity available for a material minus the quantity committed to open or partially fulfilled sales orders (committed = ordered quantity - delivered quantity).
- **Required Data**: `inventory`, `sales_orders`, `sales_order_items`
