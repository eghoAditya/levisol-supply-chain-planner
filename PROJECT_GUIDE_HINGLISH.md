# 📘 LEVISOL SUPPLY CHAIN PROJECT — COMPLETE GUIDE (Hinglish)
### Power Up 4.0 — "Balancing Act" | Zero se samajhne ke liye poori guide

> **Is guide ka maksad:** Agar aapne pehli baar ye project dekha hai, to ye document padhkar aap **pura project samajh jaoge** — problem kya hai, humne kya banaya, har file kya kaam kar rahi hai, screen pe jo numbers dikh rahe hain unka matlab kya hai, aur naye data pe kaise test karein. Padho, thoda practice karo, phir aap kisi ko bhi confidently explain kar paoge.

---

## 🎯 PART 1: PROBLEM KYA HAI? (Basics)

### 1.1 Kahani (Story)
**Levisol** ek lubricant company hai (basically Castrol ka ek fictional naam). Ye engine oil, gear oil, coolant jaise products banati hai aur pure India mein bechti hai.

Ek problem aa gayi hai: **"base-oil shock"** — matlab raw material (base oil) ke daam achanak upar-neeche ho rahe hain, aur company pe paisa bachane (cash) aur cost kam karne ka pressure hai. Saath hi, important products kabhi **out of stock** nahi hone chahiye (kyunki agar dealer ke paas stock khatam, to wo doosri company ka brand bechne lagega — permanent customer loss).

Company ne humein (consultant team) bulaya hai ye decide karne ke liye:
1. **Kitna stock** har warehouse mein rakhein? (Inventory norms)
2. **Kya banayein, kahan banayein, aur kaise bhejein** taaki cost sabse kam ho? (Production + Distribution plan)
3. Ek **tool** banao jise koi bhi planner (jo coding nahi jaanta) har mahine use kar sake.

### 1.2 Network kaisa hai? (Supply chain ka structure)

Maal (product) is raaste se ghar tak pahunchta hai:

```
   3 PLANTS          →      2 HUBS          →      10 CFAs        →  Customer
 (factories)            (bade warehouse)      (regional warehouse)

  BOM (Mumbai)  ┐                          ┌→ Guwahati (East)
  AHM (Ahmedabad)├→  MHW (Mother Hub West) ─┼→ Kolkata (East)
  KOL (Kolkata) ┘   MHE (Mother Hub East)  ┼→ Jamshedpur (East)
                                            ┼→ Kanpur (North)
                                            ┼→ Haryana (North)
                                            ┼→ Rajpura (North)
                                            ┼→ Bhiwandi (West)
                                            ┼→ Ahmedabad (West)
                                            ┼→ Bangalore (South)
                                            └→ Hyderabad (South)
```

- **Plant** = factory jahan product banta hai. 3 hain: BOM (Mumbai), AHM (Ahmedabad), KOL (Kolkata).
- **Hub** (Mother Hub) = bada central warehouse jahan plants se maal aata hai aur store hota hai. 2 hain: **MHW** (West — North/West/South India serve karta hai) aur **MHE** (East — East India).
- **CFA** (Clearing & Forwarding Agent) = regional warehouse jahan se maal aage dealers/customers tak jaata hai. 10 hain.

*(Units — SKU, kl, aur demand ka unit — neeche section **1.4** mein detail se samjhaya hai. Wo zaroor padho, ye sabse confusing part hota hai.)*

### 1.4 UNITS SAMAJHNA — SKU kya hai, kl kya hai, demand kis unit mein hai? (VERY IMPORTANT)

Ye section dhyan se padho, kyunki yahi sabse zyada confuse karta hai.

#### 🔹 SKU kya hai?
**SKU = Stock Keeping Unit = ek specific product, ek specific pack size mein.**

Ye ek "product ki pehchaan" hai. 100 SKUs hain (SKU_001 se SKU_100). Har SKU ka ek **pack size** hota hai jo batata hai wo physically kaise packed hai. Example:

| SKU | Pack size | Matlab (kaise packed hai) |
|---|---|---|
| SKU_001 | `20 X 900 ML` | ek carton/case mein **20 bottles**, har bottle **900 ml** ki |
| SKU_002 | `20 X 1 LT` | 20 bottles, har 1 litre |
| SKU_006 | `1 X 210 LT` | ek bada **drum**, 210 litre ka |
| SKU_026 | `1 X 180 KG` | ek grease ka drum, 180 **kg** (ye akela weight mein hai — neeche dekho) |

To "SKU_001" bolne ka matlab hai: "wo product jo 20×900ml packs mein aata hai".

