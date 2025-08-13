import streamlit as st
import plotly.express as px
import pandas as pd
import json
from datetime import date
from openai import OpenAI

# =====================
# Setup
# =====================
st.set_page_config(page_title="Cost-Plus Pricing Lab", page_icon=":rocket:", layout="centered")
client = OpenAI(api_key=st.secrets["openai"]["api_key"])  # Keep API key in Streamlit secrets

# Background style
st.markdown(
    """
    <style>
      .stApp { background: radial-gradient(circle at 50% 40%, #144e72 0%, #1e5f8d 55%, #e7f6ff 100%); min-height: 100vh; }
      .small-note { color:#245a75; font-size:0.9rem; }
      .edu { background:#f0fbff; border-left:5px solid #19a7ff; padding:0.6rem 0.8rem; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<div style='text-align:center; font-size:38px; font-weight:800; color:#13c0ff;'>
  🚀 Cost-Plus Pricing Lab for Young Entrepreneurs
</div>
<div style='text-align:center; color:#0f2f44;'>Figure out a fair price, learn how costs work, and get friendly AI tips.</div>
""", unsafe_allow_html=True)
st.markdown("---")

# =====================
# Save / Load product profiles
# =====================
if "profiles" not in st.session_state:
    st.session_state.profiles = {}

cols = st.columns([2,2,1])
with cols[0]:
    profile_name = st.text_input("Save as profile name", placeholder="My Slime Kit v1")
with cols[1]:
    selected_profile = st.selectbox("Load profile", [""] + list(st.session_state.profiles.keys()))
with cols[2]:
    if st.button("💾 Save") and profile_name.strip():
        st.session_state.profiles[profile_name.strip()] = st.session_state.get("_current_profile", {})
        st.success(f"Saved profile '{profile_name.strip()}'")

if selected_profile:
    loaded = st.session_state.profiles.get(selected_profile, {})
    if loaded:
        st.session_state.update(loaded)
        st.info(f"Loaded profile '{selected_profile}'")

# =====================
# Product Basics
# =====================
st.subheader("📝 Product Basics")
colA, colB = st.columns(2)
with colA:
    product_name = st.text_input("Product name", value=st.session_state.get("product_name", ""), help="What are you selling?")
with colB:
    time_minutes = st.number_input("Time to make one product (minutes)", min_value=0, value=st.session_state.get("time_minutes", 15), help="How long it takes you to make one item.")
product_desc = st.text_area("Short description", value=st.session_state.get("product_desc", ""), placeholder="A handmade bracelet with cute charms.")

st.markdown("<div class='edu'>Tip: Time is money. Your time counts as a cost called 'labor'.</div>", unsafe_allow_html=True)

# =====================
# Materials
# =====================
st.subheader("🧱 Materials (per product)")
colM1, colM2 = st.columns(2)
with colM1:
    materials_cost = st.number_input("Raw materials ($)", min_value=0.0, value=st.session_state.get("materials_cost", 2.00), help="Beads, wood, flour, etc.")
with colM2:
    packaging_cost = st.number_input("Packaging ($)", min_value=0.0, value=st.session_state.get("packaging_cost", 0.50), help="Bags, boxes, labels.")

# =====================
# One-Time Equipment (CRITICAL)
# =====================
st.subheader("🛠️ One-Time Equipment")
colE1, colE2 = st.columns(2)
with colE1:
    equip_name = st.text_input("Equipment name", value=st.session_state.get("equip_name", "Glue gun"), help="Tool or machine you bought once.")
    equip_cost = st.number_input("Equipment total cost ($)", min_value=0.0, value=st.session_state.get("equip_cost", 25.0))
with colE2:
    equip_units = st.number_input("How many products can this make?", min_value=1, value=st.session_state.get("equip_units", 200), help="Best guess over the life of the equipment.")
    equip_date = st.date_input("Purchase date", value=st.session_state.get("equip_date", date.today()))

# Equipment cost per unit (amortized)
if equip_units > 0:
    equip_per_unit = equip_cost / equip_units
else:
    equip_per_unit = 0.0

# =====================
# Production Costs (CRITICAL)
# =====================
st.subheader("🏭 Production Costs")
colP1, colP2 = st.columns(2)
with colP1:
    hourly_wage = st.number_input("Your desired hourly wage ($/hour)", min_value=0.0, value=st.session_state.get("hourly_wage", 12.0), help="Pay yourself fairly for your time.")
    other_prod_cost = st.number_input("Other production cost per product ($)", min_value=0.0, value=st.session_state.get("other_prod_cost", 0.20), help="Electricity, water, etc.")
