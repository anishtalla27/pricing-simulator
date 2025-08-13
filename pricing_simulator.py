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
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# Background + UI polish
st.markdown(
    """
    <style>
      .stApp { background: radial-gradient(circle at 50% 40%, #0e3d5a 0%, #175a80 55%, #e7f6ff 100%); min-height: 100vh; }
      .note { background:#eef8ff; border-left:5px solid #0ea5e9; padding:0.6rem 0.8rem; border-radius:6px; }
      div[data-testid="stTextArea"] { margin-bottom: 0px; }
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
<div style='text-align:center; color:#13d0ff;'>Calculate unit economics, structure pricing, and stress-test decisions.</div>
""",
    unsafe_allow_html=True,
)
st.markdown("---")

# =====================
# Session state defaults
# =====================
if "materials" not in st.session_state:
    st.session_state.materials = [{"name": "Primary Material", "unit_cost": 2.00}]
if "equipment" not in st.session_state:
    st.session_state.equipment = [{"name": "Starter Tool", "units_supported": 200, "total_cost": 25.0}]
if "competitors" not in st.session_state:
    st.session_state.competitors = [{"name": "Competitor 1", "price": 8.0, "source": "Local shop"}]

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
    "Provide a precise, professional description including materials, process, unique value proposition, and expected use-cases."
    "Example: 'We produce 8-inch woven paracord bracelets with stainless-steel clasps for outdoor enthusiasts. Each unit uses 3 meters of Type III 550 paracord,"
    " is assembled using a jig for consistent tension, and is packaged in a recyclable kraft sleeve. Target customers are middle-school students and hikers"
    " seeking durable, customizable accessories. Production occurs in small batches of 25 to maintain quality control.'"
)
product_desc = st.text_area("Detailed product description (be specific)", value=st.session_state.get("product_desc", ""), help=product_desc_help)

colT1, colT2 = st.columns(2)
with colT1:
    target_audience = st.text_input("Target audience (segments/personas)", value=st.session_state.get("target_audience", ""))
with colT2:
    sales_channel = st.text_input("Primary sales channel (online, local, school, etc.)", value=st.session_state.get("sales_channel", ""))

# =====================
# Location section
# =====================
st.markdown("---")
st.subheader("Location")
loc1, loc2 = st.columns(2)
with loc1:
    city = st.text_input("City", value=st.session_state.get("city", ""))
with loc2:
    state = st.text_input("State/Region", value=st.session_state.get("state", ""))

# Additional product info
additional_info = st.text_area("Additional information (constraints, objectives, differentiators)", value=st.session_state.get("additional_info", ""))

# =====================
# Pricing approach selector
# =====================
pricing_mode = st.selectbox("Choose pricing approach", ["Cost-plus", "Market-based"], index=0)

