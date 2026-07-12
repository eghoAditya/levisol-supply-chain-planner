"""
Runs Component 1 end-to-end: load data -> derive tiers -> compute CFA and
hub inventory norms -> write outputs/inventory_norms.xlsx.

Usage: python src/build_norms.py
"""
from pathlib import Path

import pandas as pd

from data_loader import load_all, assign_sku_tiers
from inventory_norms import compute_cfa_norms, compute_hub_norms

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def main():
    d = load_all()
    tiers = assign_sku_tiers(d["sales"], d["service_levels"])
    print("Tier distribution:\n", tiers.value_counts())

    cfa_norms = compute_cfa_norms(
        sales=d["sales"], source_lt=d["source_lt"], skus=d["skus"],
        tiers=tiers, service_levels=d["service_levels"], forecast=d["forecast"],
    )
    hub_norms = compute_hub_norms(cfa_norms)

    print(f"\nCFA norms: {len(cfa_norms)} rows")
    print(cfa_norms[["sku", "cfa", "hub", "avg_daily_demand_kl", "reorder_point_kl", "days_of_cover"]].head(10))
    print(f"\nHub norms: {len(hub_norms)} rows")
    print(hub_norms.head(10))

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / "inventory_norms.xlsx"
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        cfa_norms.to_excel(writer, sheet_name="CFA Norms", index=False)
        hub_norms.to_excel(writer, sheet_name="Hub Norms", index=False)
        tiers.reset_index().rename(columns={"index": "sku"}).to_excel(
            writer, sheet_name="SKU Tiers", index=False
        )
    print(f"\nWrote {out_path}")
    return cfa_norms, hub_norms, tiers


if __name__ == "__main__":
    main()
