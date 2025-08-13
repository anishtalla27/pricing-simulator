import streamlit as st
import plotly.express as px
import pandas as pd
import json
from datetime import date
from openai import OpenAI

# =====================
# Setup
# =====================
st.set_page_config(page_title="Professional Cost-Plus Pricing Studio", page_icon=":briefcase:", layout="centered")
client = OpenAI(api_key=st.secrets["openai"]["api_key"])  # Secrets-managed API key

# Background style
st.markdown(
    """
    <style>
      .stApp { background: radial-gradient(circle at 50% 40%, #0e3d5a 0%, #175a80 55%, #e7f6ff 100%); min-height: 100vh; }
      .note { background:#eef8ff; border-left:5px solid #0ea5e9; padding:0.6rem 0.8rem; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style='text-align:center; font-size:34px; font-weight:800; color:#0ea5e9;'>
  Professional Cost-Plus Pricing Studio
</div>
<div style='text-align:center; color:#0f2f44;'>A rigorous tool for calculating unit economics and stress-testing pricing decisions.</div>
""",
    unsafe_allow_html=True,
)
st.markdown("---")

# =====================
# Session state for dynamic inputs
# =====================
if "materials" not in st.session_state:
    st.session_state.materials = [{"name": "Primary Material", "unit_cost": 2.00}]
if "equipment" not in st.session_state:
    st.session_state.equipment = [{"name": "Starter Tool", "cap_units": 200, "total_cost": 25.0}]

# =====================
# Product basics
# =====================
st.subheader("Product Definition")
colA, colB = st.columns(2)
with colA:
    product_name = st.text_input("Product name", value=st.session_state.get("product_name", ""))
with colB:
    cycle_minutes = st.number_input("Direct labor time per unit (minutes)", min_value=0, value=st.session_state.get("cycle_minutes", 15))

product_desc = st.text_area("Concise product description", value=st.session_state.get("product_desc", ""), placeholder="Handcrafted bracelet with premium charms.")

st.markdown("<div class='note'>Labor time converts to a per-unit labor cost using your target hourly compensation.</div>", unsafe_allow_html=True)

# =====================
# Section 1: Cost of Goods Sold (COGS)
# =====================
st.markdown("---")
st.header("Cost of Goods Sold (COGS)")

# Dynamic Raw Materials
st.markdown("### Raw materials per unit")
add_mat, _ = st.columns([1,5])
if add_mat.button("Add material"):
    st.session_state.materials.append({"name": "", "unit_cost": 0.0})

mat_rows = []
for i, item in enumerate(st.session_state.materials):
    c1, c2 = st.columns([3,2])
    name = c1.text_input(f"Material {i+1} name", value=item["name"], key=f"mat_name_{i}")
    cost = c2.number_input(f"Material {i+1} cost per unit ($)", min_value=0.0, value=float(item["unit_cost"]), step=0.01, key=f"mat_cost_{i}")
    st.session_state.materials[i] = {"name": name, "unit_cost": cost}
    mat_rows.append({"Material": name or f"Material {i+1}", "$/unit": round(cost, 2)})

materials_df = pd.DataFrame(mat_rows) if mat_rows else pd.DataFrame(columns=["Material", "$/unit"]) 
materials_total = float(sum([m["unit_cost"] for m in st.session_state.materials]))

st.markdown("### COGS subtotal")
st.metric("Materials subtotal (per unit)", f"${materials_total:.2f}")

# =====================
# Section 2: Variable Costs (selling and distribution per unit)
# =====================
st.markdown("---")
st.header("Variable Costs")

colV1, colV2 = st.columns(2)
with colV1:
    shipping_unit = st.number_input("Outbound shipping or delivery per unit ($)", min_value=0.0, value=st.session_state.get("shipping_unit", 3.50), step=0.10)
with colV2:
    variable_selling = st.number_input("Other variable selling expense per unit ($)", min_value=0.0, value=st.session_state.get("variable_selling", 0.00), step=0.10, help="Samples, small discounts, event ticket per-unit allocation")

