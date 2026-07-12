"""
Levisol Supply Chain Planning Tool — Streamlit front end.

Run with:  streamlit run app.py

Gives a non-technical planner:
  - editable inputs (plant capacity, production cost, transport cost,
    hub safety-stock override, Jan-26 demand) without touching code
  - one-click "Run Plan" that recomputes inventory norms + the
    production/distribution optimization
  - clear, actionable outputs: production plan, routing plan, cost summary,
    inventory norms, and an explicit unmet-demand report
  - graceful handling of infeasible/short scenarios (no crashes)
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import load_inputs, run_norms, run_plan

st.set_page_config(page_title="Levisol Supply Chain Planner", layout="wide", page_icon="🛢️")

CFA_COORDS = {
    "Guwahati": (26.1445, 91.7362), "Kolkata": (22.5726, 88.3639),
    "Jamshedpur": (22.8046, 86.2029), "Kanpur": (26.4499, 80.3319),
    "Haryana": (29.0588, 76.0856), "Rajpura": (30.4849, 76.5936),
    "Bhiwandi": (19.3002, 73.0629), "Ahmedabad": (23.0225, 72.5714),
    "Bangalore": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867),
}
HUB_COORDS = {"MHW": (19.0760, 72.8777), "MHE": (22.5726, 88.3639)}
PLANT_COORDS = {"BOM": (19.0760, 72.8777), "AHM": (23.0225, 72.5714), "KOL": (22.5726, 88.3639)}


@st.cache_resource
def get_base_inputs():
    return load_inputs()


def init_session_state():
    if "inputs" not in st.session_state:
        base = get_base_inputs()
        st.session_state.plants_edit = base.plants.copy()
        st.session_state.plant_hub_cost_edit = base.plant_hub_cost.copy()
        st.session_state.hub_cfa_cost_edit = base.hub_cfa_cost.copy()
        st.session_state.jan_forecast_edit = base.jan_forecast.copy()
        st.session_state.inputs = base
        st.session_state.plan_result = None
        st.session_state.norms = None


def sidebar_scenario_editor(base):
    st.sidebar.header("Scenario Inputs")
    st.sidebar.caption("Edit any value below, then click Run Plan. Changes only affect this session.")

    with st.sidebar.expander("Plant capacities & production cost", expanded=False):
        st.session_state.plants_edit = st.data_editor(
            st.session_state.plants_edit, key="plants_editor", use_container_width=True,
        )

    with st.sidebar.expander("Plant → Hub transport cost (₹/kl)", expanded=False):
        st.session_state.plant_hub_cost_edit = st.data_editor(
            st.session_state.plant_hub_cost_edit, key="plant_hub_editor", use_container_width=True,
        )

    with st.sidebar.expander("Hub → CFA transport cost (₹/kl)", expanded=False):
        st.session_state.hub_cfa_cost_edit = st.data_editor(
            st.session_state.hub_cfa_cost_edit, key="hub_cfa_editor", use_container_width=True,
        )

    with st.sidebar.expander("Jan-2026 demand forecast (kl)", expanded=False):
        st.caption("100 SKUs x 10 CFAs — edit specific rows or upload a replacement CSV below.")
        uploaded = st.file_uploader("Replace with CSV (sku, cfa, jan26_forecast_kl)", type="csv")
        if uploaded is not None:
            try:
                new_demand = pd.read_csv(uploaded)
                required = {"sku", "cfa", "jan26_forecast_kl"}
                if not required.issubset(new_demand.columns):
                    st.error(f"CSV must have columns: {sorted(required)}")
                else:
                    st.session_state.jan_forecast_edit = new_demand
                    st.success(f"Loaded {len(new_demand)} demand rows.")
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
        st.dataframe(st.session_state.jan_forecast_edit.head(20), use_container_width=True)

    time_limit = st.sidebar.slider("Solver time limit (seconds)", 10, 300, 60)

    run = st.sidebar.button("▶ Run Plan", type="primary", use_container_width=True)
    reset = st.sidebar.button("Reset to original case data", use_container_width=True)
    if reset:
        for k in ["plants_edit", "plant_hub_cost_edit", "hub_cfa_cost_edit", "jan_forecast_edit"]:
            del st.session_state[k]
        st.session_state.pop("inputs", None)
        st.rerun()

    return run, time_limit


def render_cost_summary(cost_summary: dict):
    cols = st.columns(5)
    labels = [
        ("Production Cost", "production_cost"),
        ("Plant→Hub Transport", "plant_hub_transport_cost"),
        ("Hub→CFA Transport", "hub_cfa_transport_cost"),
        ("Unmet Demand Penalty", "unmet_demand_penalty_cost"),
        ("Total Cost", "total_cost"),
    ]
    for col, (label, key) in zip(cols, labels):
        col.metric(label, f"₹{cost_summary.get(key, 0):,.0f}")

    served = cost_summary.get("total_demand_kl", 0) - cost_summary.get("total_unmet_volume_kl", 0)
    fill_rate = served / cost_summary["total_demand_kl"] * 100 if cost_summary.get("total_demand_kl") else 0
    st.metric("Overall Fill Rate", f"{fill_rate:.1f}%",
              help="Volume served / total Jan-2026 forecast demand, across all SKUs and CFAs.")


def render_unmet_demand(unmet_df: pd.DataFrame):
    short = unmet_df[unmet_df["qty_kl"] > 1e-6].sort_values("cost", ascending=False)
    if short.empty:
        st.success("All demand fully met within capacity — no shortfalls.")
        return
    st.warning(f"{len(short)} SKU–CFA combinations were left short, "
               f"totalling {short['qty_kl'].sum():,.1f} kl "
               f"(₹{short['cost'].sum():,.0f} penalty cost).")
    st.dataframe(
        short.style.format({"qty_kl": "{:.2f}", "penalty_per_kl": "₹{:,.0f}", "cost": "₹{:,.0f}"}),
        use_container_width=True, height=300,
    )


def render_flow_map(plant_hub_df, hub_cfa_df):
    fig = go.Figure()
    ph = plant_hub_df.groupby(["plant", "hub"])["qty_kl"].sum().reset_index()
    ph = ph[ph["qty_kl"] > 0.5]
    for _, r in ph.iterrows():
        lat0, lon0 = PLANT_COORDS[r["plant"]]
        lat1, lon1 = HUB_COORDS[r["hub"]]
        fig.add_trace(go.Scattergeo(
            lat=[lat0, lat1], lon=[lon0, lon1], mode="lines",
            line=dict(width=max(1, min(8, r["qty_kl"] / 200)), color="#2ca02c"),
            opacity=0.6, showlegend=False,
            hovertext=f"{r['plant']} → {r['hub']}: {r['qty_kl']:.0f} kl", hoverinfo="text",
        ))

    hc = hub_cfa_df.groupby(["hub", "cfa"])["qty_kl"].sum().reset_index()
    hc = hc[hc["qty_kl"] > 0.5]
    for _, r in hc.iterrows():
        lat0, lon0 = HUB_COORDS[r["hub"]]
        lat1, lon1 = CFA_COORDS[r["cfa"]]
        fig.add_trace(go.Scattergeo(
            lat=[lat0, lat1], lon=[lon0, lon1], mode="lines",
            line=dict(width=max(1, min(8, r["qty_kl"] / 100)), color="#1f77b4"),
            opacity=0.5, showlegend=False,
            hovertext=f"{r['hub']} → {r['cfa']}: {r['qty_kl']:.0f} kl", hoverinfo="text",
        ))

    all_points = {**PLANT_COORDS, **HUB_COORDS, **CFA_COORDS}
    fig.add_trace(go.Scattergeo(
        lat=[v[0] for v in all_points.values()], lon=[v[1] for v in all_points.values()],
        text=list(all_points.keys()), mode="markers+text", textposition="top center",
        marker=dict(size=8, color="#d62728"), showlegend=False,
    ))
    fig.update_geos(scope="asia", center=dict(lat=22, lon=80), projection_scale=4,
                     showland=True, landcolor="#f0f0f0", showcountries=True)
    fig.update_layout(height=550, margin=dict(l=0, r=0, t=30, b=0),
                       title="Network Flow — Jan 2026 Plan (green = plant→hub, blue = hub→CFA)")
    st.plotly_chart(fig, use_container_width=True)


def main():
    st.title("🛢️ Levisol Supply Chain Planning Tool")
    st.caption("Power Up 4.0 — Production & Distribution Optimizer | Balancing Act case study")

    init_session_state()
    base = st.session_state.inputs
    run, time_limit = sidebar_scenario_editor(base)

    tab_norms, tab_plan, tab_map, tab_data = st.tabs(
        ["📦 Inventory Norms", "🏭 Production & Distribution Plan", "🗺️ Network Map", "📊 Raw Data"]
    )

    # Build a fresh scenario object each run rather than mutating `base`
    # in place — `base` is the @st.cache_resource singleton, so writing to
    # its attributes would permanently corrupt the cached original data and
    # break "Reset to original case data".
    scenario_inputs = replace(
        base,
        plants=st.session_state.plants_edit,
        plant_hub_cost=st.session_state.plant_hub_cost_edit,
        hub_cfa_cost=st.session_state.hub_cfa_cost_edit,
        jan_forecast=st.session_state.jan_forecast_edit,
    )

    if run:
        with st.spinner("Computing inventory norms..."):
            tiers, cfa_norms, hub_norms = run_norms(scenario_inputs)
            st.session_state.norms = (tiers, cfa_norms, hub_norms)
        with st.spinner(f"Solving production & distribution plan (up to {time_limit}s)..."):
            try:
                plan = run_plan(scenario_inputs, hub_norms, time_limit_seconds=time_limit)
                st.session_state.plan_result = plan
                st.session_state.plan_error = None
            except Exception as e:
                st.session_state.plan_result = None
                st.session_state.plan_error = str(e)

    with tab_norms:
        if st.session_state.norms is None:
            st.info("Click **Run Plan** in the sidebar to compute inventory norms.")
        else:
            tiers, cfa_norms, hub_norms = st.session_state.norms
            st.subheader("CFA-level Inventory Norms")
            st.caption("Reorder point and days of cover per SKU × CFA, using demand + lead-time variability.")
            st.dataframe(
                cfa_norms[[
                    "sku", "cfa", "hub", "tier", "avg_daily_demand_kl", "std_daily_demand_kl",
                    "total_lt_days", "lt_std_days", "z_score", "safety_stock_kl",
                    "reorder_point_kl", "days_of_cover",
                ]].round(2), use_container_width=True, height=350,
            )
            csv = cfa_norms.to_csv(index=False).encode()
            st.download_button("Download CFA norms (CSV)", csv, "cfa_inventory_norms.csv")

            st.subheader("Hub-level Inventory Norms (98% service level)")
            st.dataframe(hub_norms.round(2), use_container_width=True, height=300)
            st.download_button("Download hub norms (CSV)", hub_norms.to_csv(index=False).encode(),
                                "hub_inventory_norms.csv")

    with tab_plan:
        if getattr(st.session_state, "plan_error", None):
            st.error(f"The solver could not produce a plan: {st.session_state.plan_error}")
        elif st.session_state.plan_result is None:
            st.info("Click **Run Plan** in the sidebar to generate the production & distribution plan.")
        else:
            plan = st.session_state.plan_result
            st.caption(f"Solver status: **{plan.status}**")
            render_cost_summary(plan.cost_summary)

            st.subheader("Unmet Demand")
            render_unmet_demand(plan.unmet_demand)

            st.subheader("Production Plan (by SKU × Plant)")
            prod = plan.production[plan.production["qty_kl"] > 0].sort_values("qty_kl", ascending=False)
            st.dataframe(prod.round(2), use_container_width=True, height=300)
            st.download_button("Download production plan (CSV)", prod.to_csv(index=False).encode(),
                                "production_plan.csv")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Plant → Hub Routing")
                ph = plan.plant_hub_flow[plan.plant_hub_flow["qty_kl"] > 0]
                st.dataframe(ph.round(2), use_container_width=True, height=250)
            with c2:
                st.subheader("Hub → CFA Routing")
                hc = plan.hub_cfa_flow[plan.hub_cfa_flow["qty_kl"] > 0]
                st.dataframe(hc.round(2), use_container_width=True, height=250)

            st.subheader("Hub Safety Stock — Target vs Achieved")
            st.dataframe(plan.hub_safety_stock.round(2), use_container_width=True, height=250)

            fig = px.pie(
                names=["Production", "Plant→Hub Transport", "Hub→CFA Transport", "Unmet Penalty", "SS Shortfall"],
                values=[
                    plan.cost_summary["production_cost"], plan.cost_summary["plant_hub_transport_cost"],
                    plan.cost_summary["hub_cfa_transport_cost"], plan.cost_summary["unmet_demand_penalty_cost"],
                    plan.cost_summary["hub_safety_stock_shortfall_cost"],
                ], title="Cost Breakdown",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab_map:
        if st.session_state.plan_result is None:
            st.info("Run a plan to see the routing map.")
        else:
            render_flow_map(st.session_state.plan_result.plant_hub_flow, st.session_state.plan_result.hub_cfa_flow)

    with tab_data:
        st.subheader("Current scenario inputs (editable in sidebar)")
        st.write("Plants"); st.dataframe(st.session_state.plants_edit)
        st.write("Plant → Hub cost"); st.dataframe(st.session_state.plant_hub_cost_edit)
        st.write("Hub → CFA cost"); st.dataframe(st.session_state.hub_cfa_cost_edit)
        st.write("Jan-2026 demand (first 50 rows)"); st.dataframe(st.session_state.jan_forecast_edit.head(50))


if __name__ == "__main__":
    main()
