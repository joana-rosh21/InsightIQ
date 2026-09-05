"""
InsightIQ — Synthetic Dataset Generator
=========================================
Generates customers.csv, products.csv, orders.csv into the data/ folder.

Scope (Day 1, scoped-down plan): 5,000 customers / 300 products / 20,000 orders.
To generate the full-spec volume later, just change N_CUSTOMERS / N_PRODUCTS /
N_ORDERS below — the generation logic itself does not need to change.

Built-in realistic patterns (so later modules have something real to find):
  - Seasonal sales: order volume rises in Oct-Dec (festival / year-end season)
  - Regional differences: baseline order-share differs by region
  - Customer churn: ~18% of customers stop ordering after a random "went quiet" date
  - Product decline: the South region + Electronics category cools off sharply
    in the last 3 months of the date range (this is what Day 6's root-cause
    engine is designed to detect and explain)
  - Return-rate differences: Apparel returns much more than Grocery, etc.
  - Promotional effects: discounts spike in festival months

Run:
    python data_pipeline/generate_data.py
"""

import os
import numpy as np
import pandas as pd
from faker import Faker
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42
N_CUSTOMERS = 5_000
N_PRODUCTS = 300
N_ORDERS = 20_000

DATE_END = date(2026, 8, 31)
DATE_START = DATE_END - timedelta(days=730)          # 24-month history
DECLINE_WINDOW_START = DATE_END - timedelta(days=90)  # last ~3 months
DECLINE_REGION = "South"
DECLINE_CATEGORY = "Electronics"

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

fake = Faker("en_IN")
Faker.seed(SEED)
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
REGIONS = ["North", "South", "East", "West", "Central"]
REGION_WEIGHTS = [0.22, 0.24, 0.19, 0.20, 0.15]  # South starts as the biggest region on purpose

REGION_CITIES = {
    "North": ["Delhi", "Chandigarh", "Lucknow", "Jaipur"],
    "South": ["Chennai", "Bengaluru", "Hyderabad", "Coimbatore"],
    "East":  ["Kolkata", "Bhubaneswar", "Guwahati", "Patna"],
    "West":  ["Mumbai", "Pune", "Ahmedabad", "Surat"],
    "Central": ["Bhopal", "Nagpur", "Raipur", "Indore"],
}

CATEGORIES = {
    "Electronics":     ["Mobiles", "Laptops", "Audio", "Accessories"],
    "Apparel":         ["Men", "Women", "Kids", "Footwear"],
    "Home & Kitchen":  ["Cookware", "Furniture", "Decor", "Appliances"],
    "Beauty":          ["Skincare", "Haircare", "Makeup", "Fragrance"],
    "Sports":          ["Fitness", "Outdoor", "Team Sports", "Cycling"],
    "Books":           ["Fiction", "Non-Fiction", "Academic", "Children"],
    "Grocery":         ["Staples", "Snacks", "Beverages", "Household"],
}

# Category-level margin band (price = cost * (1 + markup)) and base return rate
CATEGORY_PROFILE = {
    "Electronics":    {"markup": (0.20, 0.45), "cost_range": (2000, 60000), "return_rate": 0.09},
    "Apparel":        {"markup": (0.40, 0.90), "cost_range": (300, 3000),   "return_rate": 0.16},
    "Home & Kitchen": {"markup": (0.30, 0.70), "cost_range": (500, 8000),   "return_rate": 0.07},
    "Beauty":         {"markup": (0.50, 1.10), "cost_range": (150, 2500),   "return_rate": 0.05},
    "Sports":         {"markup": (0.25, 0.60), "cost_range": (400, 6000),   "return_rate": 0.06},
    "Books":          {"markup": (0.15, 0.35), "cost_range": (100, 900),    "return_rate": 0.03},
    "Grocery":        {"markup": (0.10, 0.25), "cost_range": (50, 800),     "return_rate": 0.01},
}

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery"]
PAYMENT_WEIGHTS = [0.38, 0.20, 0.18, 0.12, 0.12]


