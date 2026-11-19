# Step 4 - Finish the star schema
# Creates dim_category.csv and dim_week.csv, then swaps text names in the fact table for keys.
import pandas as pd

BASE = "data"   # folder holding the source file and the CSVs this pipeline creates (not in this repo)

# ---------- 1. Load what we built in Steps 2 and 3 ----------
fact      = pd.read_csv(BASE + "/fact_weekly_sales.csv")
dim_store = pd.read_csv(BASE + "/dim_store.csv")

# ---------- 2. Dim_Category ----------
# Level tells Power BI how categories relate:
#   Segment     = Notebooks, DT          -> these two add up to Total PC
#   Sub-segment = parts of Notebooks     -> never add them to Notebooks
#   Accessory   = ACC, HyperX            -> separate product lines
dim_category = pd.DataFrame([
    # Category,       Level,          Parent,       InTotalPC
    ("Notebooks",     "Segment",      "Total PC",    True),
    ("DT",            "Segment",      "Total PC",    True),
    ("Convertibles",  "Sub-segment",  "Notebooks",   False),
    ("Gaming",        "Sub-segment",  "Notebooks",   False),
    ("Commercial",    "Sub-segment",  "Notebooks",   False),
    ("Pure Premium",  "Sub-segment",  "Notebooks",   False),
    ("ACC",           "Accessory",    "Accessories", False),
    ("HyperX",        "Accessory",    "Accessories", False),
], columns=["Category", "Level", "Parent", "InTotalPC"])
dim_category.insert(0, "CategoryKey", range(1, len(dim_category) + 1))
dim_category["SortOrder"] = dim_category["CategoryKey"]      # display order in visuals

# ---------- 3. Dim_Week ----------
dim_week = (fact[["WeekSeq", "Month", "Week"]]
            .drop_duplicates()
            .sort_values("WeekSeq")
            .reset_index(drop=True))
dim_week["WeekKey"]    = dim_week["WeekSeq"]                          # 1..13
dim_week["WeekLabel"]  = dim_week["Month"] + " " + dim_week["Week"]   # "M1 W1"
dim_week["MonthNum"]   = dim_week["Month"].str[1].astype(int)         # 1, 2, 3
dim_week["MonthLabel"] = "Q1 " + dim_week["Month"]                    # "Q1 M1"
dim_week["Quarter"]    = "Q1"
dim_week["IsBulkWeek"] = (dim_week["Month"] == "M3") & (dim_week["Week"] == "W1")
dim_week = dim_week[["WeekKey", "WeekLabel", "Week", "Month", "MonthNum",
                     "MonthLabel", "Quarter", "WeekSeq", "IsBulkWeek"]]

# ---------- 4. Fact table with keys ----------
# merge = Excel's VLOOKUP: bring the key from each dimension into the fact table
fact_model = (fact
    .merge(dim_store[["Store", "StoreKey"]], on="Store", how="left")
    .merge(dim_category[["Category", "CategoryKey"]], on="Category", how="left")
    .rename(columns={"WeekSeq": "WeekKey"}))
fact_model = fact_model[["WeekKey", "StoreKey", "CategoryKey",
                         "Target", "Sales", "Stock", "IsBulk"]]

# ---------- 5. Checks ----------
print("Missing keys (must all be 0):")
print(fact_model[["WeekKey", "StoreKey", "CategoryKey"]].isna().sum())
print("\nDuplicate rows (must be 0):",
      fact_model.duplicated(["WeekKey", "StoreKey", "CategoryKey"]).sum())
print("Rows in fact:", len(fact_model), "| same as before:", len(fact_model) == len(fact))
print("Total sales before vs after:", fact["Sales"].sum(), fact_model["Sales"].sum())
print("\n", dim_category.to_string(index=False))
print("\n", dim_week.to_string(index=False))

# ---------- 6. Save ----------
fact_model.to_csv(BASE + "/fact_sales.csv", index=False)
dim_category.to_csv(BASE + "/dim_category.csv", index=False)
dim_week.to_csv(BASE + "/dim_week.csv", index=False)
print("\nSaved fact_sales.csv, dim_category.csv, dim_week.csv")