# =====================
# COST-PLUS FLOW
# =====================
if pricing_mode == "Cost-plus":
    # Section 1: COGS
    st.markdown("---")
    st.header("Cost of Goods Sold (COGS)")
    add_mat_col = st.columns([3,7])[0]
    if add_mat_col.button("Add material +", use_container_width=True):
        st.session_state.materials.append({"name": "", "unit_cost": 0.0})

    mat_rows = []
    for i, item in enumerate(st.session_state.materials):
        c1, c2 = st.columns([3,2])
        name = c1.text_input(f"Material {i+1} name", value=item.get("name", ""), key=f"mat_name_{i}")
        cost = c2.number_input(f"Material {i+1} cost per unit ($)", min_value=0.0, value=float(item.get("unit_cost", 0.0)), step=0.01, key=f"mat_cost_{i}")
        st.session_state.materials[i] = {"name": name, "unit_cost": cost}
        mat_rows.append({"Material": name or f"Material {i+1}", "$ / unit": round(cost, 2)})

    materials_df = pd.DataFrame(mat_rows)
    materials_total = sum([m["unit_cost"] for m in st.session_state.materials])
    st.metric("Materials subtotal (per unit)", f"${materials_total:.2f}")

    # Section 2: Variable Costs
    st.markdown("---")
    st.header("Variable Costs")
    colV1, colV2 = st.columns(2)
    with colV1:
        shipping_unit = st.number_input("Outbound shipping or delivery per unit ($)", min_value=0.0, value=st.session_state.get("shipping_unit", 3.50), step=0.10)
    with colV2:
        variable_selling = st.number_input("Other variable selling expense per unit ($)", min_value=0.0, value=st.session_state.get("variable_selling", 0.00), step=0.10)

    variable_total = shipping_unit + variable_selling
    st.metric("Variable costs subtotal (per unit)", f"${variable_total:.2f}")

    # Section 3: Production Costs
    st.markdown("---")
    st.header("Production Costs")
    packaging_unit = st.number_input("Packaging cost per unit ($)", min_value=0.0, value=st.session_state.get("packaging_unit", 0.50), step=0.05)

    st.markdown("### Machinery and tools (amortized per unit)")
    add_eqp_col = st.columns([3,7])[0]
    if add_eqp_col.button("Add equipment +", use_container_width=True):
        st.session_state.equipment.append({"name": "", "units_supported": 100, "total_cost": 0.0})

    # Migrate legacy keys
    for idx, _eq in enumerate(st.session_state.equipment):
        if "units_supported" not in _eq and "cap_units" in _eq:
            try:
                st.session_state.equipment[idx]["units_supported"] = int(_eq.get("cap_units") or 100)
            except Exception:
                st.session_state.equipment[idx]["units_supported"] = 100
        if "total_cost" not in _eq and "tcost" in _eq:
            try:
                st.session_state.equipment[idx]["total_cost"] = float(_eq.get("tcost") or 0.0)
            except Exception:
                st.session_state.equipment[idx]["total_cost"] = 0.0

    # Build equipment UI rows safely
    eq_rows = []
    for j, eq in enumerate(st.session_state.equipment):
        c1, c2, c3 = st.columns([3,2,2])
        ename = c1.text_input(f"Equipment {j+1} name", value=eq.get("name", ""), key=f"eq_name_{j}")
        default_units = int(eq.get("units_supported", eq.get("cap_units", 100)) or 100)
        units_supported = c2.number_input(
            "Products it can make total",
            min_value=1,
            value=default_units,
            step=1,
            help="Total lifetime output this tool can realistically help produce before replacement",
            key=f"eq_units_{j}"
        )
        default_cost = float(eq.get("total_cost", eq.get("tcost", 0.0)) or 0.0)
        tcost = c3.number_input(
            f"Total cost {j+1} ($)",
            min_value=0.0,
            value=default_cost,
            step=1.0,
            key=f"eq_cost_{j}"
        )
        st.session_state.equipment[j] = {"name": ename, "units_supported": units_supported, "total_cost": tcost}
        per_unit = (tcost / units_supported) if units_supported > 0 else 0.0
        eq_rows.append({"Equipment": ename or f"Equipment {j+1}", "Per-unit amortization ($)": round(per_unit, 4)})

    equipment_df = pd.DataFrame(eq_rows)
    equipment_unit_total = 0.0
    for e in st.session_state.equipment:
        us = int(e.get("units_supported", e.get("cap_units", 0)) or 0)
        tc = float(e.get("total_cost", e.get("tcost", 0.0)) or 0.0)
        if us > 0:
            equipment_unit_total += tc / us

    production_total = packaging_unit + equipment_unit_total
    colPS1, colPS2 = st.columns(2)
    colPS1.metric("Packaging per unit", f"${packaging_unit:.2f}")
    colPS2.metric("Equipment per unit", f"${equipment_unit_total:.2f}")

    # Pricing and margin
    st.markdown("---")
    st.header("Pricing and Margin")
    margin_pct = st.slider("Target gross margin (%)", 5, 95, value=40, step=1)
    unit_cost = float(materials_total + variable_total + production_total)
    suggested_price = unit_cost * (1 + margin_pct / 100)
    unit_gross_profit = suggested_price - unit_cost

    colR1, colR2 = st.columns(2)
    with colR1:
        st.metric("Comprehensive unit cost", f"${unit_cost:.2f}")
        st.metric("Suggested price", f"${suggested_price:.2f}")
    with colR2:
        st.metric("Target margin", f"{margin_pct}%")
        st.metric("Gross profit per unit", f"${unit_gross_profit:.2f}")

    additional_cost_info = st.text_area("Additional cost information (special expenses, context)", value=st.session_state.get("additional_cost_info", ""))

    # Visuals
    comp_df = pd.DataFrame([
        {"Category": "COGS (materials)", "$ / unit": round(materials_total, 2)},
        {"Category": "Variable costs", "$ / unit": round(variable_total, 2)},
        {"Category": "Production costs", "$ / unit": round(production_total, 2)},
    ])
    fig = px.pie(comp_df, names="Category", values="$ / unit", title="Unit cost breakdown")
    fig.update_traces(textinfo='label+percent')
    st.plotly_chart(fig, use_container_width=True)

