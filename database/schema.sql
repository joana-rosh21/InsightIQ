-- =========================================================
-- InsightIQ — Database Schema
-- Run with:  psql -U postgres -d insightiq -f database/schema.sql
-- =========================================================

-- Clean slate if re-running during development
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- =========================================================
-- customers
-- =========================================================
CREATE TABLE customers (
    customer_id      SERIAL PRIMARY KEY,
    name              VARCHAR(120)  NOT NULL,
    age               SMALLINT      CHECK (age BETWEEN 12 AND 100),
    city              VARCHAR(100)  NOT NULL,
    region            VARCHAR(50)   NOT NULL,
    signup_date       DATE          NOT NULL,
    customer_segment  VARCHAR(30)                -- populated later by ml/segmentation.py (Day 5)
);

-- =========================================================
-- products
-- =========================================================
CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(150)   NOT NULL,
    category      VARCHAR(80)    NOT NULL,
    sub_category  VARCHAR(80)    NOT NULL,
    cost          NUMERIC(10,2)  NOT NULL CHECK (cost >= 0),
    price         NUMERIC(10,2)  NOT NULL CHECK (price >= 0),
    CONSTRAINT price_covers_cost CHECK (price >= cost)
);

-- =========================================================
-- orders
-- =========================================================
CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INTEGER       NOT NULL REFERENCES customers(customer_id),
    product_id      INTEGER       NOT NULL REFERENCES products(product_id),
    order_date      DATE          NOT NULL,
    quantity        INTEGER       NOT NULL CHECK (quantity > 0),
    revenue         NUMERIC(12,2) NOT NULL CHECK (revenue >= 0),
    cost            NUMERIC(12,2) NOT NULL CHECK (cost >= 0),
    discount        NUMERIC(5,2)  NOT NULL DEFAULT 0 CHECK (discount BETWEEN 0 AND 1),
    profit          NUMERIC(12,2) NOT NULL,
    region          VARCHAR(50)   NOT NULL,
    payment_method  VARCHAR(30)   NOT NULL,
    delivery_days   SMALLINT      NOT NULL CHECK (delivery_days >= 0),
    return_status   VARCHAR(20)   NOT NULL DEFAULT 'Not Returned'
                    CHECK (return_status IN ('Not Returned', 'Returned', 'Cancelled'))
);

-- =========================================================
-- Indexes — chosen to match the analytics queries built on
-- Day 3 (date-range filters, per-customer/product lookups,
-- and regional roll-ups are the hottest query patterns)
-- =========================================================
CREATE INDEX idx_orders_order_date   ON orders(order_date);
CREATE INDEX idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX idx_orders_product_id   ON orders(product_id);
CREATE INDEX idx_orders_region       ON orders(region);
CREATE INDEX idx_customers_region    ON customers(region);
CREATE INDEX idx_products_category   ON products(category);

-- =========================================================
-- Quick sanity check after running this file
-- =========================================================
-- \d customers
-- \d products
-- \d orders
