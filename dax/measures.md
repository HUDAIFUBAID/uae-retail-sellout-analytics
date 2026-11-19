# DAX measures

All measures live in a dedicated `_Measures` table. Category hierarchy matters: **Total PC = Notebooks + DT**; Convertibles, Gaming, Commercial and Pure Premium are sub-segments *inside* Notebooks, so "Total PC" measures filter on `dim_category[InTotalPC] = TRUE` to avoid double counting.

## Sales and target

```DAX
Sales = SUM ( fact_sales[Sales] )
Target = SUM ( fact_sales[Target] )
Achievement % = DIVIDE ( [Sales], [Target] )

Total PC Sales  = CALCULATE ( [Sales],  dim_category[InTotalPC] = TRUE () )
Total PC Target = CALCULATE ( [Target], dim_category[InTotalPC] = TRUE () )
Total PC Ach %  = DIVIDE ( [Total PC Sales], [Total PC Target] )

Total PC Sales excl Bulk = CALCULATE ( [Total PC Sales], fact_sales[IsBulk] = FALSE () )
```

## Stock (semi-additive: last week of the selection, never summed over time)

```DAX
Closing Stock =
VAR LastWeek = MAX ( dim_week[WeekSeq] )
RETURN
    CALCULATE ( SUM ( fact_sales[Stock] ), dim_week[WeekSeq] = LastWeek )

Total PC Stock = CALCULATE ( [Closing Stock], dim_category[InTotalPC] = TRUE () )
Total PC Avg Weekly Sales = DIVIDE ( [Total PC Sales], DISTINCTCOUNT ( dim_week[WeekKey] ) )
Total PC WOS = DIVIDE ( [Total PC Stock], [Total PC Avg Weekly Sales] )
Total PC Sell-Through % = DIVIDE ( [Total PC Sales], [Total PC Sales] + [Total PC Stock] )
```

## Mix

```DAX
Acc Attach % =
DIVIDE (
    CALCULATE ( [Sales], REMOVEFILTERS ( dim_category ), dim_category[Category] = "ACC" ),
    CALCULATE ( [Total PC Sales], REMOVEFILTERS ( dim_category ) )
)

Online Share % =
DIVIDE (
    CALCULATE ( [Total PC Sales], dim_store[Channel] = "Online" ),
    CALCULATE ( [Total PC Sales], REMOVEFILTERS ( dim_store ) )
)
```

## Time

```DAX
Total PC Sales Prev Week =
VAR Cur = MAX ( dim_week[WeekSeq] )
RETURN
    CALCULATE ( [Total PC Sales], REMOVEFILTERS ( dim_week ), dim_week[WeekSeq] = Cur - 1 )

-- HASONEVALUE blanks the total row, where week-on-week has no meaning
Total PC WoW % =
IF (
    HASONEVALUE ( dim_week[WeekSeq] ),
    DIVIDE ( [Total PC Sales] - [Total PC Sales Prev Week], [Total PC Sales Prev Week] )
)
```

## Ranking

```DAX
Store Rank =
IF (
    HASONEVALUE ( dim_store[Store] ),
    RANKX ( ALLSELECTED ( dim_store[Store] ), [Total PC Sales] )
)
```

## Stock-ageing risk (from the Python risk table)

```DAX
Risk Positions = COUNTROWS ( fact_stock_risk )
High Risk Stock = CALCULATE ( SUM ( fact_stock_risk[Stock] ), fact_stock_risk[RiskLevel] = "High" )
Stock Needed (units) = CALCULATE ( SUM ( fact_stock_risk[StockNeeded] ), fact_stock_risk[StockNeeded] > 0 )
Excess Stock (units) = - CALCULATE ( SUM ( fact_stock_risk[StockNeeded] ), fact_stock_risk[StockNeeded] < 0 )
```

## Conditional colours

```DAX
Ach Color =
VAR a = [Total PC Ach %]
RETURN SWITCH ( TRUE (), ISBLANK ( a ), BLANK (), a >= 1, "#2E7D32", a < 0.8, "#C62828", "#333333" )

Category Ach Color =
VAR a = [Achievement %]
RETURN SWITCH ( TRUE (), ISBLANK ( a ), BLANK (), a >= 1, "#2A9D8F", a < 0.8, "#F26B5B", "#2A9D8F" )
```

## Cluster label (calculated column on dim_store)

```DAX
Cluster = COALESCE ( RELATED ( store_cluster[ClusterName] ), "Not clustered – " & dim_store[Channel] )
```
