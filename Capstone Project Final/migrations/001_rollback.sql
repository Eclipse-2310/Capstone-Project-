-- Rollback Migration 001
DROP INDEX IF EXISTS idx_orders_customer_id;
DROP INDEX IF EXISTS idx_order_items_order_id;
DROP INDEX IF EXISTS idx_order_items_product_id;

-- Drop added columns (supported in modern SQLite 3.35.0+)
ALTER TABLE Customers DROP COLUMN password_hash;
ALTER TABLE Customers DROP COLUMN role;