#### 🔹 kl kya hai?
**kl = kilolitre = 1000 litre.** Ye ek **VOLUME** ka unit hai (kitna liquid, litre wala), **weight (kg) nahi**.

- 1 kl = 1,000 litre
- 0.5 kl = 500 litre
- 191.74 kl = 191,740 litre

Poore project mein — demand, production, transport, inventory — **sab kuch kl (volume) mein hai.** Kahin bhi "cases", "bottles", ya "kg" mein count nahi hota.

#### 🔹 Demand kis unit mein hai? (Aapka main sawaal)
**Demand ka unit = kl (kilolitre) = VOLUME. Kg nahi, bottles nahi, cases nahi — sirf kl (litre wala volume).**

Jab aap Exhibit J (January forecast) mein dekhte ho:
```
SKU_001   Kolkata   191.74
```
Iska matlab hai: **Kolkata warehouse ko January mein SKU_001 ka 191.74 kl chahiye = 191,740 litre.**

**Worked example (asli numbers ke saath) — taaki bilkul clear ho jaaye:**
- SKU_001 ka 1 case = 20 bottles × 900 ml = 18,000 ml = **18 litre = 0.018 kl**
- Kolkata ki demand = **191.74 kl** = 191,740 litre
- Matlab number of cases = 191,740 ÷ 18 = **~10,652 cases**

**PAR — hum model mein cases count nahi karte.** Hum sab kuch **kl (bulk volume)** mein rakhte hain. Pack size ("20 X 900 ML") ka use sirf ek cheez ke liye hai: ye decide karna ki product kaunsi **production line** pe banega (chhoti bottle line, ya bade drum line). Demand/production/stock — sab kl mein.

**Ise aise yaad rakho:** company sochti hai "kitna liquid (kl) chahiye", na ki "kitni bottles". Kyunki factory bhi liquid banati hai (litre mein), phir baad mein bottle/drum mein bharti hai.

#### 🔹 Ek exception — SKU_026 (grease, kg mein)
100 mein se **99 SKUs liquid hain (litre-based)**. Sirf **1 SKU (SKU_026) grease hai jo originally kg (180 kg) mein hai** — kyunki grease thick hota hai, use weight se naapte hain.

Model mein hum consistency ke liye ise bhi ek volume-equivalent (approx 195 kl-scale) maan lete hain, taaki saara data ek hi unit (kl) mein ho aur maths aasaan rahe. Ye humari ek chhoti assumption hai — agar judge poochhe to bata dena: *"99 products litre-based hain, 1 grease kg-based; humne use bade-drum ke volume-equivalent maan liya taaki poora model ek unit (kl) mein consistent rahe."*

#### 🔹 Summary table (ratt lo)
| Cheez | Unit | Matlab |
|---|---|---|
| Demand | **kl** | kitna volume chahiye (1 kl = 1000 L) |
| Production | **kl** | kitna volume banega |
| Transport | **₹ per kl** | 1 kl bhejne ka kharcha |
| Safety stock / ROP | **kl** | kitna buffer volume |
| Pack size | bottles × ml/litre | product physically kaise packed hai (sirf line decide karne ke liye) |
| SKU_026 (grease) | asli kg, model mein kl-equivalent | akela weight-based product |

### 1.3 Ye kyun mushkil hai?
Kyunki **demand > capacity** ho sakta hai (jitna log maangte hain, utna banane ki factory capacity nahi hai). To har decision ka ek cost hai:
- Zyada banao → production cost badhta hai
- Galat jagah se bhejo → transport cost badhta hai
- Kam banao → demand miss → penalty cost (customer naraz)

Humein wo combination dhoondhna hai jismein **total cost sabse kam** ho, aur important products (contractual wale) kabhi miss na hon.

---

## 🏆 PART 2: HUMEIN KYA DELIVER KARNA HAI? (3 Components)

Case 3 cheezein maangta hai:

### COMPONENT 1 — INVENTORY NORMS
Har SKU × CFA (aur SKU × Hub) ke liye batao:
- **Reorder Point (ROP)**: stock is level pe pahunche to naya order karo. (kl mein)
- **Safety Stock**: extra buffer stock demand/supply ki uncertainty ke liye.
- **Days of Cover**: ROP kitne din ki average demand ke barabar hai.

Rule: Hub ke liye service level 98% (matlab 98% chance ki stock out na ho). CFA ke liye tier ke hisaab se (A=98%, B=97%, C/D=92%).

### COMPONENT 2 — PRODUCTION & DISTRIBUTION PLAN
January 2026 ke liye exactly batao:
1. Har SKU ka kitna (kl mein, **25 kl ke batch** mein) kis plant pe banega.
2. Har plant se har hub ko kitna bhejenge.
3. Har hub se har CFA ko kitna bhejenge.
4. Har hub pe kitna safety stock rakhenge.
5. **Total cost** — production + transport + penalty (agar demand miss hui).

