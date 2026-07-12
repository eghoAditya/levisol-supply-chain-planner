"""
Component 2 — Production & Distribution Plan.

Formulates and solves a Mixed-Integer Linear Program (MILP) that decides,
for the Jan-2026 planning month:

  1. Production qty of each SKU at each plant (integer multiple of 25 kL,
     bounded by that plant's line-type capacity for that SKU's pack size).
  2. Flow of each SKU from each plant to each hub.
  3. Flow of each SKU from each hub to each CFA.
  4. Safety stock retained at each hub (from Component 1's hub norms).
  5. Unmet demand at each CFA (a shortfall/penalty variable, not a hard
     infeasibility) when total capacity < total demand.

Objective
---------
Minimize total OpEx = production cost + plant->hub transport cost
                       + hub->CFA transport cost
                       + penalty cost of unmet demand
                       + penalty cost of hub safety-stock shortfall

Unmet demand is *never* a hard constraint — it is priced via each SKU's
penalty cost (Exhibit D), with an extra multiplier on contractual SKUs so
the optimizer strongly prefers to protect them (reflecting the case's
statement that under-supplying contractual SKUs carries consequences well
beyond the normal lost-margin/penalty figure already in the data).

Constraints
-----------
  - Flow conservation at each hub: inbound (from plants) = outbound (to
    CFAs) + safety stock retained + opening inventory carried in - opening
    inventory used. (Simplified single-period model: hub outbound + safety
    stock <= opening inventory + inbound production this month.)
  - CFA demand balance: opening inventory + inbound from hubs + unmet =
    Jan-2026 forecast demand.
  - Plant capacity: production of SKUs sharing a line type at a plant cannot
    exceed that line's monthly capacity (kL).
  - Batch size: every plant-SKU production quantity is an integer multiple
    of 25 kL.
  - Non-negativity on all flow/production/shortfall variables.

CONTRACTUAL_PENALTY_MULTIPLIER inflates the effective penalty for
contractual SKUs so the solver treats them as near-must-serve without making
them a hard constraint (which would risk infeasibility if total capacity is
insufficient even for contractual SKUs alone).
"""
from dataclasses import dataclass, field

import pandas as pd
import pulp

CONTRACTUAL_PENALTY_MULTIPLIER = 5.0
LINE_TYPE_TO_CAPCOL = {
    "<=1.5 LT": "cap_1_5lt",
    "3-5 LT": "cap_3_5lt",
    "7-20 LT": "cap_7_20lt",
    "50 LT": "cap_50lt",
    "180-210 LT": "cap_180_210lt",
}
BATCH_SIZE = 25


@dataclass
class PlanResult:
    status: str
    production: pd.DataFrame       # sku, plant, qty_kl
    plant_hub_flow: pd.DataFrame   # sku, plant, hub, qty_kl
    hub_cfa_flow: pd.DataFrame     # sku, hub, cfa, qty_kl
    hub_safety_stock: pd.DataFrame  # sku, hub, qty_kl
    unmet_demand: pd.DataFrame     # sku, cfa, qty_kl, cost
    cost_summary: dict = field(default_factory=dict)


