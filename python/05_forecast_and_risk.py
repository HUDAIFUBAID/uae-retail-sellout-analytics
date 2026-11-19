# Step 8 - Predictive analytics: sales forecast, stock needs and ageing risk
import pandas as pd
import numpy as np

BASE = "data"   # folder holding the source file and the CSVs this pipeline creates (not in this repo)
fact  = pd.read_csv(BASE + "/fact_sales.csv")
store = pd.read_csv(BASE + "/dim_store.csv")
cat   = pd.read_csv(BASE + "/dim_category.csv")

pc = fact.merge(cat, on="CategoryKey")
pc = pc[pc["InTotalPC"]]

# =====================================================================
# PART A - Forecast total weekly PC sales for the next 6 weeks
# =====================================================================
weekly = pc.groupby("WeekKey")["Sales"].sum()

# The bulk week (10) is not normal demand: replace it with the average of the other M3 weeks
weekly_clean = weekly.copy()
weekly_clean[10] = weekly[[11, 12, 13]].mean()
print("Weekly Total PC sales (bulk week smoothed):")
print(weekly_clean.round(0).astype(int).to_string())

# --- Three simple methods ---
def naive(history, h):
    return [history.iloc[-1]] * h                       # next = last week

def moving_avg(history, h, n=4):
    return [history.iloc[-n:].mean()] * h               # next = average of last 4 weeks

def holt(history, h, alpha, beta):
    level, trend = history.iloc[0], history.iloc[1] - history.iloc[0]
    for y in history.iloc[1:]:                           # update level and trend week by week
        prev_level = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return [level + (i + 1) * trend for i in range(h)]

def mape(actual, forecast):
    actual, forecast = np.array(actual), np.array(forecast)
    return np.mean(np.abs(actual - forecast) / actual)

# --- Test on the last 3 weeks (the model never sees them) ---
train, test = weekly_clean.iloc[:10], weekly_clean.iloc[10:]

# Find the best alpha/beta for Holt on the training weeks only
best = None
for a in np.arange(0.1, 1.0, 0.1):
    for b in np.arange(0.0, 0.6, 0.1):
        err = mape(train.iloc[4:], [holt(train.iloc[:i], 1, a, b)[0] for i in range(4, 10)])
        if best is None or err < best[0]:
            best = (err, a, b)
_, ALPHA, BETA = best

results = {
    "Naive":            mape(test, naive(train, 3)),
    "4-week average":   mape(test, moving_avg(train, 3)),
    f"Holt (a={ALPHA:.1f}, b={BETA:.1f})": mape(test, holt(train, 3, ALPHA, BETA)),
}
print("\nAccuracy on the last 3 weeks (MAPE, lower is better):")
for k, v in results.items():
    print(f"  {k:<22} {v:.1%}")
best_method = min(results, key=results.get)
print("Best method:", best_method)

# --- Final forecast: refit on all 13 weeks, predict weeks 14-19 ---
H = 6
if best_method == "Naive":
    fc = naive(weekly_clean, H)
elif best_method == "4-week average":
    fc = moving_avg(weekly_clean, H)
else:
    fc = holt(weekly_clean, H, ALPHA, BETA)
err = results[best_method]

forecast = pd.DataFrame({
    "WeekSeq":  range(14, 14 + H),
    "WeekLabel": [f"Q2 W{i}" for i in range(1, H + 1)],
    "Forecast": np.round(fc, 0),
})
forecast["Low"]  = np.round(forecast["Forecast"] * (1 - err), 0)   # simple error band
forecast["High"] = np.round(forecast["Forecast"] * (1 + err), 0)
forecast["Method"] = best_method
print("\nForecast:\n", forecast.to_string(index=False))

# =====================================================================
# PART B - Stock needs and ageing risk per store x category
# =====================================================================
d = fact.merge(cat[["CategoryKey", "Category", "Level"]], on="CategoryKey")
d = d[d["Level"] != "Sub-segment"]                  # Notebooks, DT, ACC, HyperX (no double count)
d_nb = d[~d["IsBulk"]]                              # ignore the bulk week for speed of sale

g = d.groupby(["StoreKey", "CategoryKey"])
risk = pd.DataFrame({
    "Sales":      g["Sales"].sum(),
    "Target":     g["Target"].sum(),
    "Stock":      d[d.WeekKey == 13].groupby(["StoreKey", "CategoryKey"])["Stock"].sum(),
    "First4":     d[d.WeekKey <= 4].groupby(["StoreKey", "CategoryKey"])["Sales"].sum(),
    "Last4":      d[d.WeekKey >= 10].groupby(["StoreKey", "CategoryKey"])["Sales"].sum(),
    "Last2":      d[d.WeekKey >= 12].groupby(["StoreKey", "CategoryKey"])["Sales"].sum(),
    "AvgWeekly":  d_nb.groupby(["StoreKey", "CategoryKey"])["Sales"].sum() / 12,
    "RecentWeekly": d_nb[d_nb.WeekKey >= 11].groupby(["StoreKey", "CategoryKey"])["Sales"].sum() / 3,
}).fillna(0).reset_index()

risk = risk[risk["Stock"] > 0]                      # no stock = nothing to age
risk["WOS"] = risk["Stock"] / risk["AvgWeekly"].replace(0, np.nan)

# Rule-based score (0-6)
risk["Pts_HighCover"]  = np.where((risk["WOS"] > 12) | risk["WOS"].isna(), 2, 0)
risk["Pts_Falling"]    = np.where(risk["Last4"] < risk["First4"], 1, 0)
risk["Pts_MissTarget"] = np.where((risk["Target"] > 0) & (risk["Sales"] / risk["Target"].replace(0, np.nan) < 0.7), 1, 0)
risk["Pts_NoRecent"]   = np.where(risk["Last2"] == 0, 2, 0)
risk["RiskScore"] = risk[["Pts_HighCover", "Pts_Falling", "Pts_MissTarget", "Pts_NoRecent"]].sum(axis=1)
risk["RiskLevel"] = pd.cut(risk["RiskScore"], bins=[-1, 2, 4, 6], labels=["Low", "Medium", "High"])

# Stock needed for 4 weeks of cover at the recent selling speed (negative = excess)
TARGET_WOS = 4
risk["StockNeeded"] = (risk["RecentWeekly"] * TARGET_WOS - risk["Stock"]).round(0)

risk = risk.merge(store[["StoreKey", "Store", "Retailer", "Channel"]], on="StoreKey") \
           .merge(cat[["CategoryKey", "Category"]], on="CategoryKey")
print("\nRisk levels (store x category with stock):")
print(risk["RiskLevel"].value_counts().to_string())
print("\nUnits of stock by risk level:")
print(risk.groupby("RiskLevel", observed=True)["Stock"].sum().to_string())
print("\nTop 10 high-risk positions:")
print(risk.sort_values(["RiskScore", "Stock"], ascending=False)
          [["Store", "Category", "Stock", "AvgWeekly", "WOS", "RiskScore"]].head(10).round(1).to_string(index=False))

# =====================================================================
# Save
# =====================================================================
forecast.to_csv(BASE + "/fact_forecast.csv", index=False)
cols = ["StoreKey", "CategoryKey", "Stock", "AvgWeekly", "RecentWeekly", "WOS",
        "Pts_HighCover", "Pts_Falling", "Pts_MissTarget", "Pts_NoRecent",
        "RiskScore", "RiskLevel", "StockNeeded"]
risk[cols].round(2).to_csv(BASE + "/fact_stock_risk.csv", index=False)
print("\nSaved fact_forecast.csv and fact_stock_risk.csv")