### COMPONENT 3 — PLANNING TOOL
Ek software jo:
- Inputs edit karne de (capacity, cost, demand) bina code chhue.
- Clear output de (plan, cost, kya miss hua).
- Agar demand puri na ho to **crash na kare** — bataye kitna miss hua aur kitna cost.
- Non-technical banda bhi chala sake.

**Evaluation 4 cheezon pe hoga (barabar weightage):** Analytical Rigor (maths sahi hai?), Solution Quality (answer accha hai?), Tool Quality (tool chalta hai?), Reasoning & Communication (aap explain kar sakte ho?).

---

## 📂 PART 3: PROJECT KE SAARE FILES (Folder structure)

Sab kuch `solution/` folder mein hai:

```
solution/
├── data/
│   └── raw_case_data.xlsx          ← Original case data (11 sheets). YAHI source of truth hai.
├── src/                            ← Saara Python code yahan hai
│   ├── data_loader.py              ← Excel padhta hai, saaf karke tables banata hai
│   ├── inventory_norms.py          ← COMPONENT 1 ka dimaag (safety stock, ROP formulas)
│   ├── optimizer.py                ← COMPONENT 2 ka dimaag (MILP optimization)
│   ├── pipeline.py                 ← Sabko jodta hai (loader + norms + optimizer)
│   ├── build_norms.py              ← Component 1 chalao → Excel output banao
│   └── build_plan.py               ← Component 2 chalao → Excel output banao
├── app.py                          ← COMPONENT 3: Streamlit tool (jo screen pe dikhta hai)
├── outputs/                        ← Yahan generated Excel files aate hain
│   ├── inventory_norms.xlsx        ← Component 1 ka result
│   └── production_distribution_plan.xlsx  ← Component 2 ka result
├── venv/                           ← Python ka virtual environment (libraries yahan install hain)
├── Methodology_and_Assumptions.md  ← COMPONENT 4: humne kya assume kiya, kyun
├── Production_Distribution_Plan_Report.md ← Deliverable #1 ka written report
├── README.md                       ← Chhoti technical readme (kaise chalayein)
└── PROJECT_GUIDE_HINGLISH.md       ← YE FILE (poori guide)
```

**Ek line mein har file:**
| File | Kaam |
|---|---|
| `raw_case_data.xlsx` | Input data — Castrol ne diya hua |
| `data_loader.py` | Excel → clean Python tables |
| `inventory_norms.py` | Safety stock / reorder point calculate |
| `optimizer.py` | Best production+distribution plan dhoondhta hai |
| `pipeline.py` | Sab modules ko ek saath chalane wala glue |
| `build_norms.py` | Component 1 ka output Excel banata hai |
| `build_plan.py` | Component 2 ka output Excel banata hai |
| `app.py` | Screen pe dikhne wala tool |
| `outputs/*.xlsx` | Final results |

---

## 🐍 PART 4: HAR PYTHON FILE DETAIL MEIN

### 4.1 `data_loader.py` — Data padhne wali file

**Kaam:** `raw_case_data.xlsx` ki 11 sheets ko padhta hai aur clean pandas tables (DataFrames) mein badalta hai. Baaki saari files yahi se data leti hain — koi bhi Excel ko directly nahi chhuti.

**Important functions:**
- `load_all()` — sab sheets padhta hai, ek dictionary return karta hai jismein har table hoti hai (plants, skus, sales, forecast, etc.).
- `parse_unit_volume_litres(pack_size)` — pack size string jaise `"20 X 900 ML"` se ek unit ka volume nikaalta hai (= 0.9 litre). Ye zaroori hai kyunki isi se pata chalta hai product kaunsi production line pe banega.
- `classify_line_type(litres)` — volume ke hisaab se line decide karta hai:
  - ≤1.5 litre → chhoti packs line (`<=1.5 LT`)
  - 1.5–5 → `3-5 LT`
  - 5–20 → `7-20 LT`
  - 20–50 → `50 LT`
  - >50 → `180-210 LT` (bade drums)
- `assign_sku_tiers(sales, service_levels)` — har SKU ko A/B/C/D tier deta hai. **Kaise?** Saare SKUs ko total sales ke hisaab se sort karo (bade se chhota). Jo top SKUs milke 50% volume banate hain = Tier A, agle 30% = B, agle 15% = C, baaki 5% = D. (Ye humari assumption hai — case ne tiers directly nahi diye.)

**Ek technical baat:** Excel sheets mein neeche footnote rows the (jaise "All production must be in 25kl batches") — ye code un footnote rows ko hata deta hai taaki wo data mein na ghusein.

