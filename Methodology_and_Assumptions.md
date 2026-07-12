# Levisol Supply Chain Case — Methodology & Assumptions

## 1. Overview

This solution addresses all three required components:

1. **Inventory Norms** — reorder point and days of cover per SKU × CFA, and per SKU × Hub, computed from 6 months of sales history and Exhibit E lead-time data.
2. **Production & Distribution Plan** — a MILP that decides Jan-2026 production by SKU × plant, plant→hub flow, hub→CFA flow, and hub safety stock, minimizing total OpEx.
3. **Planning Tool** — a Streamlit application (`app.py`) that lets a non-technical planner edit inputs and re-run both components live.

All code lives in `solution/src/`. Source data is `solution/data/raw_case_data.xlsx` (the case's own machine-readable data file — takes precedence over the PDF per the case instructions).

## 2. SKU Tier Classification

The case states SKUs are tiered A/B/C/D by sales volume, with tier volume shares given in Exhibit F (A=50%, B=30%, C=15%, D=5%). We derive each SKU's tier by:
1. Summing each SKU's total sales volume across all CFAs and all 6 months.
2. Ranking SKUs descending by that total.
3. Assigning tiers by cumulative share of total portfolio volume (top SKUs cumulatively accounting for 50% of volume → A, next 30% → B, next 15% → C, remaining 5% → D).

This is an assumption, since the case does not hand us tiers directly for all 100 SKUs — Exhibit D gives penalty cost and contractual flag only.

## 3. Inventory Norms (Component 1)

### 3.1 CFA-level norms

For each SKU × CFA:

- **Average daily demand** and its **standard deviation** are derived from the 6 months of sales history (Exhibit G), converting monthly figures to daily using 30 working days/month (per case instruction). Monthly standard deviation is converted to daily standard deviation by dividing by √30 (variance scales linearly with time for i.i.d. periods).
- **Lead time** = production lead time + plant→hub transit + hub→CFA transit, all from Exhibit E, using the **historically predefined source** for that SKU–CFA (the case explicitly says norms must use the predefined source, not the least-cost source — that flexibility is reserved for fulfilling Jan-2026 demand in Component 2).
- **Lead-time variability**: the data provides one "production variability" and one "transit lead variability" figure per SKU–CFA row (not split by leg). We combine them via root-sum-of-squares (independent variance sources) for the CFA echelon, since a CFA's full replenishment cycle spans all three legs.
- **Safety stock** is computed with the standard formula for simultaneously variable demand and variable lead time (assuming independence):

  SS = z · √( LT_avg · σ_d² + d_avg² · σ_LT² )

  where z is the service-level z-score for that SKU's tier fill-rate target (Exhibit F: A=98%→z≈2.05, B=97%→z≈1.88, C/D=92%→z≈1.41).

- **Reorder point** = d_avg · LT_avg + SS.
- **Days of Cover** = Reorder Point ÷ average daily demand (last 6 months), per case instruction.

### 3.2 Hub-level norms

The case fixes hub service level at a flat 98% for all SKUs (not tier-dependent).

- **Demand**: aggregated across all CFAs the hub historically serves for that SKU. Because CFA demands are assumed independent (per case instruction), pooled variance = **sum** of the individual CFA daily-demand variances — this is risk pooling, and is why hub safety stock is meaningfully less than the sum of its CFAs' safety stocks.
- **Lead time**: only the plant→hub leg is relevant (production lead time + plant-to-hub transit) — the hub's own replenishment trigger doesn't depend on the downstream hub→CFA leg.
- **Lead-time variability apportionment**: since the data's single transit-variability figure covers the full plant→hub→CFA transit and isn't split by leg, we apportion it to the plant→hub leg in proportion to that leg's share of total transit time, scaled by √(time) — i.e. `σ_leg = σ_total · √(t_leg / t_total_transit)` — reflecting that variance accumulates with elapsed time in a renewal-type delay process. **This is a modelling assumption we are transparent about**, made necessary because the underlying data doesn't split transit variability by leg.

## 4. Production & Distribution Plan (Component 2)

### 4.1 Objective

Minimize total OpEx = production cost + plant→hub transport cost + hub→CFA transport cost + penalty cost of unmet demand + penalty cost of hub safety-stock shortfall.

We deliberately treat **unmet demand as a soft, penalized outcome rather than a hard infeasibility**. In a real base-oil-shock scenario, total demand can exceed total capacity; a model that simply fails to solve is useless to a planner in a war room. Pricing shortfalls (using each SKU's penalty cost from Exhibit D) lets the optimizer make the same trade-off a human planner would: which SKUs to under-serve, weighted by the true commercial cost of doing so.

**Contractual SKUs** get an additional penalty multiplier (5×) on top of their listed penalty cost, reflecting the case's statement that under-supplying them "carries financial and reputational consequences that significantly exceed the normal lost-margin calculation" — a cost that isn't fully captured by the flat per-kL penalty figure alone. This is a soft rather than hard constraint deliberately: making contractual SKUs a hard constraint risks total model infeasibility if capacity is insufficient even for contractual volume alone; the heavy penalty achieves the same practical prioritization while keeping the model always solvable.

### 4.2 Constraints

- **Plant line-type capacity**: each SKU's pack size determines which production line it runs on (parsed from the unit container volume — e.g. "20 X 900 ML" → 0.9L/unit → the ≤1.5LT line). Total production of all SKUs sharing a line at a plant cannot exceed that line's monthly capacity.
- **Batch size**: production quantities are constrained to integer multiples of 25 kL (modeled as an integer "batch count" variable, not a continuous one rounded after the fact).
- **Hub flow balance**: hub outbound (to CFAs) + safety stock retained = opening inventory + inbound from plants, for each SKU at each hub.
- **Hub safety stock target**: actual hub safety stock is driven toward the Component-1 hub norm; any shortfall is captured as an explicit, penalized variable rather than silently ignored.
- **CFA demand balance**: opening inventory + inbound from hubs + unmet demand ≥ Jan-2026 forecast, for each SKU at each CFA.
- **Sourcing flexibility**: per the case ("material can be sourced from any of the 3 plants to ensure least-cost sourcing" and "any plant can supply any hub... CFAs may be supplied from either hub"), Component 2 does **not** restrict flows to the historical sourcing pattern used in Component 1 — the optimizer is free to choose the cheapest feasible routing.

### 4.3 What we chose not to supply, and why

Run the tool to see the specific SKU × CFA shortfalls for the current scenario — the **Unmet Demand** tab reports exactly which combinations were left short, by how much, and at what cost, ranked by total penalty impact. In general, the model will preferentially short lower-tier (C/D), non-contractual SKUs on high-cost routes before touching tier-A or contractual volume, because that minimizes total penalty cost — matching the business intent of protecting critical SKUs first.

## 5. Planning Tool (Component 3)

- **Stack**: Python (pandas for data prep, PuLP with the HiGHS solver for the MILP (CBC fallback), Streamlit for the UI, Plotly for charts/maps). Chosen for fast iteration and because HiGHS and CBC are open-source (no license dependency for judges to reproduce results).
- **Editable inputs**: plant capacities/production cost, plant→hub and hub→CFA transport cost tables, and Jan-2026 demand (editable inline or via CSV upload) are all exposed as data-editor tables in the sidebar — no code changes needed.
- **Graceful infeasibility handling**: unmet demand is a decision variable, not a failure mode, so the model always returns a plan; the UI surfaces shortfalls explicitly with quantity and cost rather than crashing.
- **Speed**: with a 60–120 second solver time limit (adjustable in the UI), HiGHS returns a near-optimal plan for the full 100-SKU × 3-plant × 2-hub × 10-CFA problem within a single planning-session timeframe.
- **No specialist knowledge required**: tabs are labeled by business question ("Inventory Norms," "Production & Distribution Plan," "Network Map"), with metrics, colored cost breakdowns, and a downloadable CSV of every output table.

## 6. Known Limitations

- Hub-level lead-time variability apportionment (Section 3.2) is a defensible assumption, not a directly-observed figure — the underlying data doesn't split transit variability by leg.
- The model treats Jan-2026 as a single-period plan (produce once, ship once) — it does not model multi-month inventory carry-forward or re-ordering within the month.
- The contractual-SKU penalty multiplier (5×) is a judgment call quantifying "significantly exceeds normal lost-margin," not a figure given in the case data; it is a parameter that can be tuned in `src/optimizer.py` (`CONTRACTUAL_PENALTY_MULTIPLIER`).