# =====================
# MARKET-BASED FLOW
# =====================
else:
    st.markdown("---")
    st.header("Market Inputs")

    # Competitor Analysis
    st.subheader("Competitor analysis")
    add_comp_col = st.columns([3,7])[0]
    if add_comp_col.button("Add competitor +", use_container_width=True):
        st.session_state.competitors.append({"name": "", "price": 0.0, "source": ""})
    comp_rows = []
    for i, comp in enumerate(st.session_state.competitors):
        c1, c2, c3 = st.columns([3,2,3])
        cname = c1.text_input(f"Competitor {i+1} name", value=comp.get("name", ""), key=f"comp_name_{i}")
        cprice = c2.number_input(f"Competitor {i+1} price ($)", min_value=0.0, value=float(comp.get("price", 0.0)), step=0.10, key=f"comp_price_{i}")
        csrc = c3.text_input(f"Data source {i+1}", value=comp.get("source", ""), key=f"comp_src_{i}")
        st.session_state.competitors[i] = {"name": cname, "price": cprice, "source": csrc}
        comp_rows.append({"Name": cname or f"Competitor {i+1}", "Price": round(cprice, 2), "Source": csrc})
    competitors_df = pd.DataFrame(comp_rows)

    # Cost foundation
    st.subheader("Cost foundation")
    mb_unit_cost = st.number_input("Total production cost per unit ($)", min_value=0.0, value=float(st.session_state.get("mb_unit_cost", 2.0)), step=0.10)
    mb_min_profitable = st.number_input("Minimum profitable price ($)", min_value=0.0, value=float(st.session_state.get("mb_min_profitable", 3.0)), step=0.10)

    # Target market
    st.subheader("Target market")
    demo = st.text_input("Customer demographic (age group, relationship to seller)", value=st.session_state.get("demo", ""))
    spend_range = st.text_input("Typical spending range for this category ($)", value=st.session_state.get("spend_range", ""))
    comp_level = st.selectbox("Competition level", ["Low", "Medium", "High"], index=1)

    # Product positioning
    st.subheader("Product positioning")
    quality_level = st.selectbox("Quality level", ["Budget", "Standard", "Premium"], index=1)
    usp = st.text_input("Unique selling points", value=st.session_state.get("usp", ""))
    features = st.text_input("Special features or benefits", value=st.session_state.get("features", ""))

    # Market timing
    st.subheader("Market timing")
    season = st.text_input("Selling season or timing", value=st.session_state.get("season", ""))
    trend_status = st.text_input("Current trend status", value=st.session_state.get("trend_status", ""))

    # Additional notes
    st.subheader("Additional notes")
    market_notes = st.text_area("Extra market factors or observations", value=st.session_state.get("market_notes", ""))

    # Derived insights
    comp_prices = [row["Price"] for _, row in competitors_df.iterrows() if row.get("Price") is not None]
    if len(comp_prices) > 0:
        comp_low = float(np.min(comp_prices))
        comp_avg = float(np.mean(comp_prices))
        comp_high = float(np.max(comp_prices))
    else:
        comp_low = comp_avg = comp_high = 0.0

    st.markdown("### Competitive price range")
    c1, c2, c3 = st.columns(3)
    c1.metric("Low competitor price", f"${comp_low:.2f}")
    c2.metric("Average competitor price", f"${comp_avg:.2f}")
    c3.metric("High competitor price", f"${comp_high:.2f}")

    # Simple positioning visualizer
    # Map quality to numeric for plotting
    quality_map = {"Budget": 1, "Standard": 2, "Premium": 3}
    points = [{"Label": r["Name"], "Quality": 2, "Price": r["Price"]} for _, r in competitors_df.iterrows()]
    points.append({"Label": product_name or "Your product", "Quality": quality_map.get(quality_level, 2), "Price": comp_avg if comp_avg else mb_min_profitable})
    pos_df = pd.DataFrame(points)
    pos_fig = px.scatter(pos_df, x="Quality", y="Price", text="Label", title="Market positioning (quality vs price)", range_x=[0.5,3.5])
    pos_fig.update_traces(textposition="top center")
    st.plotly_chart(pos_fig, use_container_width=True)

    # Price recommendation and sweet spot finder
    # Base on comp_avg anchored by cost floor
    if comp_avg and comp_avg > 0:
        recommended = max(mb_min_profitable, comp_avg)
    else:
        recommended = max(mb_min_profitable, mb_unit_cost * 1.3)
    sweet_low = max(mb_min_profitable, recommended * 0.95)
    sweet_high = recommended * 1.10

    st.markdown("### Recommended price")
    r1, r2, r3 = st.columns(3)
    r1.metric("Recommended", f"${recommended:.2f}")
    r2.metric("Sweet spot low", f"${sweet_low:.2f}")
    r3.metric("Sweet spot high", f"${sweet_high:.2f}")

    # Competitor comparison chart
    chart_df = competitors_df.copy()
    chart_df = chart_df.append({"Name": product_name or "Your product", "Price": recommended, "Source": "Recommendation"}, ignore_index=True)
    bar = px.bar(chart_df, x="Name", y="Price", title="Competitor prices vs your recommendation")
    st.plotly_chart(bar, use_container_width=True)

# =====================
# AI analysis and outputs (shared)
# =====================
st.markdown("---")
st.header("AI Commercial Analysis")

n_customers = st.slider("Number of simulated customer opinions", 100, 5000, 1000, step=100)