variable_total = shipping_unit + variable_selling

st.metric("Variable costs subtotal (per unit)", f"${variable_total:.2f}")

# =====================
# Section 3: Production Costs (conversion costs and capital amortization)
# =====================
st.markdown("---")
st.header("Production Costs")

colP1, colP2 = st.columns(2)
with colP1:
    hourly_wage = st.number_input("Target hourly compensation ($/hour)", min_value=0.0, value=st.session_state.get("hourly_wage", 12.0), step=0.50)
    labor_unit = (cycle_minutes / 60.0) * hourly_wage
with colP2:
    packaging_unit = st.number_input("Packaging cost per unit ($)", min_value=0.0, value=st.session_state.get("packaging_unit", 0.50), step=0.05)

other_conversion = st.number_input("Other conversion cost per unit ($)", min_value=0.0, value=st.session_state.get("other_conversion", 0.20), step=0.05, help="Electricity, consumables, cleaning")

st.markdown("### Machinery and tools (amortized per unit)")
add_eqp, _ = st.columns([1,5])
if add_eqp.button("Add equipment"):
    st.session_state.equipment.append({"name": "", "cap_units": 100, "total_cost": 0.0})

eq_rows = []
for j, eq in enumerate(st.session_state.equipment):
    c1, c2, c3 = st.columns([3,2,2])
    ename = c1.text_input(f"Equipment {j+1} name", value=eq["name"], key=f"eq_name_{j}")
    cap = c2.number_input(f"Capacity units {j+1}", min_value=1, value=int(eq["cap_units"]), step=1, key=f"eq_cap_{j}")
    tcost = c3.number_input(f"Total cost {j+1} ($)", min_value=0.0, value=float(eq["total_cost"]), step=1.0, key=f"eq_cost_{j}")
    st.session_state.equipment[j] = {"name": ename, "cap_units": cap, "total_cost": tcost}
    per_unit = (tcost / cap) if cap > 0 else 0.0
    eq_rows.append({"Equipment": ename or f"Equipment {j+1}", "Per-unit amortization ($)": round(per_unit, 4)})

equipment_df = pd.DataFrame(eq_rows) if eq_rows else pd.DataFrame(columns=["Equipment", "Per-unit amortization ($)"])
equipment_unit_total = float(sum([(e["total_cost"] / e["cap_units"]) for e in st.session_state.equipment if e["cap_units"] > 0]))

production_total = labor_unit + packaging_unit + other_conversion + equipment_unit_total

st.markdown("### Production subtotal")
colPS1, colPS2, colPS3, colPS4 = st.columns(4)
colPS1.metric("Labor per unit", f"${labor_unit:.2f}")
colPS2.metric("Packaging per unit", f"${packaging_unit:.2f}")
colPS3.metric("Other conversion per unit", f"${other_conversion:.2f}")
colPS4.metric("Equipment per unit", f"${equipment_unit_total:.2f}")

# =====================
# Pricing
# =====================
st.markdown("---")
st.header("Pricing and Margin")

margin_pct = st.slider("Target gross margin (%)", 5, 95, value=40, step=1)

unit_cost = materials_total + variable_total + production_total
suggested_price = unit_cost * (1 + margin_pct / 100)
unit_gross_profit = suggested_price - unit_cost

colR1, colR2 = st.columns(2)
with colR1:
    st.metric("Comprehensive unit cost", f"${unit_cost:.2f}")
    st.metric("Suggested price", f"${suggested_price:.2f}")
with colR2:
    st.metric("Target margin", f"{margin_pct}%")
    st.metric("Gross profit per unit", f"${unit_gross_profit:.2f}")

# =====================
# Visuals
# =====================
st.markdown("### Cost composition")
comp_df = pd.DataFrame([
    {"Category": "COGS (materials)", "$/unit": round(materials_total, 2)},
    {"Category": "Variable costs", "$/unit": round(variable_total, 2)},
    {"Category": "Production costs", "$/unit": round(production_total, 2)},
])
fig = px.pie(comp_df, names="Category", values="$/unit", title="Unit cost breakdown")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Details")
cols = st.columns(2)
with cols[0]:
    st.caption("Materials detail")
    st.dataframe(materials_df, use_container_width=True, hide_index=True)