with colP2:
    shipping_cost = st.number_input("Shipping / delivery per product ($)", min_value=0.0, value=st.session_state.get("shipping_cost", 3.50))
    platform_fee_pct = st.slider("Platform fee (% of price)", min_value=0, max_value=30, value=st.session_state.get("platform_fee_pct", 5), help="Fees from Etsy, eBay, etc.")
    platform_fee_fixed = st.number_input("Platform fixed fee per sale ($)", min_value=0.0, value=st.session_state.get("platform_fee_fixed", 0.30))

# Labor cost per unit
labor_cost = (time_minutes / 60.0) * hourly_wage

# =====================
# Monthly Business Costs
# =====================
st.subheader("📅 Monthly Business Costs")
colB1, colB2 = st.columns(2)
with colB1:
    monthly_expenses = st.number_input("Total monthly business expenses ($)", min_value=0.0, value=st.session_state.get("monthly_expenses", 30.0), help="Ads, extra supplies, website, etc.")
with colB2:
    avg_units_per_month = st.number_input("Average products sold per month", min_value=1, value=st.session_state.get("avg_units_per_month", 20))

monthly_overhead_per_unit = monthly_expenses / avg_units_per_month if avg_units_per_month > 0 else 0.0

# =====================
# Additional Notes
# =====================
notes = st.text_area("Additional notes (optional)", value=st.session_state.get("notes", ""), help="Any special costs or things to remember.")

# =====================
# Cost-plus Calculation
# =====================
st.markdown("---")
st.subheader("🧮 Cost-Plus Calculator")
margin_pct = st.slider("Choose your profit margin (%)", 10, 100, value=40, help="Higher margin means more profit per sale, but price goes up.")

# Variable costs per unit (costs that happen every sale)
variable_costs = (
    materials_cost + packaging_cost + equip_per_unit + labor_cost + other_prod_cost + shipping_cost
)

# Price-dependent fees
# We will compute after we get pre-fee price guess. Start with base price guess:
base_price_no_fees = variable_costs + monthly_overhead_per_unit
prelim_price = base_price_no_fees * (1 + margin_pct/100)
platform_fees_per_unit = (platform_fee_pct/100.0) * prelim_price + platform_fee_fixed

true_unit_cost = variable_costs + monthly_overhead_per_unit + platform_fees_per_unit
suggested_price = true_unit_cost * (1 + margin_pct/100)
profit_per_unit = suggested_price - true_unit_cost

# Break-even units per month (to cover monthly expenses only)
contribution_per_unit = suggested_price - (variable_costs + platform_fees_per_unit)
breakeven_units = int(monthly_expenses / contribution_per_unit) + (1 if monthly_expenses % max(contribution_per_unit, 1e-9) != 0 else 0) if contribution_per_unit > 0 else None

# =====================
# Show Results
# =====================
st.success("Great job. Your pricing calculation is ready!")
st.balloons()

colR1, colR2 = st.columns(2)
with colR1:
    st.metric("Suggested Price", f"${suggested_price:.2f}")
    st.metric("Profit per Unit", f"${profit_per_unit:.2f}")
with colR2:
    st.metric("Your Margin", f"{margin_pct}%")
    if breakeven_units is not None and breakeven_units > 0:
        st.metric("Break-even units / month", f"{breakeven_units}")
    else:
        st.metric("Break-even units / month", "N/A")

# Cost breakdown table
breakdown = pd.DataFrame([
    {"Cost Type":"Materials", "$/unit": round(materials_cost,2)},
    {"Cost Type":"Packaging", "$/unit": round(packaging_cost,2)},
    {"Cost Type":"Equipment (spread)", "$/unit": round(equip_per_unit,2)},
    {"Cost Type":"Labor", "$/unit": round(labor_cost,2)},
    {"Cost Type":"Other Production", "$/unit": round(other_prod_cost,2)},
    {"Cost Type":"Shipping/Delivery", "$/unit": round(shipping_cost,2)},
    {"Cost Type":"Platform Fees", "$/unit": round(platform_fees_per_unit,2)},
    {"Cost Type":"Monthly Overhead", "$/unit": round(monthly_overhead_per_unit,2)},
], columns=["Cost Type","$/unit"]) 

st.markdown("### 📦 Where does the money go?")
st.dataframe(breakdown, use_container_width=True, hide_index=True)

fig = px.pie(breakdown, names="Cost Type", values="$/unit", title="Cost Breakdown per Unit")
st.plotly_chart(fig, use_container_width=True)

# =====================
# AI Feedback (competitiveness + advice)
# =====================
st.markdown("---")
st.subheader("🤖 AI Feedback on Your Price")

n_customers = st.slider("How many customer opinions to simulate?", 100, 5000, 1000, step=100)