### 4.2 `inventory_norms.py` — Component 1 ka dimaag

**Kaam:** Har SKU × CFA aur SKU × Hub ke liye safety stock, reorder point, days of cover nikaalta hai.

**Do main functions:**

**`compute_cfa_norms(...)`** — CFA level ke norms. Ye steps:

1. **Average daily demand** nikaalo (6 mahine ki sales se, /30 din).
2. **Demand ki uncertainty (sigma_d)** nikaalo — **ye important hai:** hum raw sales ki variation nahi lete, hum **forecast error** lete hain. Matlab: har mahine actual sales vs jo forecast tha, uska difference. Iska RMSE (root mean square error) = demand uncertainty.
   - *Kyun forecast error?* Kyunki January ka plan **forecast** pe based hai (humein future ka actual nahi pata). Safety stock is baat se bachata hai ki forecast galat nikle. Ye textbook-correct tareeka hai.
3. **Lead time (LT)** = production time + plant→hub transit + hub→CFA transit (Exhibit E se). Days mein.
4. **Lead time uncertainty (sigma_LT)** = √(production_variability² + transit_variability²).
5. **Safety Stock formula:**

   ```
   Safety Stock = z × √( LT × sigma_d²  +  demand² × sigma_LT² )
   ```
   - `z` = service level ka number (Tier A = 2.05, B = 1.88, C/D = 1.41). Zyada z = zyada safe = zyada stock.
   - Ye formula "variable demand + variable lead time" wala standard formula hai. Dono uncertainties ko combine karta hai.
6. **Reorder Point (ROP)** = (average daily demand × lead time) + safety stock.
7. **Days of Cover** = ROP ÷ average daily demand.

**`compute_hub_norms(...)`** — Hub level ke norms. CFA se thoda different:
- Service level **hamesha 98%** (case rule), tier se matlab nahi.
- Demand = us hub ke saare CFAs ki demand ka **jod** (aggregate).
- **Risk pooling:** kyunki CFAs independent hain, hub ki total uncertainty individual CFAs ke sum se **kam** hoti hai (variance add hote hain, phir √). Isliye hub ka safety stock alag se calculate hota hai, sabka jod nahi.
- Lead time yahan sirf plant→hub tak (kyunki hub apna order tab karta hai jab uska stock girta hai, aage CFA tak ka time matter nahi karta).

### 4.3 `optimizer.py` — Component 2 ka dimaag (sabse important)

**Kaam:** Best production + distribution plan dhoondhta hai jismein **total cost minimum** ho. Ye ek **MILP** (Mixed Integer Linear Program) hai — ek maths optimization jo lakhon possibilities mein se best chunta hai.

**Kya minimize karta hai (Objective)?**
```
Total Cost = Production cost
           + Plant→Hub transport cost
           + Hub→CFA transport cost
           + Unmet demand penalty (agar demand miss hui)
           + Hub safety-stock shortfall penalty
```

**Decision variables (jo optimizer decide karta hai):**
- `batches[plant, sku]` — har plant pe har SKU ke kitne 25kl batch banenge (integer — aadha batch nahi ban sakta).
- `plant_hub[plant, hub, sku]` — plant se hub kitna maal jaayega.
- `hub_cfa[hub, cfa, sku]` — hub se CFA kitna jaayega.
- `hub_ss_actual[hub, sku]` — hub pe kitna safety stock bacha.
- `unmet[cfa, sku]` — kitni demand puri nahi hui.

**Rules (Constraints) — plain language mein:**
1. **Plant capacity:** ek line pe jitne products banenge unka total us line ki monthly capacity se zyada nahi ho sakta.
2. **25 kl batch:** har production quantity 25 ka multiple honi chahiye (25, 50, 75...).
3. **Plant flow:** plant jitna bhejega utna banana padega (phantom maal nahi bhej sakta). `<=` isliye ki batch rounding ka thoda extra plant pe closing inventory ban jaata hai (waste nahi).
4. **Hub balance:** hub ke andar aaya maal (opening stock + plant se aaya) = bahar gaya (CFA ko) + safety stock jo bacha.
5. **CFA demand:** CFA ka opening stock + hub se aaya + unmet = total demand.

**Sabse smart trick — Unmet demand ko "crash" ki jagah "cost" banaya:**
Agar demand > capacity ho, to normal optimizer FAIL ho jaata (infeasible). Humne unmet demand ko ek variable banaya jiska ek **penalty cost** hai (Exhibit D se). Isse optimizer khud decide karta hai kaunsi demand miss karni hai (jiska penalty kam ho) — bilkul jaise ek insaan planner karta.

