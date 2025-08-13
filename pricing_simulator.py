import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import json
from openai import OpenAI

# =====================
# Setup
# =====================
st.set_page_config(page_title="Professional Cost-Plus Pricing Studio", page_icon=":briefcase:", layout="centered")
client = OpenAI(api_key=st.secrets["openai"]["api_key"])  # Secrets-managed API key

# Background + UI polish
st.markdown(
    """
    <style>
      .stApp { background: radial-gradient(circle at 50% 40%, #0e3d5a 0%, #175a80 55%, #e7f6ff 100%); min-height: 100vh; }
      .note { background:#eef8ff; border-left:5px solid #0ea5e9; padding:0.6rem 0.8rem; border-radius:6px; }
      /* Tighten space after description */
      div[data-testid="stTextArea"] { margin-bottom: 0px; }
      /* Make utility buttons single line and wide */
      div[data-testid="column"] button { white-space: nowrap; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style='text-align:center; font-size:34px; font-weight:800; color:#0ea5e9;'>
  Professional Cost-Plus Pricing Studio
</div>
<div style='text-align:center; color:#0f2f44;'>Calculate unit economics, structure pricing, and stress-test decisions.</div>
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

product_desc_help = (
    "Provide a precise, professional description including materials, process, unique value proposition, and expected use-cases. "
    "Example: 'We produce 8-inch woven paracord bracelets with stainless-steel clasps for outdoor enthusiasts. Each unit uses 3 meters of Type III 550 paracord, "
    "is assembled using a jig for consistent tension, and is packaged in a recyclable kraft sleeve. Target customers are middle-school students and hikers "
    "seeking durable, customizable accessories. Production occurs in small batches of 25 to maintain quality control.'"
)
product_desc = st.text_area(
    "Detailed product description (be specific)",
    value=st.session_state.get("product_desc", ""),
    help=product_desc_help,
)

# Targeting and location
colT1, colT2 = st.columns(2)
with colT1:
    target_audience = st.text_input("Target audience (segments/personas)", value=st.session_state.get("target_audience", ""))
with colT2:
    city = st.text_input("City", value=st.session_state.get("city", ""))
state = st.text_input("State/Region", value=st.session_state.get("state", ""))

additional_info = st.text_area("Additional information (constraints, objectives, differentiators)", value=st.session_state.get("additional_info", ""))

# =====================
# Section 1: Cost of Goods Sold (COGS)
# =====================
st.markdown("---")
st.header("Cost of Goods Sold (COGS)")

# Dynamic Raw Materials
st.markdown("### Raw materials per unit")
add_mat_col = st.columns([3,7])[0]
if add_mat_col.button("Add material +", use_container_width=True):
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

st.metric("Materials subtotal (per unit)", f"${materials_total:.2f}")

# =====================
# Section 2: Variable Costs (selling and distribution per unit)
# =====================
st.markdown("---")
st.header("Variable Costs")

colV1, colV2 = st.columns(2)
with colV1:
    shipping_unit = st.number_input("Outbound shipping/delivery per unit ($)", min_value=0.0, value=st.session_state.get("shipping_unit", 3.50), step=0.10)
with colV2:
    variable_selling = st.number_input("Other variable selling expense per unit ($)", min_value=0.0, value=st.session_state.get("variable_selling", 0.00), step=0.10, help="Samples, small discounts, per-transaction incidentals")

variable_total = shipping_unit + variable_selling
st.metric("Variable costs subtotal (per unit)", f"${variable_total:.2f}")

# =====================
# Section 3: Production Costs (conversion costs and capital amortization)
# =====================
st.markdown("---")
st.header("Production Costs")

# Direct labor cost per unit (no hourly fields)
colP1, colP2 = st.columns(2)
with colP1:
    labor_unit = st.number_input("Direct labor cost per unit ($)", min_value=0.0, value=float(st.session_state.get("labor_unit", 0.00)), step=0.10)
with colP2:
    packaging_unit = st.number_input("Packaging cost per unit ($)", min_value=0.0, value=st.session_state.get("packaging_unit", 0.50), step=0.05)

st.markdown("### Machinery and tools (amortized per unit)")
add_eqp_col = st.columns([3,7])[0]
if add_eqp_col.button("Add equipment +", use_container_width=True):
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

production_total = labor_unit + packaging_unit + equipment_unit_total

colPS1, colPS2, colPS3 = st.columns(3)
colPS1.metric("Labor per unit", f"${labor_unit:.2f}")
colPS2.metric("Packaging per unit", f"${packaging_unit:.2f}")
colPS3.metric("Equipment per unit", f"${equipment_unit_total:.2f}")

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
fig.update_traces(textinfo='label+percent')
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
        "target_audience": target_audience,
        "city": city,
        "state": state,
        "additional_info": additional_info,
        "labor_minutes_per_unit": cycle_minutes,
        "materials": st.session_state.materials,
        "equipment": st.session_state.equipment,
        "labor_per_unit": labor_unit,
        "packaging_per_unit": packaging_unit,
        "shipping_per_unit": shipping_unit,
        "other_variable_per_unit": variable_selling,
        "unit_cost": unit_cost,
        "target_margin_pct": margin_pct,
        "suggested_price": suggested_price,
        "gross_profit_per_unit": unit_gross_profit,
        "n_customers": n_customers,
    }

    prompt = f"""
    Act as a pricing and go-to-market advisor. Evaluate the unit economics and market fit using the full context provided. Incorporate location (city/state) and target audience in all judgments.

    Data: {json.dumps(payload)}

    Tasks:
    1) Provide a concise competitiveness assessment in professional vocabulary.
    2) Return exactly {12 if n_customers>=1000 else 8} concise customer-style comments tailored to the stated audience and location, each with a practical improvement.
    3) Provide top 2 strengths and top 2 weaknesses with integer percentages that sum to 100 for each list, plus an "Other" value.
    4) Provide a star rating distribution (1–5 stars) for {n_customers} simulated reviews that aligns with the analysis.

    Return valid JSON only with this schema:
    {{
      "competitive_summary": "...",
      "comments": ["..."],
      "best_aspects": {{"aspect1": "...", "percentage1": 60, "aspect2": "...", "percentage2": 30, "other": 10}},
      "worst_aspects": {{"aspect1": "...", "percentage1": 50, "aspect2": "...", "percentage2": 35, "other": 15}},
      "star_ratings": {{"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}}
    }}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": prompt}],
            max_tokens=1600
        )
        raw = resp.choices[0].message.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)

        st.markdown("### Executive view")
        st.info(data.get("competitive_summary", ""))

        # Strengths/Weaknesses tables
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

        # Customer comments
        comments = data.get("comments", [])
        st.markdown("### Customer commentary")
        if comments:
            for c in comments:
                st.info(f"🗣️ {c}")
        else:
            st.write("No comments available.")

        # Detailed metrics table
        metrics_rows = [
            {"Metric": "COGS (materials)", "Value": round(materials_total, 2)},
            {"Metric": "Variable costs", "Value": round(variable_total, 2)},
            {"Metric": "Production costs", "Value": round(production_total, 2)},
            {"Metric": "— Labor per unit", "Value": round(labor_unit, 2)},
            {"Metric": "— Packaging per unit", "Value": round(packaging_unit, 2)},
            {"Metric": "— Equipment per unit", "Value": round(equipment_unit_total, 2)},
            {"Metric": "Unit cost (total)", "Value": round(unit_cost, 2)},
            {"Metric": "Target margin (%)", "Value": int(margin_pct)},
            {"Metric": "Suggested price", "Value": round(suggested_price, 2)},
            {"Metric": "Gross profit per unit", "Value": round(unit_gross_profit, 2)},
        ]
        metrics_df = pd.DataFrame(metrics_rows)
        st.markdown("### Detailed financials")
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        # Star ratings pie chart
        stars = data.get("star_ratings", {}) or {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        # Ensure counts sum to n_customers; if percentages given, convert
        total_reported = sum(int(v) for v in stars.values()) if all(str(v).isdigit() for v in stars.values()) else 0
        if total_reported != int(n_customers):
            # Normalize to n_customers
            vals = np.array([max(0, int(stars.get(str(k), 0))) for k in range(1,6)], dtype=int)
            s = vals.sum()
            if s == 0:
                vals = np.array([0,0,0,int(n_customers*0.4), int(n_customers*0.6)], dtype=int)
                s = vals.sum()
            # Adjust last bucket to hit n_customers
            if s != n_customers:
                diff = int(n_customers) - int(s)
                vals[-1] += diff
            stars = {str(i+1): int(vals[i]) for i in range(5)}
        star_df = pd.DataFrame({"Stars": ["1★","2★","3★","4★","5★"], "Count": [stars["1"], stars["2"], stars["3"], stars["4"], stars["5"]]})
        star_fig = px.pie(star_df, names="Stars", values="Count", title=f"Star Ratings Distribution ({int(n_customers)} reviews)")
        star_fig.update_traces(textinfo='label+percent')
        st.plotly_chart(star_fig, use_container_width=True)

    except Exception:
        st.error("AI response could not be parsed. Here is the raw output:")
        st.code(locals().get("raw", "<no raw output>"))

st.markdown("---")
st.caption("Built with Streamlit and OpenAI • Structured around COGS, variable costs, and production costs.")

