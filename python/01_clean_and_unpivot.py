# ---------- CELL 1: imports and settings ----------
import pandas as pd
import openpyxl

BASE = "data"   # folder holding the source file and the CSVs this pipeline creates (not in this repo)
FILE = BASE + "/source_report.xlsx"   # the weekly sell-out Excel report (confidential, not included)
OUT  = BASE + "/fact_weekly_sales.csv"                               # where the clean table is saved

# Column numbers (0 = column A) of Target, Sales, Stock for each category in the weekly sheets
CATEGORIES = {
    "Notebooks":    (6, 7, 8),     # G, H, I
    "Convertibles": (9, 10, 11),   # J, K, L
    "Gaming":       (12, 13, 14),  # M, N, O
    "Commercial":   (15, 16, 17),  # P, Q, R
    "Pure Premium": (18, 19, 20),  # S, T, U
    "DT":           (21, 22, 23),  # V, W, X
    "ACC":          (24, 25, 27),  # Y, Z, AB  (AA is Acc att %, we skip it)
    "HyperX":       (28, 29, 30),  # AC, AD, AE
}

# Subtotal rows: we drop them so nothing is counted twice
# Retailer subtotal rows plus the report's grand-total rows.
# Retailer names are anonymised in this public version: put the real subtotal labels here.
SUBTOTALS = {"Retailer A", "Retailer B", "Retailer C", "Retailer D", "Retailer E",
             "Retailer F", "Retailer G", "Total", "B&M", "Online", "Online Ratiio"}

# ---------- CELL 2: read one sheet and fix merged cells ----------
def read_sheet(sheet_name):
    """Read a sheet as a grid. A value merged over several rows is split equally between them."""
    ws = openpyxl.load_workbook(FILE, data_only=True)[sheet_name]
    grid = [[c.value for c in row] for row in ws.iter_rows()]
    for rng in ws.merged_cells.ranges:
        n_rows = rng.max_row - rng.min_row + 1
        if n_rows > 1 and rng.min_col > 1:                 # vertical merge inside the numbers
            value = grid[rng.min_row - 1][rng.min_col - 1]
            if isinstance(value, (int, float)):
                for r in range(rng.min_row, rng.max_row + 1):
                    grid[r - 1][rng.min_col - 1] = value / n_rows
    return pd.DataFrame(grid)

# ---------- CELL 3: unpivot wide -> long ----------
rows = []
for month in ["M1", "M2", "M3"]:
    sheet = read_sheet(f"{month} Weekly View")
    for _, r in sheet.iterrows():
        store = r[0]
        if not isinstance(store, str):
            continue
        store = " ".join(store.split())            # remove extra spaces
        if store in SUBTOTALS or "/" in store:     # skip subtotals and week headers
            continue
        week = r[60]                                # W1..W5 sits in column BI
        for cat, (t, s, k) in CATEGORIES.items():
            rows.append({
                "Month": month, "Week": week, "Store": store, "Category": cat,
                "Target": pd.to_numeric(r[t], errors="coerce"),
                "Sales":  pd.to_numeric(r[s], errors="coerce"),
                "Stock":  pd.to_numeric(r[k], errors="coerce"),
            })

fact = pd.DataFrame(rows)
fact[["Target", "Sales", "Stock"]] = fact[["Target", "Sales", "Stock"]].fillna(0)
print(fact.shape)
fact.head(10)

# ---------- CELL 4: drop empty weeks, add WeekSeq and IsBulk ----------
week_total = fact.groupby(["Month", "Week"])[["Target", "Sales", "Stock"]].sum().sum(axis=1)
empty_weeks = week_total[week_total == 0].index.tolist()
print("Empty weeks dropped:", empty_weeks)
fact = fact.set_index(["Month", "Week"]).drop(index=empty_weeks).reset_index()

order = fact[["Month", "Week"]].drop_duplicates().sort_values(["Month", "Week"]).reset_index(drop=True)
order["WeekSeq"] = order.index + 1                  # 1..13 in time order
fact = fact.merge(order, on=["Month", "Week"])
fact["IsBulk"] = (fact["Month"] == "M3") & (fact["Week"] == "W1")
fact.head()

# ---------- CELL 5: quality checks ----------
pc = fact[fact["Category"].isin(["Notebooks", "DT"])]
check = pc.groupby(["WeekSeq", "Month", "Week"])[["Target", "Sales"]].sum()
print(check)                                        # compare with the Total row in Excel
print("Stores:", fact["Store"].nunique(), "| Weeks:", fact["WeekSeq"].nunique(),
      "| Categories:", fact["Category"].nunique(), "| Rows:", len(fact))
print("Q1 Total PC sales:", pc["Sales"].sum(), "(Excel Q124 View says 19,351)")

# ---------- CELL 6: save ----------
fact.to_csv(OUT, index=False)
print("Saved", OUT)