if st.button("Generate AI Analysis"):
    payload = {
        "pricing_mode": pricing_mode,
        "product_name": product_name,
        "product_description": product_desc,
        "target_audience": target_audience,
        "sales_channel": sales_channel,
        "city": city,
        "state": state,
        "additional_info": additional_info,
    }

    if pricing_mode == "Cost-plus":
        payload.update({
            "materials": st.session_state.materials,
            "equipment": st.session_state.equipment,
            "packaging_per_unit": float(packaging_unit),
            "shipping_per_unit": float(shipping_unit),
            "other_variable_per_unit": float(variable_selling),
            "unit_cost": float(unit_cost),
            "target_margin_pct": int(margin_pct),
            "suggested_price": float(suggested_price),
            "gross_profit_per_unit": float(unit_gross_profit),
            "additional_cost_info": st.session_state.get("additional_cost_info", ""),
        })
    else:
        payload.update({
            "competitors": st.session_state.competitors,
            "mb_unit_cost": float(mb_unit_cost),
            "mb_min_profitable": float(mb_min_profitable),
            "demographic": demo,
            "spending_range": spend_range,
            "competition_level": comp_level,
            "quality_level": quality_level,
            "usp": usp,
            "features": features,
            "season": season,
            "trend_status": trend_status,
            "market_notes": market_notes,
            "recommended_price": float(recommended),
            "sweet_spot_low": float(sweet_low),
            "sweet_spot_high": float(sweet_high),
            "comp_low": float(comp_low),
            "comp_avg": float(comp_avg),
            "comp_high": float(comp_high),
        })

    payload["n_customers"] = int(n_customers)

    prompt = f"""
    Act as a pricing and go-to-market advisor for a youth entrepreneur. Use every field in Data to tailor your analysis, including location and audience. If pricing_mode is Market-based, ground advice in competitor landscape and willingness to pay. If Cost-plus, ground advice in unit economics. Keep tone encouraging and professional.

    Data: {json.dumps(payload)}

    Tasks:
    1) Provide a concise competitiveness assessment using professional vocabulary.
    2) Return exactly {12 if n_customers>=1000 else 8} concise customer-style comments tailored to the audience and location, each with a practical improvement.
    3) Provide top 2 strengths and top 2 weaknesses with integer percentages that sum to 100 for each list, plus an "Other" value.
    4) Provide a star rating distribution (1–5 stars) for {n_customers} simulated reviews aligned to the analysis.

    Return valid JSON only with this schema:
    {{
      "competitive_summary": "...",
      "comments": ["..."],
      "best_aspects": {{"aspect1": "...", "percentage1": 60, "aspect2": "...", "percentage2": 30, "other": 10}},
      "worst_aspects": {{"aspect1": "...", "percentage1": 50, "aspect2": 35, "other": 15}},
      "star_ratings": {{"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}}
    }}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": prompt}],
            max_tokens=1800
        )
        raw = resp.choices[0].message.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)

        st.markdown("### Executive view")
        st.info(data.get("competitive_summary", ""))

        # Strengths and weaknesses
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

        # Detailed financials if Cost-plus
        if pricing_mode == "Cost-plus":
            metrics_rows = [
                {"Metric": "COGS (materials)", "Value": round(materials_total, 2)},
                {"Metric": "Variable costs", "Value": round(variable_total, 2)},
                {"Metric": "Production costs", "Value": round(production_total, 2)},
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
        else:
            # Market-based summary table
            mrows = [
                {"Metric": "Min profitable price", "Value": round(mb_min_profitable, 2)},
                {"Metric": "Competitive low", "Value": round(comp_low, 2)},
                {"Metric": "Competitive average", "Value": round(comp_avg, 2)},
                {"Metric": "Competitive high", "Value": round(comp_high, 2)},
                {"Metric": "Recommended price", "Value": round(recommended, 2)},
                {"Metric": "Sweet spot low", "Value": round(sweet_low, 2)},
                {"Metric": "Sweet spot high", "Value": round(sweet_high, 2)},
            ]
            st.markdown("### Market summary")
            st.dataframe(pd.DataFrame(mrows), use_container_width=True, hide_index=True)

        # Star ratings pie chart
        stars = data.get("star_ratings", {}) or {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        total_reported = sum(int(v) for v in stars.values()) if all(str(v).isdigit() for v in stars.values()) else 0
        if total_reported != int(n_customers):
            vals = np.array([max(0, int(stars.get(str(k), 0))) for k in range(1,6)], dtype=int)
            s = vals.sum()
            if s == 0:
                vals = np.array([0,0,0,int(n_customers*0.4), int(n_customers*0.6)], dtype=int)
                s = vals.sum()
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
st.caption("Built with Streamlit and OpenAI • Structured around cost-plus and market-based pricing paths.")

