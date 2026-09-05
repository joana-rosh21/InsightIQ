\# InsightIQ Analytics Engine



The analytics engine contains SQL and Python functions for analyzing sales, customers, products, and operations.



\## db.py

\- Provides the shared PostgreSQL database connection used by the analytics modules.



\## sales.py

\- `total\_revenue(start, end)` — Returns total revenue, optionally filtered by date.

\- `total\_profit(start, end)` — Returns total profit, optionally filtered by date.

\- `profit\_margin(start, end)` — Returns profit as a percentage of revenue.

\- `average\_order\_value(start, end)` — Returns the average revenue per order.

\- `monthly\_revenue()` — Returns revenue, profit, and orders by calendar month.

\- `quarterly\_revenue()` — Returns revenue, profit, and orders by quarter.

\- `revenue\_growth\_mom()` — Returns month-over-month revenue growth.

\- `revenue\_by\_region()` — Returns revenue, profit, and orders by region.

\- `revenue\_by\_product(top\_n)` — Returns the top products by revenue.

\- `discount\_analysis()` — Returns revenue and profit by discount bracket.



\## customers.py

\- `total\_customers()` — Returns the total number of customers.

\- `new\_customers\_by\_month()` — Returns customer signups by month.

\- `returning\_customers()` — Returns the number of customers with more than one order.

\- `retention\_rate()` — Returns the percentage of ordering customers who ordered more than once.

\- `churn\_rate(inactivity\_days)` — Returns the percentage of customers inactive beyond the specified window.

\- `customer\_lifetime\_value()` — Returns revenue, profit, and orders per customer.

\- `average\_purchase\_frequency()` — Returns the mean number of orders per customer.



\## products.py

\- `top\_products(n, by)` — Returns top products by revenue, profit, or orders.

\- `bottom\_products(n)` — Returns lowest-revenue products with at least one order.

\- `most\_profitable\_products(n)` — Returns products with the highest total profit and margin.

\- `low\_margin\_products(n)` — Returns products with the lowest margins among products with at least five orders.

\- `return\_rate\_by\_product(n)` — Returns products with the highest return rates among products with at least five orders.

\- `category\_performance()` — Returns revenue, profit, orders, and return rate by category.



\## operations.py

\- `average\_delivery\_time()` — Returns the average delivery time across orders.

\- `cancellation\_rate()` — Returns the percentage of cancelled orders.

\- `return\_rate()` — Returns the percentage of returned orders.

\- `regional\_operational\_performance()` — Returns delivery, return, and cancellation metrics by region.

\- `delivery\_time\_by\_category()` — Returns average delivery time by product category.

