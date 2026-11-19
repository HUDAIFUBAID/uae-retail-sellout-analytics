# Project steps

1. **Understand the raw data**: grain, subtotals, category hierarchy, outliers, merged cells.
2. **Clean and unpivot** (`python/01_clean_and_unpivot.py`): weekly sheets → one long table; checked against the report's totals.
3. **Store lookup** (`python/02_store_lookup.py`): retailer, channel, mall, emirate from store-name codes.
4. **Star schema** (`python/03_star_schema.py`): category and week dimensions, integer keys.
5. **Power BI model**: relationships, sort-by-column, hidden keys, `_Measures` table.
6. **DAX measures** (`dax/measures.md`): achievement, semi-additive stock, WOS, mix, week-on-week, ranking.
7. **Store clusters** (`python/04_store_clusters.py`): k-means on 54 physical stores (sales, achievement, WOS, growth, premium mix), scaled features, k chosen with elbow + silhouette + business judgement.
8. **Forecast and ageing risk** (`python/05_forecast_and_risk.py`): naive vs 4-week average vs Holt, tested on held-out weeks with MAPE; rule-based stock-ageing score and stock-need calculation.
9. **Dashboard**: two pages (Overview; Clusters & Risk), field-parameter "View by" switch, synced slicers, conditional formatting, custom theme.