**Contractual SKUs ki protection:** jo SKUs contractual hain (key customer se pakka vaada), unke penalty ko **5× (5 guna)** kar diya. Isse optimizer inhe last mein miss karta hai — pehle sab non-contractual miss karega. (Isko hard rule nahi banaya kyunki agar capacity itni kam ho ki contractual bhi na ban sake, to model fail ho jaata; 5x penalty se same kaam ho jaata hai bina fail hue.)

**Output:** ek `PlanResult` object jismein production, routing, safety stock, unmet demand, aur cost breakdown hoti hai.

### 4.4 `pipeline.py` — Glue (jodne wali file)

**Kaam:** `data_loader` + `inventory_norms` + `optimizer` ko ek saath chalata hai. Isse app aur command-line scripts dono same logic use karte hain (kabhi mismatch nahi hoga).
- `load_inputs()` — data load karo.
- `run_norms(inputs)` — Component 1 chalao.
- `run_plan(inputs, hub_norms)` — Component 2 chalao.

### 4.5 `build_norms.py` aur `build_plan.py` — Output banane wali scripts
- `build_norms.py` chalao → `outputs/inventory_norms.xlsx` banega.
- `build_plan.py` chalao → `outputs/production_distribution_plan.xlsx` banega.
Ye command line se chalte hain (bina app khole), quick output ke liye.

### 4.6 `app.py` — Screen wala tool (Streamlit)
Ye wo file hai jo browser mein khulta hai. Detail Part 6 mein.

---

## 📥 PART 5: INPUT DATA FILE (`raw_case_data.xlsx`) — Har sheet, har column

Ye 11 sheets hain (Exhibits A–J). **Ye data Castrol ne diya — hum ise change nahi karte, sirf padhte hain.**

### Sheet: `A - Plants & Production` (Exhibit A)
Kaunsa plant kitna bana sakta hai aur kitne mein.
| Column | Matlab |
|---|---|
| Plant Code | BOM / AHM / KOL |
| Location | Mumbai / Ahmedabad / Kolkata |
| Line Capacity ≤1.5 LT | chhoti packs line ki monthly capacity (kl) |
| Line Capacity 3-5 LT | 3-5 litre line capacity |
| Line Capacity 7-20 LT | 7-20 litre line capacity |
| Line Capacity 50 LT | 50 litre line capacity |
| Line Capacity 180-210 LT | bade drums line capacity |
| Production Cost (₹/kl) | 1 kl banane ka kharcha. BOM=12000, AHM=12500, **KOL=9000 (sabse sasta)** |

### Sheet: `B - Plant-Hub Transport` (Exhibit B)
Plant se hub tak 1 kl bhejne ka kharcha (₹/kl).
| From Plant | To MHW | To MHE |
|---|---|---|
| Mumbai | 1000 (sasta) | 8000 (mehnga) |
| Ahmedabad | 4000 | 5000 |
| Kolkata | 10000 (mehnga) | 1100 (sasta) |
→ Isliye Mumbai West-hub ko feed karta hai, Kolkata East-hub ko.

### Sheet: `C -Hub-CFA Transport` (Exhibit C)
Hub se CFA tak 1 kl ka kharcha (₹/kl). Har CFA ke liye dono hubs ke rate.

### Sheet: `D -SKU Portfolio+Penalty matrix` (Exhibit D)
100 SKUs ki list.
| Column | Matlab |
|---|---|
| Product Name | SKU_001 ... SKU_100 |
| Pack size | jaise "20 X 900 ML" (20 bottles, har 900ml) |
| Penalty cost (per kL) | agar ye 1 kl miss hui to kitna nuksaan (₹) |
| Contractual? | "YES" = key customer se pakka vaada (isko miss mat karo) |

### Sheet: `E - Source + LT data` (Exhibit E)
Har SKU × CFA ke lead time (delivery time) details.
| Column | Matlab |
|---|---|
| Source | East / Rest of India (kaunse hub se aata hai historically) |
| LT (Plant to Hub) | plant se hub tak din |
| LT (Hub to CFA) | hub se CFA tak din |
| Production lead time | banane mein din |
| Production variability | production time kitna upar-neeche hota hai (din) |
| Transit lead variability | transport time kitna upar-neeche (din) |

### Sheet: `F - Service Levels` (Exhibit F)
Tier ke hisaab se target.
| Tier | Volume % | Target Fill Rate |
|---|---|---|
| A | 50% | 98% |
| B | 30% | 97% |
| C | 15% | 92% |
| D | 5% | 92% |

### Sheet: `G - Sales History` (Exhibit G)
Har SKU × CFA ki **actual sales** — Jul-25 se Dec-25 (6 mahine). Isse average demand aur variation nikalte hain.

