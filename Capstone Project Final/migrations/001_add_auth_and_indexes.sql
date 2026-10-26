-- Migration 001: Add Authentication Columns and Foreign Key Indexes
-- Add password_hash and role to Customers table
ALTER TABLE Customers ADD COLUMN password_hash TEXT;
ALTER TABLE Customers ADD COLUMN role TEXT DEFAULT 'customer';

-- Add indexes on foreign key columns for fast JOINs and cascade checks
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON Orders(Customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON Order_Items(Order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON Order_Items(Product_id);
