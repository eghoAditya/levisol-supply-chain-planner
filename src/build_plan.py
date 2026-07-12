"""
Runs Component 2 end-to-end: load data -> Component 1 norms -> solve the
production/distribution MILP -> write outputs/production_distribution_plan.xlsx.

Usage: python src/build_plan.py
"""
from pathlib import Path

import pandas as pd

from pipeline import load_inputs, run_norms, run_plan

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def main():
    inputs = load_inputs()
    tiers, cfa_norms, hub_norms = run_norms(inputs)
    print("Hub norms ready:", hub_norms.shape)

    plan = run_plan(inputs, hub_norms, time_limit_seconds=600)
    print("Solver status:", plan.status)
    print("Cost summary:")
    for k, v in plan.cost_summary.items():
        print(f"  {k}: {v:,.2f}")

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / "production_distribution_plan.xlsx"
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        plan.production.to_excel(writer, sheet_name="Production Plan", index=False)
        plan.plant_hub_flow.to_excel(writer, sheet_name="Plant-Hub Routing", index=False)
        plan.hub_cfa_flow.to_excel(writer, sheet_name="Hub-CFA Routing", index=False)
        plan.hub_safety_stock.to_excel(writer, sheet_name="Hub Safety Stock", index=False)
        plan.unmet_demand.to_excel(writer, sheet_name="Unmet Demand", index=False)
        pd.DataFrame([plan.cost_summary]).T.rename(columns={0: "value"}).to_excel(
            writer, sheet_name="Cost Summary"
        )
    print(f"\nWrote {out_path}")
    return plan


if __name__ == "__main__":
    main()