### Sheet: `H - Forecast History` (Exhibit H)
Same 6 mahine ka **forecast** (jo predict kiya tha). Actual (G) se compare karke **forecast error** nikalte hain → safety stock.

### Sheet: `I - Expected opening Inventory` (Exhibit I)
January shuru hone pe har jagah (CFA + Hub) kitna stock pehle se pada hai. Ye demand se ghata dete hain (jitna pehle se hai utna kam banana padega).

### Sheet: `J - Jan Forecast` (Exhibit J)
**January 2026 ki predicted demand** — har SKU × CFA. **Yahi wo demand hai jiske against hum plan banate hain.**

---

## 📤 PART 6: OUTPUT FILES — Har sheet, har column

### File: `outputs/inventory_norms.xlsx` (Component 1 ka result)

**Sheet `CFA Norms` (957 rows)** — har SKU × CFA ke norms:
| Column | Matlab (kya represent karta hai) |
|---|---|
| `sku` | product |
| `cfa` | warehouse |
| `avg_monthly_demand_kl` | mahine ki average demand |
| `std_monthly_demand_kl` | raw sales variation (diagnostic) |
| `avg_daily_demand_kl` | roz ki average demand (÷30) |
| `std_daily_demand_kl_raw_sales` | raw daily variation (sirf comparison ke liye) |
| `forecast_error_rmse_monthly` | forecast kitna galat tha (RMSE) |
| `std_daily_demand_kl` | **actual demand uncertainty** (forecast error se, daily) — safety stock isi se banta hai |
| `hub` | is CFA ka source hub |
| `total_lt_days` | total lead time (din) |
| `lt_std_days` | lead time uncertainty (din) |
| `tier` | A/B/C/D |
| `target_fill_rate` | 0.98/0.97/0.92 |
| `z_score` | service level ka number |
| **`safety_stock_kl`** | **buffer stock (kl)** — deliverable ka main number |
| **`reorder_point_kl`** | **ROP — is level pe order karo (kl)** |
| **`days_of_cover`** | **ROP kitne din chalega** |
| `penalty_per_kl` | miss karne ka nuksaan |
| `contractual` | True/False |
| `line_type` | production line |

**Sheet `Hub Norms` (151 rows)** — SKU × Hub ke norms (98% service level). Same columns lekin hub level pe (`pooled_std_daily_demand_kl` = risk-pooled uncertainty).

**Sheet `SKU Tiers` (100 rows)** — har SKU ka tier (A/B/C/D).

### File: `outputs/production_distribution_plan.xlsx` (Component 2 ka result)

**Sheet `Production Plan`** — `sku, plant, qty_kl`: har SKU har plant pe kitna banega (25 ke multiple mein).

**Sheet `Plant-Hub Routing`** — `sku, plant, hub, qty_kl`: kis plant se kis hub kitna jaayega.

**Sheet `Hub-CFA Routing`** — `sku, hub, cfa, qty_kl`: kis hub se kis CFA kitna jaayega.

**Sheet `Hub Safety Stock`** — `sku, hub, target_kl, actual_kl, shortfall_kl`: hub pe safety stock ka target vs jitna actual bacha vs kitna kam pada.

**Sheet `Unmet Demand`** — `sku, cfa, qty_kl, penalty_per_kl, contractual, cost`: **kaunsi demand puri nahi hui** aur uska cost. (Base plan mein ye 0 hai — sab puri hui.)

**Sheet `Cost Summary`** — total cost ka breakdown:
| Item | Base plan ka value |
|---|---|
| production_cost | ₹7.42 crore |
| plant_hub_transport_cost | ₹75 lakh |
| hub_cfa_transport_cost | ₹1.39 crore |
| unmet_demand_penalty_cost | ₹0 |
| hub_safety_stock_shortfall_cost | ₹19 lakh |
| **total_cost** | **₹9.75 crore** |
| total_unmet_volume_kl | 0 kl |
| total_demand_kl | 8,109.7 kl |

---

## 🖥️ PART 7: TOOL (app.py) — Screen pe kya dikhta hai

Tool browser mein khulta hai: **http://localhost:8899**

### Left side — Sidebar (Scenario Inputs)
Yahan aap **inputs edit** kar sakte ho (ye wahi cheez hai jo judges "changed input" dekar test karenge):
- **Plant capacities & production cost** — table jise directly edit kar sakte ho.
- **Plant → Hub transport cost** — freight rate edit.
- **Hub → CFA transport cost** — freight rate edit.
- **Jan-2026 demand forecast** — demand edit, ya poora naya CSV upload karo.
- **Solver time limit** — slider (kitne second tak optimizer chale, 60-120 kaafi hai).
- **▶ Run Plan** button — dabao, sab dobara calculate hoga.
- **Reset to original case data** — wapas original data pe le aata hai.