# Choose number of comments based on n_customers
def comment_count(n):
    if n <= 100:
        return 8
    elif n <= 1000:
        return 10
    elif n <= 2500:
        return 12
    else:
        return 15

n_comments = comment_count(n_customers)

if st.button("Generate AI Feedback"):
    prompt = f"""
    You are helping a 10-17 year old entrepreneur think about pricing.
    Product: {product_name}
    Description: {product_desc}
    Time per unit (minutes): {time_minutes}
    Calculated suggested price: ${suggested_price:.2f}
    Profit per unit at this price: ${profit_per_unit:.2f}
    Margin percent: {margin_pct}%

    Unit cost breakdown (all values are $/unit):
    - Materials: {materials_cost:.2f}
    - Packaging: {packaging_cost:.2f}
    - Equipment (spread over {equip_units} units): {equip_per_unit:.2f}
    - Labor: {labor_cost:.2f}
    - Other production: {other_prod_cost:.2f}
    - Shipping: {shipping_cost:.2f}
    - Platform fees: {platform_fees_per_unit:.2f}
    - Monthly overhead per unit: {monthly_overhead_per_unit:.2f}

    Task 1: In one short paragraph, say whether this price looks competitive in a simple, friendly way.
    Task 2: Give {n_comments} short customer-style comments (kid-friendly) with mostly helpful improvement ideas they can actually do. Include a couple encouraging messages.
    Task 3: List the top 2 BEST aspects and top 2 WORST aspects with an estimated percentage of customers who chose each. Also include an 'Other' catch-all percent for each list. All percentages must be integers 0-100 and each list should sum to 100.

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

        st.markdown("### 📣 Competitive Summary")
        st.info(data.get("competitive_summary", ""))

        # Best/Worst aspects tables (2 aspects + Other)
        best = data.get("best_aspects", {})
        worst = data.get("worst_aspects", {})

        best_table = pd.DataFrame([
            {"Aspect": best.get("aspect1", "N/A"), "Percent of customers (%)": best.get("percentage1", "N/A")},
            {"Aspect": best.get("aspect2", "N/A"), "Percent of customers (%)": best.get("percentage2", "N/A")},
            {"Aspect": "Other", "Percent of customers (%)": best.get("other", "N/A")},
        ])
        best_table["Percent of customers (%)"] = best_table["Percent of customers (%)"].astype(str)

        worst_table = pd.DataFrame([
            {"Aspect": worst.get("aspect1", "N/A"), "Percent of customers (%)": worst.get("percentage1", "N/A")},
            {"Aspect": worst.get("aspect2", "N/A"), "Percent of customers (%)": worst.get("percentage2", "N/A")},
            {"Aspect": "Other", "Percent of customers (%)": worst.get("other", "N/A")},
        ])
        worst_table["Percent of customers (%)"] = worst_table["Percent of customers (%)"].astype(str)

        st.markdown("### 🏅 Best reasons people like your product")
        st.dataframe(best_table, use_container_width=True, hide_index=True)
        st.caption("Percent of customers (%) means how many people picked that reason as their favorite part.")

        st.markdown("### 🚧 Top things to improve")
        st.dataframe(worst_table, use_container_width=True, hide_index=True)
        st.caption("Percent of customers (%) means how many people picked that reason as the biggest thing to fix.")

        # Comments
        comments = data.get("comments", [])
        st.markdown("### 💬 Customer-style comments")
        if comments:
            for c in comments:
                st.info(f"🗣️ {c}")
        else:
            st.write("No comments available.")

    except Exception as e:
        st.error("AI response could not be parsed. Here's what we got:")
        st.code(locals().get("raw", "<no raw output>"))

# =====================
# Persist current profile in session
# =====================
st.session_state._current_profile = dict(
    product_name=product_name,
    product_desc=product_desc,
    time_minutes=time_minutes,
    materials_cost=materials_cost,
    packaging_cost=packaging_cost,
    equip_name=equip_name,
    equip_cost=equip_cost,
    equip_units=equip_units,
    equip_date=str(equip_date),
    hourly_wage=hourly_wage,
    other_prod_cost=other_prod_cost,
    shipping_cost=shipping_cost,
    platform_fee_pct=platform_fee_pct,
    platform_fee_fixed=platform_fee_fixed,
    monthly_expenses=monthly_expenses,
    avg_units_per_month=avg_units_per_month,
    notes=notes,
    margin_pct=margin_pct,
)

# Download profile as JSON
profile_json = json.dumps(st.session_state._current_profile, indent=2)
st.download_button("⬇️ Download profile JSON", data=profile_json, file_name=f"{product_name or 'product'}.json", mime="application/json")

st.markdown("---")
st.caption("Made with Streamlit + OpenAI • Learn by doing • You got this! ✨")