def random_dates(start: date, end: date, n: int, recent_bias: bool = False) -> np.ndarray:
    """Uniform-random dates in [start, end]. If recent_bias, skew slightly toward `end`."""
    span = (end - start).days
    if recent_bias:
        u = rng.beta(2.2, 1.4, size=n)  # skews toward 1 (recent)
    else:
        u = rng.random(n)
    offsets = (u * span).astype(int)
    return np.array([start + timedelta(days=int(o)) for o in offsets])


# ---------------------------------------------------------------------------
# 1. customers.csv
# ---------------------------------------------------------------------------
def generate_customers() -> pd.DataFrame:
    regions = rng.choice(REGIONS, size=N_CUSTOMERS, p=REGION_WEIGHTS)
    cities = [rng.choice(REGION_CITIES[r]) for r in regions]
    signup_dates = random_dates(DATE_START, DATE_END, N_CUSTOMERS, recent_bias=True)

    df = pd.DataFrame({
        "customer_id": np.arange(1, N_CUSTOMERS + 1),
        "name": [fake.name() for _ in range(N_CUSTOMERS)],
        "age": rng.integers(18, 65, size=N_CUSTOMERS),
        "city": cities,
        "region": regions,
        "signup_date": signup_dates,
        "customer_segment": "",  # filled later by ml/segmentation.py (Day 5)
    })

    # Churn cohort: ~18% of customers get a "went quiet" date after which
    # they place no more orders. Stored here only to drive order generation
    # below — not written to the CSV, since customer_segment/labels belong
    # to the ML phase, not the raw dataset.
    n_churned = int(0.18 * N_CUSTOMERS)
    churn_idx = rng.choice(df.index, size=n_churned, replace=False)
    quiet_after = pd.Series(pd.NaT, index=df.index, dtype="object")
    quiet_dates = random_dates(DATE_START + timedelta(days=200), DATE_END - timedelta(days=30), n_churned)
    quiet_after.loc[churn_idx] = quiet_dates
    df["_quiet_after"] = quiet_after  # internal use only, dropped before saving

    return df


# ---------------------------------------------------------------------------
# 2. products.csv
# ---------------------------------------------------------------------------
def generate_products() -> pd.DataFrame:
    rows = []
    pid = 1
    cats = list(CATEGORIES.keys())
    # distribute 300 products roughly evenly across 7 categories
    per_cat = N_PRODUCTS // len(cats)
    remainder = N_PRODUCTS - per_cat * len(cats)

    for i, cat in enumerate(cats):
        count = per_cat + (1 if i < remainder else 0)
        profile = CATEGORY_PROFILE[cat]
        subcats = CATEGORIES[cat]
        for _ in range(count):
            cost = round(rng.uniform(*profile["cost_range"]), 2)
            markup = rng.uniform(*profile["markup"])
            price = round(cost * (1 + markup), 2)
            rows.append({
                "product_id": pid,
                "product_name": f"{fake.word().capitalize()} {cat.split(' ')[0]} {rng.integers(100, 999)}",
                "category": cat,
                "sub_category": rng.choice(subcats),
                "cost": cost,
                "price": price,
            })
            pid += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. orders.csv
# ---------------------------------------------------------------------------
def month_seasonality_weight(d: date) -> float:
    """Festival/year-end season (Oct-Dec) gets a volume boost; Feb is the low point."""
    boosts = {10: 1.35, 11: 1.55, 12: 1.45, 1: 1.10, 2: 0.80, 6: 0.85}
    return boosts.get(d.month, 1.0)