### Top — 4 Tabs

**Tab 1: 📦 Inventory Norms**
- CFA-level table: har SKU × CFA ka safety stock, ROP, days of cover.
- Hub-level table: 98% service level ke norms.
- "Download CSV" button — Excel mein le jaane ke liye.

**Tab 2: 🏭 Production & Distribution Plan**
- Upar 5 bade numbers (metrics): Production Cost, Plant→Hub Transport, Hub→CFA Transport, Unmet Demand Penalty, **Total Cost**.
- **Overall Fill Rate** — kitni % demand puri hui (base plan = 100%).
- **Unmet Demand** section — agar sab puri hui to green "All demand met". Agar nahi, to red table jismein kaunsi SKU × CFA kitni miss hui + cost (penalty ke hisaab se sorted).
- **Production Plan** table — kaunsa SKU kis plant pe kitna.
- **Plant → Hub** aur **Hub → CFA Routing** tables.
- **Hub Safety Stock** table — target vs actual.
- **Cost Breakdown pie chart** — cost kis cheez mein gaya.

**Tab 3: 🗺️ Network Map**
- India ka map jismein lines dikhti hain: **green lines = plant→hub**, **blue lines = hub→CFA**. Line jitni moti, utna zyada maal us route pe.

**Tab 4: 📊 Raw Data**
- Current inputs dikhata hai (jo abhi set hain).

---

## ▶️ PART 8: KAISE CHALAYEIN (Run karna)

### Ek baar setup (agar naya computer ho):
```bash
cd solution
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy scipy openpyxl pulp streamlit plotly xlsxwriter
```

### Tool kholna (main demo ke liye):
```bash
cd solution
source venv/bin/activate
streamlit run app.py
```
Browser khud khul jaayega. Ya `http://localhost:8501` (ya jo port dikhe) kholo.

### Sirf Excel outputs banane (bina tool khole):
```bash
cd solution/src
../venv/bin/python3 build_norms.py    # Component 1 → inventory_norms.xlsx
../venv/bin/python3 build_plan.py     # Component 2 → production_distribution_plan.xlsx
```

---

## 🧪 PART 9: NAYE DATA PE KAISE TEST KAREIN (Bahut important — demo day ke liye)

Demo day pe judges aapko **30 min pehle naya data** denge (capacity change, demand change, ya cost change). Aapko tool chala ke naya plan dikhana hai. **Do tareeke:**

### Tareeka 1: Tool ke andar edit karo (sabse easy — demo ke liye best)
1. Tool khol lo (`streamlit run app.py`).
2. Left sidebar mein jo change karna hai us section ko kholo:
   - Capacity change → "Plant capacities & production cost" table mein number badlo.
   - Transport cost change → transport cost table edit karo.
   - Demand change → "Jan-2026 demand" table edit karo, ya naya CSV upload karo.
3. **▶ Run Plan** dabao.
4. Naya plan, nayi cost, naya unmet demand — sab automatically update.

### Tareeka 2: Naya CSV upload (agar demand bahut saara badla ho)
CSV mein 3 columns honi chahiye: `sku`, `cfa`, `jan26_forecast_kl`. Example:
```
sku,cfa,jan26_forecast_kl
SKU_001,Kolkata,250.5
SKU_001,Guwahati,30.0
...
```
Sidebar → "Jan-2026 demand" → "Replace with CSV" → file choose karo → Run Plan.

### Tareeka 3: Poora naya Excel data (agar puri file badal jaye)
1. Naye Excel ko `solution/data/raw_case_data.xlsx` ke naam se save karo (purani ko backup rakh lo).
2. Sheet ke naam aur column order **bilkul same** hone chahiye (warna loader confuse hoga).
3. Tool restart karo ya `build_plan.py` chalao.

**⚠️ Demo tip:** Tareeka 1 sabse safe hai. Judges ke number tool mein type karo, Run Plan, done. CSV upload ya file replace tab jab bahut zyada data ek saath badle.

### Test karke kaise pata chale sahi chala?
- Status "Optimal" dikhna chahiye (crash nahi).
- Agar capacity kam ki → cost badhega, shayad thoda unmet aayega, par contractual SKUs safe rahenge.
- Agar demand badhai → jab tak capacity hai puri hogi, warna unmet demand table mein dikhega (penalty ke hisaab se sorted).

---

## 🧠 PART 10: ASSUMPTIONS JO AAPKO DEFEND KARNI HAIN (Q&A ke liye)

