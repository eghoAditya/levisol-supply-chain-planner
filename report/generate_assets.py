"""
Generates all charts (as PNG) and a JSON of key numbers for the Castrol-branded
submission PDF. Charts use Castrol brand colours (green/red/charcoal).

Run:  ../venv/bin/python3 generate_assets.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from pipeline import load_inputs, run_norms, run_plan

ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(exist_ok=True)

# Castrol brand palette
GREEN = "#009543"
DARK = "#1b3a2b"
RED = "#ED1C24"
GOLD = "#F4B400"
BLUE = "#2b6cb0"
GREY = "#6b7280"
LIGHT = "#e8f3ec"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "figure.dpi": 150,
})


def cr(x):
    """Format rupees as crore."""
    return x / 1e7


def main():
    inputs = load_inputs()
    tiers, cfa_norms, hub_norms = run_norms(inputs)
    plan = run_plan(inputs, hub_norms, time_limit_seconds=600)
    cs = plan.cost_summary

    # ---------- Chart 1: Cost breakdown (horizontal bar) ----------
    fig, ax = plt.subplots(figsize=(8, 3.4))
    items = [
        ("Production", cs["production_cost"], GREEN),
        ("Hub → CFA freight", cs["hub_cfa_transport_cost"], BLUE),
        ("Plant → Hub freight", cs["plant_hub_transport_cost"], GOLD),
        ("Hub buffer shortfall", cs["hub_safety_stock_shortfall_cost"], RED),
        ("Unmet demand penalty", cs["unmet_demand_penalty_cost"], GREY),
    ]
    labels = [i[0] for i in items]
    vals = [cr(i[1]) for i in items]
    colors = [i[2] for i in items]
    y = np.arange(len(labels))[::-1]
    bars = ax.barh(y, vals, color=colors, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("₹ crore")
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.01, b.get_y() + b.get_height() / 2,
                f"₹{v:.2f} cr", va="center", fontsize=9.5, color=DARK)
    ax.set_xlim(0, max(vals) * 1.18)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_title("Total OpEx = ₹{:.2f} crore".format(cr(cs["total_cost"])),
                 fontweight="bold", color=DARK, loc="left")
    plt.tight_layout()
    plt.savefig(ASSETS / "cost_breakdown.png", bbox_inches="tight")
    plt.close()

    # ---------- Chart 2: Production by plant ----------
    prod = plan.production[plan.production.qty_kl > 0]
    byp = prod.groupby("plant").qty_kl.sum().reindex(["BOM", "AHM", "KOL"]).fillna(0)
    pcost = inputs.plants["prod_cost_per_kl"].reindex(["BOM", "AHM", "KOL"])
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    names = [f"{p}\n₹{int(pcost[p]):,}/kl" for p in byp.index]
    bars = ax.bar(names, byp.values, color=[GREEN, GOLD, RED], width=0.6)
    for b, v in zip(bars, byp.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, f"{v:,.0f} kl",
                ha="center", fontsize=10, fontweight="bold", color=DARK)
    ax.set_ylabel("Volume produced (kl)")
    ax.set_ylim(0, byp.max() * 1.18)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_title("Production by plant: cheapest plant (KOL) runs hard",
                 fontweight="bold", color=DARK, loc="left", fontsize=11)
    plt.tight_layout()
    plt.savefig(ASSETS / "production_by_plant.png", bbox_inches="tight")
    plt.close()

    # ---------- Chart 3: Tier distribution (donut) ----------
    tc = tiers.value_counts().reindex(["A", "B", "C", "D"])
    total_sku = int(tc.sum())
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    wedges, _ = ax.pie(
        tc.values, colors=[GREEN, BLUE, GOLD, GREY],
        startangle=90, counterclock=False,
        wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2),
    )
    # Side-aligned labels with short elbow leader lines — labels sit fully
    # outside the ring on their own side, so nothing can overlap a wedge.
    for w, tier, n in zip(wedges, tc.index, tc.values):
        ang = np.deg2rad((w.theta1 + w.theta2) / 2)
        x, y = np.cos(ang), np.sin(ang)
        side = 1 if x >= 0 else -1
        ax.annotate(
            f"Tier {tier}: {n} SKUs",
            xy=(1.03 * x, 1.03 * y), xytext=(1.42 * side, 1.18 * y),
            ha="left" if side == 1 else "right", va="center",
            fontsize=10.5, color=DARK, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color="#aaaaaa", lw=0.9,
                            shrinkA=4, shrinkB=2,
                            connectionstyle="angle,angleA=0,angleB=60"),
        )
    ax.text(0, 0, f"{total_sku}\nSKUs", ha="center", va="center",
            fontsize=15, fontweight="bold", color=DARK)
    ax.set_xlim(-1.6, 1.6); ax.set_ylim(-1.3, 1.3)
    ax.set_title("Portfolio mix: SKU count by tier", fontweight="bold",
                 color=DARK, fontsize=11.5, pad=10)
    plt.tight_layout()
    plt.savefig(ASSETS / "tier_donut.png", bbox_inches="tight", dpi=170)
    plt.close()

    # ---------- Chart 4: Network flow map (schematic) ----------
    ph = plan.plant_hub_flow[plan.plant_hub_flow.qty_kl > 0].groupby(["plant", "hub"]).qty_kl.sum()
    hc = plan.hub_cfa_flow[plan.hub_cfa_flow.qty_kl > 0].groupby(["hub", "cfa"]).qty_kl.sum()
    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    plant_pos = {"BOM": (0, 8.4), "AHM": (0, 6.0), "KOL": (0, 3.6)}
    hub_pos = {"MHW": (3, 7.2), "MHE": (3, 4.2)}
    cfas = sorted(inputs.hub_cfa_cost["cfa"].unique())
    top, bot = 10.0, 1.2
    cfa_pos = {c: (6, top - i * ((top - bot) / (len(cfas) - 1))) for i, c in enumerate(cfas)}

    maxflow = max(ph.max(), hc.max())
    for (p, h), v in ph.items():
        x0, y0 = plant_pos[p]; x1, y1 = hub_pos[h]
        ax.plot([x0, x1], [y0, y1], color=GREEN, lw=0.6 + 6 * v / maxflow, alpha=0.6, zorder=1,
                solid_capstyle="round")
    for (h, c), v in hc.items():
        x0, y0 = hub_pos[h]; x1, y1 = cfa_pos[c]
        ax.plot([x0, x1], [y0, y1], color=BLUE, lw=0.4 + 4 * v / maxflow, alpha=0.38, zorder=1,
                solid_capstyle="round")

    for p, (x, y) in plant_pos.items():
        ax.scatter(x, y, s=1000, color=RED, zorder=3, edgecolor="white", lw=1.6)
        ax.text(x, y, p, ha="center", va="center", color="white", fontweight="bold", fontsize=9, zorder=4)
    for h, (x, y) in hub_pos.items():
        ax.scatter(x, y, s=1500, color=DARK, zorder=3, edgecolor="white", lw=1.6)
        ax.text(x, y, h, ha="center", va="center", color="white", fontweight="bold", fontsize=9, zorder=4)
    for c, (x, y) in cfa_pos.items():
        ax.scatter(x, y, s=340, color=GREEN, zorder=3, edgecolor="white", lw=1)
        ax.text(x + 0.28, y, c, ha="left", va="center", fontsize=8.8, color=DARK, zorder=4)

    hdr = 10.9
    ax.text(0, hdr, "PLANTS", ha="center", fontweight="bold", color=RED, fontsize=10.5)
    ax.text(3, hdr, "HUBS", ha="center", fontweight="bold", color=DARK, fontsize=10.5)
    ax.text(6, hdr, "CFAs", ha="left", fontweight="bold", color=GREEN, fontsize=10.5)
    ax.set_xlim(-0.9, 8.8); ax.set_ylim(0.4, 12.0)
    ax.axis("off")
    ax.text(-0.9, 11.7, "January 2026 network flow",
            fontweight="bold", color=DARK, fontsize=12, ha="left")
    ax.text(-0.9, 11.25, "green = plant → hub,  blue = hub → CFA;  line thickness ∝ volume",
            color=GREY, fontsize=9, ha="left")
    plt.tight_layout()
    plt.savefig(ASSETS / "network_flow.png", bbox_inches="tight", dpi=170)
    plt.close()

    # ---------- Chart 5: Scenario robustness ----------
    from dataclasses import replace
    scenarios = {"Base plan": plan}
    s1 = inputs.plants.copy()
    for col in ["cap_1_5lt", "cap_3_5lt", "cap_7_20lt", "cap_50lt", "cap_180_210lt"]:
        s1.loc["BOM", col] = round(s1.loc["BOM", col] * 0.5)
    scenarios["BOM cap -50%"] = run_plan(replace(inputs, plants=s1), hub_norms, 600)
    s2 = inputs.jan_forecast.copy(); s2["jan26_forecast_kl"] *= 1.4
    scenarios["Demand +40%"] = run_plan(replace(inputs, jan_forecast=s2), hub_norms, 600)
    s3 = inputs.plant_hub_cost.copy(); s3.loc["BOM", "to_MHW"] *= 5
    scenarios["BOM→MHW ×5 freight"] = run_plan(replace(inputs, plant_hub_cost=s3), hub_norms, 600)

    bad = [n for n, s in scenarios.items() if s.status != "Optimal"]
    if bad:
        raise RuntimeError(
            f"Scenarios not solved to optimality: {bad}. "
            "Their incumbent numbers are unreliable — raise the time limit instead of publishing them."
        )

    fig, ax1 = plt.subplots(figsize=(8.4, 4.0))
    names = list(scenarios.keys())
    costs = [cr(s.cost_summary["total_cost"]) for s in scenarios.values()]
    fills = [(1 - s.cost_summary["total_unmet_volume_kl"] / s.cost_summary["total_demand_kl"]) * 100
             for s in scenarios.values()]
    x = np.arange(len(names))
    cost_headroom = max(costs) * 1.30
    bars = ax1.bar(x - 0.21, costs, 0.4, color=GREEN, label="Total cost (₹ cr)", zorder=3)
    ax1.set_ylabel("Total cost (₹ crore)", color=GREEN, fontsize=10)
    ax1.set_ylim(0, cost_headroom)
    ax1.set_xticks(x); ax1.set_xticklabels(names, fontsize=9.5)
    ax1.tick_params(axis="y", labelcolor=GREEN)
    # Value labels go INSIDE each bar (white on green, dark on gold) so the
    # cost label can never collide with the fill-rate label next to it.
    for b, v in zip(bars, costs):
        ax1.text(b.get_x() + b.get_width() / 2, v - cost_headroom * 0.025,
                 f"₹{v:.1f} cr", ha="center", va="top",
                 fontsize=8.6, color="white", fontweight="bold", zorder=4)
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + 0.21, fills, 0.4, color=GOLD, label="Fill rate (%)", zorder=3)
    ax2.set_ylabel("Customer fill rate (%)", color="#b8860b", fontsize=10)
    ax2.set_ylim(0, 130)
    ax2.set_yticks([0, 25, 50, 75, 100])
    ax2.tick_params(axis="y", labelcolor="#b8860b")
    for b, v in zip(bars2, fills):
        ax2.text(b.get_x() + b.get_width() / 2, v - 2.6, f"{v:.1f}%",
                 ha="center", va="top", fontsize=8.6, color=DARK,
                 fontweight="bold", zorder=4)
    for s in ["top"]:
        ax1.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
    ax1.set_title("Every input shock re-solves cleanly: cost adapts, service holds",
                  fontweight="bold", color=DARK, loc="left", fontsize=11.5, pad=12)
    plt.tight_layout()
    plt.savefig(ASSETS / "robustness.png", bbox_inches="tight", dpi=170)
    plt.close()

    # ---------- Key numbers JSON ----------
    prod_total = prod.qty_kl.sum()
    ph_flow = plan.plant_hub_flow.qty_kl.sum()
    hc_flow = plan.hub_cfa_flow.qty_kl.sum()
    cfa_open = inputs.opening_inv[inputs.opening_inv.location.isin(cfas)].opening_inv_kl.sum()
    ss = plan.hub_safety_stock
    contractual_n = int(inputs.skus.contractual.sum())

    # example norm row for illustration
    ex = cfa_norms[(cfa_norms.sku == "SKU_001") & (cfa_norms.cfa == "Kolkata")].iloc[0]

    numbers = {
        "total_cost_cr": round(cr(cs["total_cost"]), 2),
        "production_cost_cr": round(cr(cs["production_cost"]), 2),
        "plant_hub_cr": round(cr(cs["plant_hub_transport_cost"]), 2),
        "hub_cfa_cr": round(cr(cs["hub_cfa_transport_cost"]), 2),
        "ss_shortfall_cr": round(cr(cs["hub_safety_stock_shortfall_cost"]), 3),
        "unmet_penalty_cr": round(cr(cs["unmet_demand_penalty_cost"]), 3),
        "total_demand_kl": round(cs["total_demand_kl"], 1),
        "unmet_kl": round(cs["total_unmet_volume_kl"], 2),
        "fill_rate_pct": round((1 - cs["total_unmet_volume_kl"] / cs["total_demand_kl"]) * 100, 2),
        "produced_kl": round(prod_total, 0),
        "shipped_to_hub_kl": round(ph_flow, 0),
        "hub_to_cfa_kl": round(hc_flow, 0),
        "cfa_opening_used_kl": round(cs["total_demand_kl"] - hc_flow, 0),
        "n_skus": int(inputs.skus.shape[0]),
        "n_cfa_norm_rows": int(len(cfa_norms)),
        "n_hub_norm_rows": int(len(hub_norms)),
        "contractual_skus": contractual_n,
        "ss_target_total": round(ss.target_kl.sum(), 1),
        "ss_shortfall_total": round(ss.shortfall_kl.sum(), 1),
        "ss_achieved_pct": round((1 - ss.shortfall_kl.sum() / ss.target_kl.sum()) * 100, 1),
        "example_norm": {
            "sku": "SKU_001", "cfa": "Kolkata",
            "avg_daily_demand_kl": round(float(ex.avg_daily_demand_kl), 2),
            "tier": str(ex.tier), "z": round(float(ex.z_score), 2),
            "lead_time_days": round(float(ex.total_lt_days), 1),
            "safety_stock_kl": round(float(ex.safety_stock_kl), 2),
            "reorder_point_kl": round(float(ex.reorder_point_kl), 2),
            "days_of_cover": round(float(ex.days_of_cover), 1),
        },
        "scenarios": [
            {"name": n, "cost_cr": round(cr(s.cost_summary["total_cost"]), 2),
             "unmet_kl": round(s.cost_summary["total_unmet_volume_kl"], 1),
             "status": s.status}
            for n, s in scenarios.items()
        ],
        "plant_hub_matrix": {
            f"{p}->{h}": round(float(v), 0) for (p, h), v in ph.items()
        },
    }
    (Path(__file__).resolve().parent / "numbers.json").write_text(json.dumps(numbers, indent=2))
    print("Assets + numbers.json generated.")
    print(json.dumps(numbers, indent=2))


if __name__ == "__main__":
    main()
