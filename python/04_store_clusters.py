# Step 7 - Cluster analysis: group physical stores that behave alike
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

BASE = "data"   # folder holding the source file and the CSVs this pipeline creates (not in this repo)
fact  = pd.read_csv(BASE + "/fact_sales.csv")
store = pd.read_csv(BASE + "/dim_store.csv")
cat   = pd.read_csv(BASE + "/dim_category.csv")
week  = pd.read_csv(BASE + "/dim_week.csv")

df = (fact.merge(store, on="StoreKey").merge(cat, on="CategoryKey")
          .merge(week[["WeekKey", "MonthNum"]], on="WeekKey"))
df = df[df["Channel"] == "Store"]                   # physical stores only (54)

# ---------- 1. Build one row of features per store ----------
pc = df[df["InTotalPC"]]
g = pc.groupby("Store")
feat = pd.DataFrame({
    "PCSales":  g["Sales"].sum(),
    "PCTarget": g["Target"].sum(),
    "Stock":    pc[pc["WeekKey"] == pc["WeekKey"].max()].groupby("Store")["Stock"].sum(),
})
feat["AchPct"] = feat["PCSales"] / feat["PCTarget"].replace(0, np.nan)
feat["WOS"]    = feat["Stock"] / (feat["PCSales"] / 13).replace(0, np.nan)

# Growth: average weekly sales in M3 (without the bulk week) vs M1
nb = pc[~pc["IsBulk"]]
m1 = nb[nb.MonthNum == 1].groupby("Store")["Sales"].sum() / 5    # M1 has 5 weeks
m3 = nb[nb.MonthNum == 3].groupby("Store")["Sales"].sum() / 3    # M3 has 3 weeks without bulk
feat["Growth"] = (m3 / m1.replace(0, np.nan)) - 1

# Mix: share of Notebook sales that are Gaming or Pure Premium
nbk = df[df.Category == "Notebooks"].groupby("Store")["Sales"].sum()
prem = df[df.Category.isin(["Gaming", "Pure Premium"])].groupby("Store")["Sales"].sum()
feat["PremiumShare"] = prem / nbk.replace(0, np.nan)

# Accessory attach rate
acc = df[df.Category == "ACC"].groupby("Store")["Sales"].sum()
feat["AccAttach"] = acc / feat["PCSales"].replace(0, np.nan)

feat = feat.fillna(0)
# AccAttach is NOT used: ACC is only really tracked at two retailers, so it would
# group stores by retailer reporting, not by behaviour.
cols = ["PCSales", "AchPct", "WOS", "Growth", "PremiumShare"]
# Cap extreme values so one odd store can't pull a whole cluster
for c in cols:
    feat[c] = feat[c].clip(upper=feat[c].quantile(0.95))
print(feat[cols].describe().round(2))

# ---------- 2. Scale, then choose k ----------
X = StandardScaler().fit_transform(feat[cols])
print("\n k  inertia  silhouette")
for k in range(2, 8):
    km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(X)
    print(f" {k}  {km.inertia_:7.1f}  {silhouette_score(X, km.labels_):.3f}")

# ---------- 3. Final model ----------
K = 4
km = KMeans(n_clusters=K, n_init=20, random_state=42).fit(X)
feat["Cluster"] = km.labels_
profile = feat.groupby("Cluster")[cols].mean().round(2)
profile["Stores"] = feat.groupby("Cluster").size()
print("\nCluster profiles:\n", profile)
for c in range(K):
    print(f"\nCluster {c}:", ", ".join(feat.index[feat.Cluster == c]))

# ---------- 4. Give each cluster a business name from its profile ----------
# Cluster numbers can change between computers, so we name them by their profile instead.
names = {}
rest = list(profile.index)
fast = profile.loc[rest, "PCSales"].idxmax();      names[fast] = "Fast Movers";            rest.remove(fast)
decl = profile.loc[rest, "Growth"].idxmin();       names[decl] = "Declining & Overstocked"; rest.remove(decl)
prem = profile.loc[rest, "PremiumShare"].idxmax(); names[prem] = "Low-Volume Premium";     rest.remove(prem)
for c in rest:                                      names[c] = "Core Steady"
feat["ClusterName"] = feat["Cluster"].map(names)
print("\n", feat.groupby("ClusterName")[cols].mean().round(2))

# ---------- 5. Save ----------
out = feat.reset_index().merge(store[["Store", "StoreKey"]], on="Store")
out[["StoreKey", "Store", "ClusterName"] + cols].to_csv(BASE + "/store_cluster.csv", index=False)
print("\nSaved store_cluster.csv")
