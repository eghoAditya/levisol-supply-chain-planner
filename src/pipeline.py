"""
Shared pipeline used by both the CLI scripts and the Streamlit app.

Turns raw loaded data + a set of (possibly planner-edited) overrides into:
  - SKU tiers
  - CFA inventory norms
  - Hub inventory norms
  - A solved production/distribution PlanResult

Keeping this logic in one place means the Streamlit app and the batch
scripts (build_norms.py, build_plan.py) can never drift apart.
"""
from dataclasses import dataclass

import pandas as pd

from data_loader import load_all, assign_sku_tiers
from inventory_norms import compute_cfa_norms, compute_hub_norms
from optimizer import solve_plan, PlanResult


@dataclass
class PipelineInputs:
    plants: pd.DataFrame
    plant_hub_cost: pd.DataFrame
    hub_cfa_cost: pd.DataFrame
    skus: pd.DataFrame
    source_lt: pd.DataFrame
    service_levels: pd.DataFrame
    sales: pd.DataFrame
    forecast: pd.DataFrame
    opening_inv: pd.DataFrame
    jan_forecast: pd.DataFrame


def load_inputs() -> PipelineInputs:
    d = load_all()
    return PipelineInputs(**d)


def run_norms(inputs: PipelineInputs):
    tiers = assign_sku_tiers(inputs.sales, inputs.service_levels)
    cfa_norms = compute_cfa_norms(
        sales=inputs.sales, source_lt=inputs.source_lt, skus=inputs.skus,
        tiers=tiers, service_levels=inputs.service_levels, forecast=inputs.forecast,
    )
    hub_norms = compute_hub_norms(cfa_norms)
    return tiers, cfa_norms, hub_norms


def run_plan(inputs: PipelineInputs, hub_norms: pd.DataFrame,
             time_limit_seconds: int = 120) -> PlanResult:
    all_cfas = sorted(inputs.hub_cfa_cost["cfa"].unique())

    opening_inv_cfa = inputs.opening_inv[inputs.opening_inv["location"].isin(all_cfas)].rename(
        columns={"location": "cfa"}
    )[["sku", "cfa", "opening_inv_kl"]]

    opening_inv_hub = inputs.opening_inv[inputs.opening_inv["location"].isin(["Mother Hub West", "Mother Hub East"])].copy()
    opening_inv_hub["hub"] = opening_inv_hub["location"].map(
        {"Mother Hub West": "MHW", "Mother Hub East": "MHE"}
    )
    opening_inv_hub = opening_inv_hub[["sku", "hub", "opening_inv_kl"]]

    empty_map = pd.DataFrame(columns=["sku", "cfa", "hub"])

    return solve_plan(
        plants=inputs.plants,
        plant_hub_cost=inputs.plant_hub_cost,
        hub_cfa_cost=inputs.hub_cfa_cost,
        skus=inputs.skus,
        jan_forecast=inputs.jan_forecast,
        opening_inv_cfa=opening_inv_cfa,
        opening_inv_hub=opening_inv_hub,
        hub_norms=hub_norms,
        cfa_hub_map=empty_map,
        time_limit_seconds=time_limit_seconds,
    )