Judges poochenge "aisa kyun kiya?" Ye teen sabse important hain — inhe ratt lo:

1. **Tiers volume se banaye (A=top 50% volume, etc.):** Case ne 100 SKUs ke tiers directly nahi diye, sirf tier ki definition di ("A = highest volume"). To humne sales volume ke cumulative share se tier assign kiye. **Defense:** "Exhibit F kehta hai tiers volume pe based hain, to humne 6-month sales se derive kiye."

2. **Contractual SKU ko 5× penalty:** Case kehta hai contractual miss karna "normal lost margin se kahin zyada" nuksaan hai, par exact number nahi diya. Humne 5× multiplier lagaya. **Defense:** "Ye ek tunable parameter hai (`CONTRACTUAL_PENALTY_MULTIPLIER`), business jaisa chahe adjust kar sakta hai. 5× isliye ki reputational + contractual breach cost lost-margin se kaafi zyada hota hai."

3. **Safety stock forecast error se banaya (raw sales se nahi):** **Defense:** "January ka plan forecast pe based hai, actual pe nahi. Safety stock forecast galat hone se bachata hai — isliye forecast error (RMSE) sahi input hai, textbook (Silver-Peterson-Pyke) bhi yahi kehta hai."

4. **Unmet demand ko penalty banaya, hard constraint nahi:** **Defense:** "Agar demand > capacity ho aur hum use hard rule banayein, to model FAIL ho jaata (koi answer nahi). Penalty se model hamesha ek actionable plan deta hai aur khud sabse kam-nuksaan wali demand miss karta hai — jaise ek insaan planner."

5. **Batch surplus plant pe chhoda (`<=`):** **Defense:** "25kl batch rule ki wajah se thoda extra ban jaata hai. Use plant pe closing inventory (asset) ki tarah rakha — hub tak bhejne mein freight lagta bina fayde ke. Humne `==` bhi test kiya, wo strictly mehenga nikla."

---

## 📖 PART 11: GLOSSARY (Shabd-kosh)

| Term | Matlab |
|---|---|
| SKU | ek specific product pack (SKU_001 se 100) |
| CFA | regional warehouse (10 hain) |
| Hub / Mother Hub | central bada warehouse (MHW, MHE) |
| Plant | factory (BOM, AHM, KOL) |
| kl | kilolitre = 1000 litre |
| Lead time | order dene se milne tak ka total time (din) |
| Safety Stock | uncertainty ke liye extra buffer stock |
| Reorder Point (ROP) | stock is level pe aaye to naya order karo |
| Days of Cover | stock kitne din ki demand ke barabar hai |
| Fill Rate | kitni % demand puri hui |
| Service Level | stock-out na hone ka probability (98% etc.) |
| Forecast Error | actual sales vs forecast ka difference |
| RMSE | Root Mean Square Error — average galti ka measure |
| z-score | service level ko number mein badalne wala (98% = 2.05) |
| MILP | Mixed Integer Linear Programming — optimization technique |
| Objective | jo minimize/maximize karna hai (yahan: total cost) |
| Constraint | rule jo maanna zaroori hai (capacity, batch, etc.) |
| Penalty cost | demand miss karne ka nuksaan (₹/kl) |
| Contractual SKU | key customer se pakka supply vaada wala product |
| Risk pooling | kai independent demands milne se total uncertainty kam hoti hai |
| Batch (25 kl) | production ek baar mein 25kl ke multiple mein hota hai |
| Solver / HiGHS | wo software jo MILP solve karta hai (PuLP library ke through) |
| Streamlit | Python library jisse browser wala tool banta hai |

---

## ✅ PART 12: PROJECT KA STATUS (Kya ho gaya, kya baaki)

**Ho gaya (verified — chalke check kiya):**
- ✅ Component 1: Inventory norms (957 CFA + 151 Hub rows)
- ✅ Component 2: Production plan (₹9.75 crore, 100% demand met)
- ✅ Component 3: Tool chalta hai, 4 tarah ke input changes pe test kiya
- ✅ Component 4: Methodology doc
- ✅ Plan report (deliverable #1)

**Baaki hai (aapke saath karenge):**
- ⬜ Aap khud tool browser mein khol ke dekho (map/charts sahi dikhte hain?)
- ⬜ Presentation slide deck banana
- ⬜ Methodology doc mein final numbers daalna
- ⬜ (Optional) Scenario comparison feature (before/after cost side-by-side)
- ⬜ Q&A practice (upar Part 10 wali assumptions)

---

*Koi bhi cheez samajh na aaye to file `Methodology_and_Assumptions.md` aur `README.md` bhi padho. Ye project 4 components ko cover karta hai jo Castrol ne maange. All the best! 🚀*
