# Levisol Supply Chain Planning Tool — Power Up 4.0 Submission

## Setup (one-time)

```bash
cd solution
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy scipy openpyxl pulp streamlit plotly xlsxwriter
```

## Run the planning tool (Component 3 — live demo)

```bash
source venv/bin/activate
streamlit run app.py
```

Opens in your browser. Edit any input in the sidebar (plant capacity, transport cost, demand — inline or via CSV upload), click **Run Plan**, and all three components refresh: inventory norms, production/distribution plan, cost breakdown, unmet-demand report, and a network flow map.

## Run components individually from the command line

```bash
cd src
../venv/bin/python3 build_norms.py   # Component 1 -> ../outputs/inventory_norms.xlsx
../venv/bin/python3 build_plan.py    # Component 2 -> ../outputs/production_distribution_plan.xlsx
```

## Project layout

```
solution/
  data/raw_case_data.xlsx          # case's machine-readable data file (source of truth)
  src/
    data_loader.py                 # parses raw workbook into tidy DataFrames + SKU tiering
    inventory_norms.py             # Component 1: CFA & Hub reorder points, safety stock, days of cover
    optimizer.py                   # Component 2: MILP production/distribution plan (PuLP + HiGHS (CBC fallback))
    pipeline.py                    # wires the above together; shared by CLI scripts and app.py
    build_norms.py / build_plan.py # CLI entry points, write outputs/*.xlsx
  app.py                           # Component 3: Streamlit planning tool
  outputs/                         # generated Excel outputs (not checked in until you run the scripts)
  Methodology_and_Assumptions.md   # Component 4 deliverable
```

## Notes for the live demo

- The sidebar sliders/tables are the "changed input set" surface — plant capacity, transport costs, and demand can all be edited or replaced (CSV upload for demand) without touching code.
- If total demand exceeds capacity, the plan still solves (status "Optimal") — unmet demand shows up as an explicit, penalized, ranked table in the Production & Distribution Plan tab rather than crashing.
- Solver time limit is adjustable (10-300s) in the sidebar; ~60-120s is enough for the full 100-SKU problem on a laptop.
