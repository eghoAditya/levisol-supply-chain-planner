"""
Loads and cleans the Levisol case study data file into tidy pandas DataFrames.

Source: data/raw_case_data.xlsx (11 sheets, matches Exhibits A-J in the
problem statement). All downstream modules (inventory_norms, optimizer, app)
should import from here rather than touching the raw workbook directly.
"""
import re
from pathlib import Path

import openpyxl
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_case_data.xlsx"

MONTH_COLS = ["Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25"]


def _sheet_rows(wb, sheet_name, header_row_idx):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[header_row_idx]
    data = [r for r in rows[header_row_idx + 1:] if any(c is not None for c in r)]
    ncols = len(header)
    data = [r[:ncols] for r in data]
    return list(header), data


def parse_unit_volume_litres(pack_size: str) -> float:
    """Extract the *unit container* volume in litres from a pack size string.

    e.g. '20 X 900 ML' -> 0.9 ; '4 X 5 LT' -> 5.0 ; '1 X 180 KG' -> 195.0 (treated
    as a bulk/barrel-equivalent pack, same production line as 180-210 LT drums).
    """
    s = pack_size.upper().replace(" ", "")
    m = re.search(r"X(\d+\.?\d*)(ML|LT|KG)", s)
    if not m:
        raise ValueError(f"Could not parse pack size: {pack_size}")
    qty, unit = float(m.group(1)), m.group(2)
    if unit == "ML":
        return qty / 1000.0
    if unit == "KG":
        # Bulk grease pack, treated as barrel-line equivalent volume.
        return 195.0
    return qty


def classify_line_type(unit_litres: float) -> str:
    if unit_litres <= 1.5:
        return "<=1.5 LT"
    if unit_litres <= 5:
        return "3-5 LT"
    if unit_litres <= 20:
        return "7-20 LT"
    if unit_litres <= 50:
        return "50 LT"
    return "180-210 LT"


