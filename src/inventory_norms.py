"""
Component 1 — Inventory Norms.

For every SKU x CFA in scope, computes:
  - average daily demand (from 6-month sales history)
  - demand uncertainty (daily std dev), estimated from *forecast error*
    (actual sales vs. Exhibit H forecast for the same 6 months) rather than
    raw sales volatility — see rationale below
  - total replenishment lead time and its variability (from Exhibit E)
  - safety stock, reorder point (kL), days of cover

Also computes hub-level norms (aggregated demand across each hub's CFAs,
fixed 98% service level for every SKU at the hub echelon).

Why forecast error, not raw sales variance, drives demand uncertainty
----------------------------------------------------------------------
The case explicitly asks norms to use "sales history, forecast accuracy
data, and lead time information" and says forecast accuracy is "relevant to
setting appropriate inventory buffers." This matters because Jan-2026
production is planned against a *forecast* (Exhibit J), not against known
demand — the risk safety stock protects against is the forecast being wrong
during the replenishment window, not historical demand simply being
volatile. Classic inventory theory (e.g. Silver-Peterson-Pyke) therefore
sizes safety stock from forecast error (RMSE of actual vs. forecast), which
is what we do here: sigma_d = RMSE(sales_kl - forecast_kl) over the 6
months of history, converted from monthly to daily via /sqrt(30). Raw
sales-history std dev is also computed and retained in the output as a
cross-check / diagnostic column.

Method
------
Reorder Point = (avg daily demand x avg lead time) + Safety Stock

Safety Stock combines *demand* variability and *lead-time* variability using
the standard combined formula for the case where both demand and lead time
are random variables (assuming independence):

    SS = z * sqrt( LT_avg * sigma_d^2  +  d_avg^2 * sigma_LT^2 )

where:
    z        = service-level z-score (CFA: tier-based fill rate; Hub: 98% flat)
    d_avg    = average daily demand (from 6-month sales history)
    sigma_d  = std dev of daily demand uncertainty (forecast-error RMSE)
    LT_avg   = average total lead time in days
             = production lead time + plant->hub transit + hub->CFA transit
    sigma_LT = combined lead-time std dev
             = sqrt(prod_lt_var^2 + transit_lt_var^2)   (days)

This is the textbook "variable demand, variable lead time" safety-stock
formula (used because both demand and lead time have documented variability
in this case, so a demand-only formula would understate risk).

Days of Cover = Reorder Point / avg daily demand (last 6 months sales).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

MONTH_COLS = ["Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25"]
DAYS_PER_MONTH = 30  # per case instructions: "30 working days to be considered"


def z_for_fill_rate(fill_rate: float) -> float:
    return norm.ppf(fill_rate)


def compute_cfa_norms(sales: pd.DataFrame, source_lt: pd.DataFrame,
                       skus: pd.DataFrame, tiers: pd.Series,
                       service_levels: pd.DataFrame,
                       forecast: pd.DataFrame = None) -> pd.DataFrame:
    """Returns one row per SKU x CFA with demand stats, lead-time stats, and
    the resulting safety stock / reorder point / days of cover."""

    # --- Average daily demand from 6-month sales history (per case instruction) ---
    wide = sales.pivot_table(index=["sku", "cfa"], columns="month",
                              values="sales_kl", aggfunc="sum")
    wide = wide.reindex(columns=MONTH_COLS)
    monthly_mean = wide.mean(axis=1)
    monthly_std = wide.std(axis=1, ddof=1).fillna(0.0)

    demand = pd.DataFrame({
        "avg_monthly_demand_kl": monthly_mean,
        "std_monthly_demand_kl": monthly_std,
    }).reset_index()
    demand["avg_daily_demand_kl"] = demand["avg_monthly_demand_kl"] / DAYS_PER_MONTH
    # Cross-check / diagnostic only: raw sales-history std, monthly -> daily.
    demand["std_daily_demand_kl_raw_sales"] = demand["std_monthly_demand_kl"] / np.sqrt(DAYS_PER_MONTH)

    # --- Demand uncertainty for safety stock: forecast-error RMSE (see module docstring) ---
    if forecast is not None:
        merged = sales.merge(forecast, on=["sku", "cfa", "month"], how="inner")
        merged["error"] = merged["sales_kl"] - merged["forecast_kl"]
        fe_rmse_monthly = (
            merged.groupby(["sku", "cfa"])["error"]
            .apply(lambda e: np.sqrt((e ** 2).mean()))
            .rename("forecast_error_rmse_monthly")
            .reset_index()
        )
        demand = demand.merge(fe_rmse_monthly, on=["sku", "cfa"], how="left")
        demand["std_daily_demand_kl"] = demand["forecast_error_rmse_monthly"] / np.sqrt(DAYS_PER_MONTH)
        # Fall back to raw sales std where forecast history is missing.
        demand["std_daily_demand_kl"] = demand["std_daily_demand_kl"].fillna(demand["std_daily_demand_kl_raw_sales"])
    else:
        demand["std_daily_demand_kl"] = demand["std_daily_demand_kl_raw_sales"]

    # --- Lead time statistics from Exhibit E (one row per sku x cfa, historical/predefined source) ---
    lt = source_lt.copy()
    lt["total_lt_days"] = lt["lt_plant_to_hub"] + lt["lt_hub_to_cfa"] + lt["prod_lt"]
    # The data provides a single transit-variability figure per route rather
    # than splitting it by leg. We combine it with production variability for
    # the CFA echelon (which cares about total end-to-end replenishment risk).
    lt["lt_std_days"] = np.sqrt(lt["prod_lt_var"] ** 2 + lt["transit_lt_var"] ** 2)

    df = demand.merge(
        lt[["sku", "cfa", "hub", "total_lt_days", "lt_std_days",
            "lt_plant_to_hub", "lt_hub_to_cfa", "prod_lt", "prod_lt_var", "transit_lt_var"]],
        on=["sku", "cfa"], how="inner",
    )

    df = df.merge(tiers.rename("tier"), left_on="sku", right_index=True, how="left")
    df["tier"] = df["tier"].fillna("D")
    df = df.merge(service_levels["target_fill_rate"], left_on="tier", right_index=True, how="left")
    df["z_score"] = df["target_fill_rate"].apply(z_for_fill_rate)

    df["safety_stock_kl"] = df["z_score"] * np.sqrt(
        df["total_lt_days"] * df["std_daily_demand_kl"] ** 2
        + (df["avg_daily_demand_kl"] ** 2) * (df["lt_std_days"] ** 2)
    )

    df["reorder_point_kl"] = df["avg_daily_demand_kl"] * df["total_lt_days"] + df["safety_stock_kl"]
    df["days_of_cover"] = df["reorder_point_kl"] / df["avg_daily_demand_kl"].replace(0, np.nan)
    df["days_of_cover"] = df["days_of_cover"].fillna(0.0)

    return df.merge(skus[["penalty_per_kl", "contractual", "line_type"]],
                     left_on="sku", right_index=True, how="left")


def compute_hub_norms(cfa_norms: pd.DataFrame) -> pd.DataFrame:
    """Hub-level safety stock per SKU, at a flat 98% service level (per case
    instructions — hub service level is 98% for all grades, not tier-based).

    Demand: aggregated across all CFAs historically served by that hub for
    this SKU. CFA demands are assumed independent (per case instructions), so
    the pooled variance is the sum of individual CFA variances — this is risk
    pooling, and it is why hub-level safety stock is *not* simply the sum of
    CFA-level safety stocks.

    Lead time: only the plant -> hub leg matters here (production lead time +
    plant-to-hub transit), since the hub's own reorder trigger doesn't depend
    on the downstream hub -> CFA leg. The case data gives one transit-variance
    figure per SKU-CFA route covering the full plant->hub->CFA transit, not
    split by leg, so we apportion it to the plant->hub leg in proportion to
    that leg's share of total transit time, scaled by sqrt(time) (variance
    accumulates in proportion to elapsed time for a renewal-type delay
    process) — i.e. sigma_leg = sigma_total * sqrt(t_leg / t_total_transit).
    """
    HUB_Z = z_for_fill_rate(0.98)

    rows = []
    for (sku, hub), g in cfa_norms.groupby(["sku", "hub"]):
        avg_daily = g["avg_daily_demand_kl"].sum()
        pooled_std_daily = np.sqrt((g["std_daily_demand_kl"] ** 2).sum())

        # Plant->hub leg is a property of (sku, hub), not the individual CFA,
        # so it should be constant across rows in this group; take the mean
        # defensively in case of minor data inconsistencies.
        prod_lt = g["prod_lt"].mean()
        prod_lt_var = g["prod_lt_var"].mean()
        lt_plant_hub = g["lt_plant_to_hub"].mean()
        lt_hub_cfa = g["lt_hub_to_cfa"].mean()
        transit_var_total = g["transit_lt_var"].mean()

        total_transit = lt_plant_hub + lt_hub_cfa
        leg_share = lt_plant_hub / total_transit if total_transit > 0 else 0.0
        transit_var_hub_leg = transit_var_total * np.sqrt(leg_share)

        hub_lt = prod_lt + lt_plant_hub
        hub_lt_std = np.sqrt(prod_lt_var ** 2 + transit_var_hub_leg ** 2)

        safety_stock = HUB_Z * np.sqrt(
            hub_lt * pooled_std_daily ** 2 + (avg_daily ** 2) * (hub_lt_std ** 2)
        )
        reorder_point = avg_daily * hub_lt + safety_stock
        days_of_cover = reorder_point / avg_daily if avg_daily > 0 else 0.0

        rows.append({
            "sku": sku, "hub": hub,
            "avg_daily_demand_kl": avg_daily,
            "pooled_std_daily_demand_kl": pooled_std_daily,
            "hub_lead_time_days": hub_lt,
            "hub_lead_time_std_days": hub_lt_std,
            "z_score": HUB_Z,
            "safety_stock_kl": safety_stock,
            "reorder_point_kl": reorder_point,
            "days_of_cover": days_of_cover,
        })
    return pd.DataFrame(rows)