def solve_plan(
    plants: pd.DataFrame,
    plant_hub_cost: pd.DataFrame,
    hub_cfa_cost: pd.DataFrame,
    skus: pd.DataFrame,
    jan_forecast: pd.DataFrame,
    opening_inv_cfa: pd.DataFrame,
    opening_inv_hub: pd.DataFrame,
    hub_norms: pd.DataFrame,
    cfa_hub_map: pd.DataFrame,
    time_limit_seconds: int = 120,
) -> PlanResult:
    """
    Parameters
    ----------
    cfa_hub_map: DataFrame with columns [sku, cfa, hub] — which hub(s) can
        legitimately serve which CFA for which SKU (from the case: "CFAs may
        be supplied from either hub — there is no hard regional restriction",
        so in practice this is the full cross product of hubs x cfas, but is
        parameterised here so a planner can restrict it via the tool).
    """
    plant_codes = list(plants.index)
    hub_codes = ["MHW", "MHE"]
    sku_codes = list(skus.index)

    demand = jan_forecast.set_index(["sku", "cfa"])["jan26_forecast_kl"].to_dict()
    cfa_open = opening_inv_cfa.set_index(["sku", "cfa"])["opening_inv_kl"].to_dict()
    hub_open = opening_inv_hub.set_index(["sku", "hub"])["opening_inv_kl"].to_dict()
    cfas = sorted({c for (_, c) in demand.keys()})

    hub_norm_ss = hub_norms.set_index(["sku", "hub"])["safety_stock_kl"].to_dict()

    # Precompute allowed (sku, cfa, hub) routes for O(1) lookup. Empty map =
    # unrestricted (per the case: "no hard regional restriction" on CFA sourcing).
    restrict_routes = not cfa_hub_map.empty
    allowed_routes = set(
        zip(cfa_hub_map["sku"], cfa_hub_map["cfa"], cfa_hub_map["hub"])
    ) if restrict_routes else set()

    def route_allowed(s, c, h):
        return (not restrict_routes) or (s, c, h) in allowed_routes

    prob = pulp.LpProblem("Levisol_Production_Distribution", pulp.LpMinimize)

    # --- Decision variables ---
    # Production batches (integer, x25kL) per plant per SKU.
    batches = pulp.LpVariable.dicts(
        "batches", [(p, s) for p in plant_codes for s in sku_codes],
        lowBound=0, cat="Integer",
    )
    prod_qty = {k: batches[k] * BATCH_SIZE for k in batches}

    plant_hub = pulp.LpVariable.dicts(
        "plant_hub", [(p, h, s) for p in plant_codes for h in hub_codes for s in sku_codes],
        lowBound=0, cat="Continuous",
    )
    hub_cfa = pulp.LpVariable.dicts(
        "hub_cfa", [(h, c, s) for h in hub_codes for c in cfas for s in sku_codes],
        lowBound=0, cat="Continuous",
    )
    hub_ss_actual = pulp.LpVariable.dicts(
        "hub_ss", [(h, s) for h in hub_codes for s in sku_codes], lowBound=0,
    )
    hub_ss_shortfall = pulp.LpVariable.dicts(
        "hub_ss_shortfall", [(h, s) for h in hub_codes for s in sku_codes], lowBound=0,
    )
    unmet = pulp.LpVariable.dicts(
        "unmet", [(c, s) for c in cfas for s in sku_codes], lowBound=0,
    )

    # --- Objective ---
    prod_cost_terms = [
        prod_qty[(p, s)] * plants.loc[p, "prod_cost_per_kl"]
        for p in plant_codes for s in sku_codes
    ]
    plant_hub_cost_terms = [
        plant_hub[(p, h, s)] * plant_hub_cost.loc[p, f"to_{h}"]
        for p in plant_codes for h in hub_codes for s in sku_codes
    ]
    hub_cfa_cost_lookup = hub_cfa_cost.set_index("cfa")
    hub_cfa_cost_terms = [
        hub_cfa[(h, c, s)] * hub_cfa_cost_lookup.loc[c, f"from_{h}"]
        for h in hub_codes for c in cfas for s in sku_codes
    ]
    unmet_cost_terms = []
    for s in sku_codes:
        penalty = skus.loc[s, "penalty_per_kl"]
        mult = CONTRACTUAL_PENALTY_MULTIPLIER if skus.loc[s, "contractual"] else 1.0
        for c in cfas:
            unmet_cost_terms.append(unmet[(c, s)] * penalty * mult)
    ss_shortfall_cost_terms = [
        hub_ss_shortfall[(h, s)] * skus.loc[s, "penalty_per_kl"] * 0.5
        for h in hub_codes for s in sku_codes
    ]

    prob += (
        pulp.lpSum(prod_cost_terms) + pulp.lpSum(plant_hub_cost_terms)
        + pulp.lpSum(hub_cfa_cost_terms) + pulp.lpSum(unmet_cost_terms)
        + pulp.lpSum(ss_shortfall_cost_terms)
    )

    # --- Constraints ---
    # Plant line-type capacity: sum of SKU production sharing a line type <= capacity.
    for p in plant_codes:
        for line_type, capcol in LINE_TYPE_TO_CAPCOL.items():
            skus_on_line = [s for s in sku_codes if skus.loc[s, "line_type"] == line_type]
            if not skus_on_line:
                continue
            cap = plants.loc[p, capcol]
            prob += (
                pulp.lpSum(prod_qty[(p, s)] for s in skus_on_line) <= cap,
                f"cap_{p}_{line_type.replace(' ', '_').replace('<=', 'le')}",
            )

    # Plant flow conservation: a plant cannot ship out more of a SKU than it
    # produces this month (plants carry no opening inventory). This is "<="
    # rather than "==" deliberately: the 25 kl batch rule can force a plant to
    # produce slightly more than the network needs (you cannot make a
    # fractional batch of a grade). The cheapest treatment of that unavoidable
    # rounding surplus is to leave it at the plant as closing inventory
    # (a carried-forward asset) rather than pay freight to push it to a hub
    # that has no rewarded use for the extra buffer. Forcing equality here was
    # tested and produced a strictly worse plan (higher freight + forced
    # shortfalls), confirming "<=" is the correct, cost-minimising formulation.
    for p in plant_codes:
        for s in sku_codes:
            prob += (
                pulp.lpSum(plant_hub[(p, h, s)] for h in hub_codes) <= prod_qty[(p, s)],
                f"plant_flow_{p}_{s}",
            )

    # Hub inbound = outbound to CFAs + safety stock retained (net of opening inventory).
    for h in hub_codes:
        for s in sku_codes:
            inbound = pulp.lpSum(plant_hub[(p, h, s)] for p in plant_codes)
            outbound = pulp.lpSum(
                hub_cfa[(h, c, s)] for c in cfas if route_allowed(s, c, h)
            )
            opening = hub_open.get((s, h), 0.0)
            target_ss = hub_norm_ss.get((s, h), 0.0)

            prob += (
                opening + inbound == outbound + hub_ss_actual[(h, s)],
                f"hub_balance_{h}_{s}",
            )
            prob += (
                hub_ss_actual[(h, s)] + hub_ss_shortfall[(h, s)] >= target_ss,
                f"hub_ss_target_{h}_{s}",
            )

    # CFA demand balance: opening inventory + inbound from hubs + unmet = demand.
    for c in cfas:
        for s in sku_codes:
            d = demand.get((s, c))
            if d is None:
                continue
            opening = cfa_open.get((s, c), 0.0)
            inbound = pulp.lpSum(
                hub_cfa[(h, c, s)] for h in hub_codes if route_allowed(s, c, h)
            )
            prob += (
                opening + inbound + unmet[(c, s)] >= d,
                f"cfa_demand_{c}_{s}",
            )

    # No production for a plant-hub-SKU combo unless a plant->hub flow is allowed.
    # (All plants can supply all hubs per the case: "any plant can supply any hub".)

    # Prefer HiGHS: it proves (near-)optimality on this model in minutes, where
    # CBC stops on the time limit with an unproven incumbent (and PuLP then
    # mislabels that incumbent "Optimal"). gapRel=0.001 = stop within 0.1% of
    # the true optimum. Fall back to CBC if highspy isn't installed.
    try:
        solver = pulp.HiGHS(msg=False, timeLimit=time_limit_seconds, gapRel=0.001)
        prob.solve(solver)
    except Exception:
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_seconds)
        prob.solve(solver)
    status = pulp.LpStatus[prob.status]

    def _val(v):
        x = v.value()
        return 0.0 if x is None else max(0.0, x)

    production_rows = [
        {"sku": s, "plant": p, "qty_kl": _val(prod_qty[(p, s)])}
        for p in plant_codes for s in sku_codes
    ]
    plant_hub_rows = [
        {"sku": s, "plant": p, "hub": h, "qty_kl": _val(plant_hub[(p, h, s)])}
        for p in plant_codes for h in hub_codes for s in sku_codes
    ]
    hub_cfa_rows = [
        {"sku": s, "hub": h, "cfa": c, "qty_kl": _val(hub_cfa[(h, c, s)])}
        for h in hub_codes for c in cfas for s in sku_codes
    ]
    hub_ss_rows = [
        {"sku": s, "hub": h, "target_kl": hub_norm_ss.get((s, h), 0.0),
         "actual_kl": _val(hub_ss_actual[(h, s)]), "shortfall_kl": _val(hub_ss_shortfall[(h, s)])}
        for h in hub_codes for s in sku_codes
    ]
    unmet_rows = [
        {"sku": s, "cfa": c, "qty_kl": _val(unmet[(c, s)]),
         "penalty_per_kl": skus.loc[s, "penalty_per_kl"],
         "contractual": bool(skus.loc[s, "contractual"]),
         "cost": _val(unmet[(c, s)]) * skus.loc[s, "penalty_per_kl"]
                 * (CONTRACTUAL_PENALTY_MULTIPLIER if skus.loc[s, "contractual"] else 1.0)}
        for c in cfas for s in sku_codes
    ]

    production_df = pd.DataFrame(production_rows)
    plant_hub_df = pd.DataFrame(plant_hub_rows)
    hub_cfa_df = pd.DataFrame(hub_cfa_rows)
    hub_ss_df = pd.DataFrame(hub_ss_rows)
    unmet_df = pd.DataFrame(unmet_rows)

    total_prod_cost = sum(
        r["qty_kl"] * plants.loc[r["plant"], "prod_cost_per_kl"] for r in production_rows
    )
    total_plant_hub_cost = sum(
        r["qty_kl"] * plant_hub_cost.loc[r["plant"], f"to_{r['hub']}"] for r in plant_hub_rows
    )
    total_hub_cfa_cost = sum(
        r["qty_kl"] * hub_cfa_cost_lookup.loc[r["cfa"], f"from_{r['hub']}"] for r in hub_cfa_rows
    )
    total_unmet_cost = unmet_df["cost"].sum() if not unmet_df.empty else 0.0
    total_ss_shortfall_cost = sum(
        r["shortfall_kl"] * skus.loc[r["sku"], "penalty_per_kl"] * 0.5 for r in hub_ss_rows
    )

    cost_summary = {
        "production_cost": total_prod_cost,
        "plant_hub_transport_cost": total_plant_hub_cost,
        "hub_cfa_transport_cost": total_hub_cfa_cost,
        "unmet_demand_penalty_cost": total_unmet_cost,
        "hub_safety_stock_shortfall_cost": total_ss_shortfall_cost,
        "total_cost": (total_prod_cost + total_plant_hub_cost + total_hub_cfa_cost
                       + total_unmet_cost + total_ss_shortfall_cost),
        "total_unmet_volume_kl": unmet_df["qty_kl"].sum() if not unmet_df.empty else 0.0,
        "total_demand_kl": sum(demand.values()),
    }

    return PlanResult(
        status=status,
        production=production_df,
        plant_hub_flow=plant_hub_df,
        hub_cfa_flow=hub_cfa_df,
        hub_safety_stock=hub_ss_df,
        unmet_demand=unmet_df,
        cost_summary=cost_summary,
    )
