# Step 3 - Build the store lookup table (Dim_Store)
# One row per store with Retailer, Mall, City, Emirate and Channel.
import pandas as pd

BASE = "data"   # folder holding the source file and the CSVs this pipeline creates (not in this repo)
FACT = BASE + "/fact_weekly_sales.csv"     # made in Step 2
OUT  = BASE + "/dim_store.csv"

# ---------- 1. The list of stores comes from the fact table ----------
stores = pd.read_csv(FACT)["Store"].drop_duplicates().sort_values().reset_index(drop=True)

# ---------- 2. Retailer: decided by the first word of the store name ----------
# Store names start with a retailer code. Retailer names are anonymised in this public
# version: map each real store-name prefix to its retailer here.
RETAILER_PREFIX = {
    "RA": "Retailer A", "RB": "Retailer B", "RC": "Retailer C", "RD": "Retailer D",
    "RE": "Retailer E", "RF": "Retailer F", "RG": "Retailer G",
    "MP1": "Marketplace 1", "MP2": "Marketplace 2",
}

def get_retailer(store):
    return RETAILER_PREFIX.get(store.split()[0], "Unknown")

# ---------- 3. Channel: Online, Hub, Unmanaged or Store ----------
def get_channel(store):
    if "Online" in store or store in ("MP1", "MP2"):   # online marketplaces
        return "Online"
    if "Hub" in store or "HUB" in store:
        return "Hub"
    if "Unmanaged" in store:
        return "Unmanaged"
    return "Store"

# ---------- 4. Mall: the code after the retailer name ----------
# code -> (Mall, City, Emirate, Confirmed?)
MALLS = {
    "MOE":        ("Mall of the Emirates", "Dubai", "Dubai", True),
    "DCC":        ("Deira City Centre", "Dubai", "Dubai", True),
    "MCC":        ("Mirdif City Centre", "Dubai", "Dubai", True),
    "DM":         ("The Dubai Mall", "Dubai", "Dubai", True),
    "Dubai Mall": ("The Dubai Mall", "Dubai", "Dubai", True),
    "IBN":        ("Ibn Battuta Mall", "Dubai", "Dubai", True),
    "DFC":        ("Dubai Festival City", "Dubai", "Dubai", True),
    "BJM":        ("BurJuman", "Dubai", "Dubai", True),
    "Burjuman":   ("BurJuman", "Dubai", "Dubai", True),
    "Oasis":      ("Oasis Centre", "Dubai", "Dubai", True),
    "DSO":        ("Dubai Silicon Oasis", "Dubai", "Dubai", True),
    "Shindagha":  ("Al Shindagha", "Dubai", "Dubai", True),
    "Qusais":     ("Al Qusais", "Dubai", "Dubai", True),
    "Barsha":     ("Al Barsha", "Dubai", "Dubai", True),
    "TSC":        ("TSC (to confirm)", "Dubai", "Dubai", False),
    "SCC":        ("City Centre Sharjah", "Sharjah", "Sharjah", True),
    "Sharjah":    ("City Centre Sharjah", "Sharjah", "Sharjah", True),
    "ZAH":        ("City Centre Al Zahia", "Sharjah", "Sharjah", True),
    "Zahia":      ("City Centre Al Zahia", "Sharjah", "Sharjah", True),
    "Ajman":      ("City Centre Ajman", "Ajman", "Ajman", True),
    "Fujairah":   ("City Centre Fujairah", "Fujairah", "Fujairah", True),
    "RAK":        ("Ras Al Khaimah", "Ras Al Khaimah", "Ras Al Khaimah", True),
    "Saqr":       ("Saqr (to confirm)", "Ras Al Khaimah", "Ras Al Khaimah", False),
    "Delma":      ("Dalma Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Delma Mall": ("Dalma Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Dalma":      ("Dalma Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Wahda":      ("Al Wahda Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Al Wahda":   ("Al Wahda Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Yas":        ("Yas Mall", "Abu Dhabi", "Abu Dhabi", True),
    "MM":         ("Marina Mall (to confirm)", "Abu Dhabi", "Abu Dhabi", False),
    "Khalidiya":  ("Khalidiyah Mall", "Abu Dhabi", "Abu Dhabi", True),
    "Mushriff":   ("Mushrif Mall", "Abu Dhabi", "Abu Dhabi", True),
    "M zayed":    ("Mohamed Bin Zayed City", "Abu Dhabi", "Abu Dhabi", True),
    "Forsan":     ("Forsan Central Mall", "Abu Dhabi", "Abu Dhabi", True),
    "AM":         ("AM (to confirm)", "Abu Dhabi", "Abu Dhabi", False),
    "Al Ain":     ("Al Ain", "Al Ain", "Abu Dhabi", True),
    "AlKuwaitat": ("Al Kuwaitat", "Al Ain", "Abu Dhabi", True),
}

def get_mall(store, channel):
    if channel != "Store":                       # online, hub, unmanaged have no mall
        return (channel, channel, channel, True)
    code = store.split(" ", 1)[1]                # everything after the first word
    return MALLS.get(code, ("Unknown", "Unknown", "Unknown", False))

# ---------- 5. Build the table ----------
dim = pd.DataFrame({"Store": stores})
dim["StoreKey"] = dim.index + 1
dim["Retailer"] = dim["Store"].apply(get_retailer)
dim["Channel"]  = dim["Store"].apply(get_channel)
mall_info = dim.apply(lambda r: get_mall(r["Store"], r["Channel"]), axis=1)
dim[["Mall", "City", "Emirate", "MallConfirmed"]] = pd.DataFrame(mall_info.tolist(), index=dim.index)
dim = dim[["StoreKey", "Store", "Retailer", "Channel", "Mall", "City", "Emirate", "MallConfirmed"]]

# ---------- 6. Checks ----------
print(dim.to_string(index=False))
print("\nStores per channel:\n", dim["Channel"].value_counts())
print("\nPhysical stores per emirate:\n", dim[dim.Channel == "Store"]["Emirate"].value_counts())
print("\nUnknown retailers:", (dim.Retailer == "Unknown").sum(), "| Unknown malls:", (dim.Mall == "Unknown").sum())
print("To confirm:", dim.loc[~dim.MallConfirmed, "Store"].tolist())

dim.to_csv(OUT, index=False)
print("\nSaved", OUT)