with cols[1]:
    st.caption("Equipment amortization detail")
    st.dataframe(equipment_df, use_container_width=True, hide_index=True)

# =====================
# AI analysis
# =====================
st.markdown("---")
st.header("AI Commercial Analysis")

n_customers = st.slider("Number of simulated customer opinions", 100, 5000, 1000, step=100)

if st.button("Generate AI Analysis"):
    payload = {
        "product_name": product_name,
        "product_description": product_desc,
        "labor_minutes_per_unit": cycle_minutes,
        "hourly_compensation": hourly_wage,
        "materials": st.session_state.materials,
        "equipment": st.session_state.equipment,
        "packaging_per_unit": packaging_unit,
        "other_conversion_per_unit": other_conversion,
        "shipping_per_unit": shipping_unit,
        "other_variable_per_unit": variable_selling,
        "unit_cost": unit_cost,
        "target_margin_pct": margin_pct,
        "suggested_price": suggested_price,
        "gross_profit_per_unit": unit_gross_profit,
        "n_customers": n_customers,
    }

    prompt = f"""
    Act as a pricing and go-to-market advisor. Evaluate the following unit economics and propose actions to improve profitability without destroying demand.

    Data: {json.dumps(payload)}

    Tasks:
    1) Provide a concise competitiveness assessment in professional vocabulary.
    2) Return exactly {12 if n_customers>=1000 else 8} crisp customer-style comments that include practical improvements.
    3) Provide top 2 strengths and top 2 weaknesses with integer percentages that sum to 100 for each list, plus an "Other" value.

    Return valid JSON only with this schema:
    {{
      "competitive_summary": "...",
      "comments": ["..."],
      "best_aspects": {{"aspect1": "...", "percentage1": 60, "aspect2": "...", "percentage2": 30, "other": 10}},
      "worst_aspects": {{"aspect1": "...", "percentage1": 50, "aspect2": "...", "percentage2": 35, "other": 15}}
    }}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": prompt}],
            max_tokens=1400
        )
        raw = resp.choices[0].message.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)

        st.markdown("### Executive view")
        st.info(data.get("competitive_summary", ""))

        best = data.get("best_aspects", {})
        worst = data.get("worst_aspects", {})

        best_table = pd.DataFrame([
            {"Aspect": best.get("aspect1", "N/A"), "Percent of customers (%)": best.get("percentage1", "N/A")},
            {"Aspect": best.get("aspect2", "N/A"), "Percent of customers (%)": best.get("percentage2", "N/A")},
            {"Aspect": "Other", "Percent of customers (%)": best.get("other", "N/A")},
        ])
        worst_table = pd.DataFrame([
            {"Aspect": worst.get("aspect1", "N/A"), "Percent of customers (%)": worst.get("percentage1", "N/A")},
            {"Aspect": worst.get("aspect2", "N/A"), "Percent of customers (%)": worst.get("percentage2", "N/A")},
            {"Aspect": "Other", "Percent of customers (%)": worst.get("other", "N/A")},
        ])

        st.markdown("### Strengths")
        st.dataframe(best_table, use_container_width=True, hide_index=True)
        st.markdown("### Weaknesses")
        st.dataframe(worst_table, use_container_width=True, hide_index=True)

        comments = data.get("comments", [])
        st.markdown("### Customer commentary")
        if comments:
            for c in comments:
                st.info(f"🗣️ {c}")
        else:
            st.write("No comments available.")

    except Exception:
        st.error("AI response could not be parsed. Here is the raw output:")
        st.code(locals().get("raw", "<no raw output>"))

st.markdown("---")
st.caption("Built with Streamlit and OpenAI • Focus on fundamentals: COGS, variable costs, production costs.")

