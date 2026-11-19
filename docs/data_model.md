# Data model and data dictionary

Star schema at **store × week × category** grain (75 stores × 13 weeks × 8 categories = 7,800 fact rows).

| Table | Type | Key columns | Notes |
| --- | --- | --- | --- |
| fact_sales | Fact | WeekKey, StoreKey, CategoryKey | Target, Sales, Stock (units), IsBulk |
| dim_store | Dimension | StoreKey | Store, Retailer, Channel (Store / Online / Hub / Unmanaged), Mall, City, Emirate, Cluster |
| dim_category | Dimension | CategoryKey | Category, Level (Segment / Sub-segment / Accessory), Parent, InTotalPC, SortOrder |
| dim_week | Dimension | WeekKey | WeekLabel, Month, MonthNum, Quarter, WeekSeq (1–13), IsBulkWeek |
| store_cluster | Python output | StoreKey (1:1) | ClusterName + clustering features |
| fact_stock_risk | Python output | StoreKey, CategoryKey | Stock, WOS, risk points, RiskScore, RiskLevel, StockNeeded |
| fact_forecast | Python output | — | Weekly forecast with low / high band (not related) |

All dimension → fact relationships are one-to-many with single-direction filtering.

## Key definitions

- **Sell-out**: units sold by the retailer to end customers
- **Total PC** = Notebooks + DT (desktops). Convertibles, Gaming, Commercial and Pure Premium are inside Notebooks
- **WOS (weeks of stock)** = closing stock ÷ average weekly sales
- **Sell-through %** = sales ÷ (sales + closing stock)
- **Attach rate** = accessory units ÷ PC units
- **Stock** is semi-additive: it is never summed across weeks; the last week of the selection is used

## Data issues handled in Python

Wide layout (categories side by side), weeks stacked vertically, retailer subtotal rows mixed with stores, merged cells, blank vs zero targets, empty weeks, and a one-off bulk deal in week 10 (flagged with `IsBulk`).