def load_all(path: Path = DATA_PATH) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)

    # --- Exhibit A: Plants & production capacity/cost ---
    _, rows = _sheet_rows(wb, "A - Plants & Production", 2)
    rows = [r for r in rows if r[1] is not None]  # drop trailing footnote row
    plants = pd.DataFrame(rows, columns=[
        "plant_code", "location", "region",
        "cap_1_5lt", "cap_3_5lt", "cap_7_20lt", "cap_50lt", "cap_180_210lt",
        "prod_cost_per_kl",
    ])
    plants = plants.set_index("plant_code")

    # --- Exhibit B: Plant -> Hub transport cost ---
    _, rows = _sheet_rows(wb, "B - Plant-Hub Transport", 2)
    rows = [r[:3] for r in rows if r[1] is not None]  # drop trailing footnote row
    plant_hub_cost = pd.DataFrame(rows, columns=["plant_location", "to_MHW", "to_MHE"])
    loc_to_code = {"Mumbai": "BOM", "Ahmedabad": "AHM", "Kolkata": "KOL"}
    plant_hub_cost["plant_code"] = plant_hub_cost["plant_location"].map(loc_to_code)
    plant_hub_cost = plant_hub_cost.set_index("plant_code")[["to_MHW", "to_MHE"]]

    # --- Exhibit C: Hub -> CFA transport cost ---
    _, rows = _sheet_rows(wb, "C -Hub-CFA Transport", 2)
    rows = [r for r in rows if r[1] is not None]  # drop trailing footnote row
    hub_cfa_cost = pd.DataFrame(rows, columns=["cfa", "region", "from_MHW", "from_MHE"])
    hub_cfa_cost["cfa"] = hub_cfa_cost["cfa"].str.strip()

    # --- Exhibit D: SKU portfolio, penalty cost, contractual flag ---
    _, rows = _sheet_rows(wb, "D -SKU Portfolio+Penalty matrix", 2)
    skus = pd.DataFrame(rows, columns=["sku", "pack_size", "penalty_per_kl", "contractual"])
    skus["contractual"] = skus["contractual"].astype(str).str.contains("YES")
    skus["unit_litres"] = skus["pack_size"].apply(parse_unit_volume_litres)
    skus["line_type"] = skus["unit_litres"].apply(classify_line_type)
    skus = skus.set_index("sku")

    # --- Exhibit E: Historical sourcing + lead-time matrix ---
    _, rows = _sheet_rows(wb, "E - Source + LT data", 2)
    source_lt = pd.DataFrame(rows, columns=[
        "sku", "pack_size", "cfa_region", "cfa", "source",
        "lt_plant_to_hub", "lt_hub_to_cfa", "prod_lt", "prod_lt_var", "transit_lt_var",
    ])
    source_lt["cfa"] = source_lt["cfa"].str.replace(" CFA", "", regex=False).str.strip()
    source_lt["hub"] = source_lt["source"].map({"East": "MHE", "Rest of India": "MHW"})

    # --- Exhibit F: Service level targets by tier ---
    _, rows = _sheet_rows(wb, "F - Service Levels", 2)
    rows = [r[:4] for r in rows if r[0] in ("A", "B", "C", "D")]
    service_levels = pd.DataFrame(rows, columns=[
        "tier", "description", "volume_contribution", "target_fill_rate",
    ])
    service_levels["target_fill_rate"] = (
        service_levels["target_fill_rate"].astype(str).str.rstrip("%").astype(float) / 100
    )
    service_levels = service_levels.set_index("tier")

    def _long_months(sheet, header_idx, value_name):
        _, rows = _sheet_rows(wb, sheet, header_idx)
        cols = ["sku", "pack_size", "cfa_region", "cfa"] + MONTH_COLS
        rows = [r[:len(cols)] for r in rows]
        df = pd.DataFrame(rows, columns=cols)
        df["cfa"] = df["cfa"].str.replace(" CFA", "", regex=False).str.strip()
        long = df.melt(
            id_vars=["sku", "pack_size", "cfa_region", "cfa"],
            value_vars=MONTH_COLS, var_name="month", value_name=value_name,
        )
        return long

    sales = _long_months("G - Sales History", 2, "sales_kl")
    forecast = _long_months("H - Forecast History", 3, "forecast_kl")

    # --- Exhibit I (data file): Opening inventory Jan-26 (CFA + Hub rows) ---
    _, rows = _sheet_rows(wb, "I - Expected opening Inventory", 3)
    opening_inv = pd.DataFrame(rows, columns=["sku", "pack_size", "cfa_region", "location", "opening_inv_kl"])
    opening_inv["location"] = opening_inv["location"].str.replace(" CFA", "", regex=False).str.strip()

    # --- Exhibit J: January 2026 forecast (what we plan against) ---
    _, rows = _sheet_rows(wb, "J - Jan Forecast", 3)
    jan_forecast = pd.DataFrame(rows, columns=["sku", "pack_size", "cfa_region", "cfa", "jan26_forecast_kl"])
    jan_forecast["cfa"] = jan_forecast["cfa"].str.replace(" CFA", "", regex=False).str.strip()

    return dict(
        plants=plants,
        plant_hub_cost=plant_hub_cost,
        hub_cfa_cost=hub_cfa_cost,
        skus=skus,
        source_lt=source_lt,
        service_levels=service_levels,
        sales=sales,
        forecast=forecast,
        opening_inv=opening_inv,
        jan_forecast=jan_forecast,
    )


def assign_sku_tiers(sales: pd.DataFrame, service_levels: pd.DataFrame) -> pd.Series:
    """Classify each SKU into tier A/B/C/D by cumulative share of total 6-month
    sales volume, matching the volume slabs in Exhibit F (A=top 50%, B=next 30%,
    C=next 15%, D=remaining 5%)."""
    total_by_sku = sales.groupby("sku")["sales_kl"].sum().sort_values(ascending=False)
    total_volume = total_by_sku.sum()
    cum_share = total_by_sku.cumsum() / total_volume

    slabs = service_levels["volume_contribution"].to_dict()  # {'A':0.5,'B':0.3,'C':0.15,'D':0.05}
    cum_bounds = {}
    running = 0.0
    for tier in ["A", "B", "C", "D"]:
        running += slabs[tier]
        cum_bounds[tier] = running

    def tier_for(cum_val):
        for tier in ["A", "B", "C", "D"]:
            if cum_val <= cum_bounds[tier] + 1e-9:
                return tier
        return "D"

    tiers = cum_share.apply(tier_for)
    tiers.name = "tier"
    return tiers


if __name__ == "__main__":
    d = load_all()
    tiers = assign_sku_tiers(d["sales"], d["service_levels"])
    print(tiers.value_counts())
    print(d["skus"]["line_type"].value_counts())
    for k, v in d.items():
        print(k, v.shape if hasattr(v, "shape") else type(v))
