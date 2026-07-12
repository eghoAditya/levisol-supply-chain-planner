# ⚡ QUICK OVERVIEW — Levisol Supply Chain Project
### Read this first (5 min). Then go deep with `PROJECT_GUIDE_HINGLISH.md`.

---

## 1. WHAT WE HAVE TO DO (The Problem)

**Levisol** (a Castrol-style lubricant company) makes 100 products (SKUs) and delivers them across India through this network:

```
3 Plants  →  2 Hubs  →  10 CFAs (regional warehouses)  →  customers
```

A raw-material price shock has hit. Management wants to **cut cost and free up cash** while making sure **critical products never run out of stock**. They asked us (the consulting team) to deliver **3 things**:

1. **Inventory Norms** — for every product at every warehouse, how much buffer stock to hold and when to reorder.
2. **Production & Distribution Plan** — for January 2026: exactly what to produce, where, and how to ship it, at the **lowest total cost**.
3. **A Planning Tool** — software a non-technical planner can use every month to redo the plan when inputs change.

**Key challenge:** demand can exceed factory capacity, so every choice has a cost. We must find the cheapest overall plan and protect the most important products first.

*(Unit note: everything is measured in **kl** = kilolitre = 1,000 litres = volume. Not kg, not bottles.)*

---

## 2. WHAT WE ARE DOING (Our Solution)

We built a complete, working system with three parts matching the three deliverables:

| Deliverable | What we built | Result |
|---|---|---|
| **Component 1 — Inventory Norms** | A statistics engine that calculates safety stock, reorder point, and days-of-cover for all 957 product×warehouse combinations + 151 product×hub combinations | Output: `inventory_norms.xlsx` |
| **Component 2 — Production Plan** | An optimization model that finds the cheapest way to produce and ship everything | **₹9.75 crore total cost, 100% of customer demand met** |
| **Component 3 — Planning Tool** | A web app (Streamlit) where anyone can edit inputs, click "Run", and see a fresh plan + map + costs | Live, tested against all input-change types |

Plus written deliverables: methodology document and a plan report.

---

## 3. HOW WE ARE DOING IT (The Approach)

### Component 1 — Inventory Norms (statistics)
- **Average daily demand** comes from 6 months of sales history.
- **Demand uncertainty** comes from **forecast error** (actual sales vs. what was forecast) — because next month's plan is built on a forecast, and safety stock protects against that forecast being wrong.
- **Lead-time uncertainty** comes from the production + transit variability data.
- We combine both into the standard **safety stock formula**:
  `Safety Stock = z × √(LeadTime × demand_variance + demand² × leadtime_variance)`
- `z` is set by the service-level target (Hub = 98%; CFAs = 98/97/92% by product tier A/B/C/D).
- **Reorder Point** = (avg daily demand × lead time) + safety stock. **Days of Cover** = ROP ÷ daily demand.

### Component 2 — Production & Distribution Plan (optimization)
- We built a **MILP** (Mixed-Integer Linear Program) that **minimises total cost** = production + plant→hub freight + hub→CFA freight + penalty for any unmet demand + penalty for any hub buffer shortfall.
- **Rules it respects:** plant line capacities, the 25 kl batch rule (production only in multiples of 25 kl), flow balance at hubs and CFAs, and starting inventory.
- **Smart part:** instead of crashing when demand > capacity, unmet demand is a *priced* option — the model chooses the cheapest demand to miss, and **contractual products get a 5× penalty** so they're protected first. This means the tool always produces a usable plan.

### Component 3 — Planning Tool (usability)
- Built in **Python + Streamlit** (web UI) with **Plotly** charts and an India routing map.
- Planner edits any input (capacity, cost, demand — or uploads a new CSV), clicks **Run Plan**, and gets: inventory norms, production plan, routing, cost breakdown, an explicit "what's unmet" report, and a network map.
- Handles the on-the-day test (judges change an input 30 min before) without breaking.

---

## 4. THE HEADLINE NUMBER

> **January 2026 plan: ₹9.75 crore total cost, 100% of customer demand met.**
> Cheapest plant (Kolkata) feeds the East hub; Mumbai feeds the West hub — routing follows the freight economics exactly. Only a tiny (1.0%) internal hub-buffer shortfall on fully-utilised production lines; zero customer demand sacrificed.

---

## 5. WHAT'S DONE vs. LEFT

**Done & verified:** all 3 components run correctly on the real data; tool tested against capacity/demand/cost changes.
**Left (to do together):** you review + test the tool yourself, build the presentation deck, and practice defending the assumptions.

---

*Full detail (every file, every formula, every Excel column, how to test new data, assumptions to defend) is in `PROJECT_GUIDE_HINGLISH.md`.*