def generate_orders(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    cust_lookup = customers.set_index("customer_id")
    prod_lookup = products.set_index("product_id")

    # Candidate order dates drawn with seasonality by resampling day-by-day weights
    all_days = pd.date_range(DATE_START, DATE_END, freq="D")
    day_weights = np.array([month_seasonality_weight(d.date()) for d in all_days], dtype=float)
    day_weights /= day_weights.sum()

    order_dates = rng.choice(all_days, size=N_ORDERS, p=day_weights)
    order_dates = pd.to_datetime(order_dates).date

    # Product popularity: a Zipf-like skew so a subset of products are bestsellers
    prod_ids = products["product_id"].values
    zipf_weights = 1.0 / np.arange(1, len(prod_ids) + 1)
    rng.shuffle(zipf_weights)
    zipf_weights /= zipf_weights.sum()

    rows = []
    active_customer_ids = customers["customer_id"].values
    quiet_after_map = customers.set_index("customer_id")["_quiet_after"]

    for order_id in range(1, N_ORDERS + 1):
        o_date = order_dates[order_id - 1]

        # pick a customer, re-rolling (up to 5 tries) if they'd already churned by this date
        for _ in range(5):
            cust_id = int(rng.choice(active_customer_ids))
            quiet_after = quiet_after_map.loc[cust_id]
            if quiet_after is pd.NaT or quiet_after is None or o_date <= quiet_after:
                break

        region = cust_lookup.loc[cust_id, "region"]

        # pick a product (Zipf-weighted popularity)
        prod_id = int(rng.choice(prod_ids, p=zipf_weights))
        category = prod_lookup.loc[prod_id, "category"]

        # Deliberate decline: South + Electronics goes quiet in the last ~3 months —
        # this is the pattern Day 6's root-cause engine is built to surface.
        if (region == DECLINE_REGION and category == DECLINE_CATEGORY
                and o_date >= DECLINE_WINDOW_START):
            if rng.random() < 0.7:  # 70% chance: skip this order, re-roll a safer combo
                prod_id = int(rng.choice(prod_ids, p=zipf_weights))
                category = prod_lookup.loc[prod_id, "category"]

        unit_price = float(prod_lookup.loc[prod_id, "price"])
        unit_cost = float(prod_lookup.loc[prod_id, "cost"])
        quantity = int(rng.integers(1, 5))

        # Promotional discount: bigger during festival months
        base_discount = rng.choice([0.0, 0.05, 0.10, 0.15], p=[0.55, 0.20, 0.15, 0.10])
        if o_date.month in (10, 11, 12):
            base_discount = min(base_discount + rng.choice([0.0, 0.05, 0.10]), 0.35)

        revenue = round(unit_price * quantity * (1 - base_discount), 2)
        cost_total = round(unit_cost * quantity, 2)
        profit = round(revenue - cost_total, 2)

        return_rate = CATEGORY_PROFILE[category]["return_rate"]
        return_status = rng.choice(
            ["Not Returned", "Returned", "Cancelled"],
            p=[1 - return_rate - 0.02, return_rate, 0.02]
        )

        delivery_days = int(rng.integers(1, 4)) if region in ("South", "West") else int(rng.integers(2, 8))
        payment_method = rng.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS)

        rows.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "product_id": prod_id,
            "order_date": o_date,
            "quantity": quantity,
            "revenue": revenue,
            "cost": cost_total,
            "discount": base_discount,
            "profit": profit,
            "region": region,
            "payment_method": payment_method,
            "delivery_days": delivery_days,
            "return_status": return_status,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Generating customers...")
    customers = generate_customers()

    print("Generating products...")
    products = generate_products()

    print("Generating orders (this is the slow step)...")
    orders = generate_orders(customers, products)

    # Drop internal-only helper column before saving
    customers_out = customers.drop(columns=["_quiet_after"])

    customers_out.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)
    products.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
    orders.to_csv(os.path.join(OUT_DIR, "orders.csv"), index=False)

    print("\nDone. Row counts:")
    print(f"  customers.csv : {len(customers_out):,}")
    print(f"  products.csv  : {len(products):,}")
    print(f"  orders.csv    : {len(orders):,}")

    print("\nQuick sanity numbers:")
    print(f"  Total revenue      : {orders['revenue'].sum():,.2f}")
    print(f"  Total profit       : {orders['profit'].sum():,.2f}")
    print(f"  Orders per region  :\n{orders['region'].value_counts()}")
    print(f"  Return-rate overall: {(orders['return_status'] != 'Not Returned').mean():.2%}")


if __name__ == "__main__":
    main()
