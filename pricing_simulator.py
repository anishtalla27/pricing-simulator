import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import json
from openai import OpenAI

# =====================
# Setup
# =====================
st.set_page_config(page_title="Professional Pricing Studio", page_icon=":briefcase:", layout="centered")
client = OpenAI(api_key=st.secrets["openai"]["api_key"])  # keep as is

# ---------- UI helpers: kid-friendly help next to each field ----------
def _help_popover(text: str, title: str = "Help"):
    with st.popover(title):
        st.write(text)


def text_input_help(label, value="", help_text="", key=None, **kwargs):
    c1, c2 = st.columns([3, 1])
    val = c1.text_input(label, value=value, key=key, **kwargs)
    with c2:
        _help_popover(help_text or "Explain this in simple words")
    return val


def text_area_help(label, value="", help_text="", key=None, **kwargs):
    c1, c2 = st.columns([3, 1])
    val = c1.text_area(label, value=value, key=key, **kwargs)
    with c2:
        _help_popover(help_text or "Explain this in simple words")
    return val


def number_input_help(label, min_value=None, max_value=None, value=None, step=None, format=None, help_text="", key=None, **kwargs):
    c1, c2 = st.columns([3, 1])
    val = c1.number_input(label, min_value=min_value, max_value=max_value, value=value, step=step, format=format, key=key, **kwargs)
    with c2:
        _help_popover(help_text or "Explain this number in simple words")
    return val


def selectbox_help(label, options, index=0, help_text="", key=None, **kwargs):
    c1, c2 = st.columns([3, 1])
    val = c1.selectbox(label, options, index=index, key=key, **kwargs)
    with c2:
        _help_popover(help_text or "Explain choices in simple words")
    return val


def slider_help(label, min_value, max_value, value=None, step=None, help_text="", key=None, **kwargs):
    c1, c2 = st.columns([3, 1])
    val = c1.slider(label, min_value, max_value, value=value, step=step, key=key, **kwargs)
    with c2:
        _help_popover(help_text or "Explain this slider in simple words")
    return val


# Background + UI polish
st.markdown(
    """
    <style>
      .stApp { background: radial-gradient(circle at 50% 40%, #0e3d5a 0%, #175a80 55%, #e7f6ff 100%); min-height: 100vh; }
      div[data-testid="stTextArea"] { margin-bottom: 0px; }
      div[data-testid="column"] button { white-space: nowrap; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style='text-align:center; font-size:34px; font-weight:800; color:#0ea5e9;'>
  Professional Pricing Studio
</div>
<div style='text-align:center; color:#13d0ff;'>Calculate unit economics, compare to market, and price based on value.</div>
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
    st.session_state.competitors = [{"name": "Competitor 1", "price": 8.0, "differences": ""}]
if "vb_benefits" not in st.session_state:
    st.session_state.vb_benefits = [{"benefit": "Saves time on setup", "impact": 3, "consequence": "Takes longer without it"}]
if "vb_alternatives" not in st.session_state:
    st.session_state.vb_alternatives = [{"name": "Do it by hand", "cost": 2.0}]

# =====================
# Product basics
# =====================
st.subheader("Product Definition")
colA, colB = st.columns(2)
with colA:
    product_name = text_input_help(
        "Product name",
        value=st.session_state.get("product_name", ""),
        help_text="What you call the product. Example: Paracord Bracelet",
        key="product_name",
    )
with colB:
    cycle_minutes = number_input_help(
        "Direct labor time per unit (minutes)",
        min_value=0,
        value=st.session_state.get("cycle_minutes", 15),
        step=1,
        help_text="How many minutes it takes you to make one item from start to finish. Use your best guess if unsure.",
        key="cycle_minutes",
    )

product_desc_help = (
    "Describe what you make, what it is made of, and who it is for in simple words. Example: We make 8-inch woven paracord bracelets with metal clasps for kids who like outdoor gear."
)
product_desc = text_area_help(
    "Detailed product description (be as specific as possible)",
    value=st.session_state.get("product_desc", ""),
    help_text=product_desc_help,
    key="product_desc",
)

colT1, colT2 = st.columns(2)
with colT1:
    target_audience = text_input_help(
        "Target audience (segments or personas)",
        value=st.session_state.get("target_audience", ""),
        help_text="Who will buy this. Example: 6th to 9th graders, parents at school events, hikers.",
        key="target_audience",
    )
with colT2:
    sales_channel = text_input_help(
        "Primary sales channel (online, local, school, etc.)",
        value=st.session_state.get("sales_channel", ""),
        help_text="Where you sell. Example: School lunch table, local fair, Etsy, Instagram DMs.",
        key="sales_channel",
    )

additional_info = text_area_help(
    "Additional information (constraints, objectives, differentiators)",
    value=st.session_state.get("additional_info", ""),
    help_text="Anything special. Example: Only weekends available, eco friendly packaging, custom colors.",
    key="additional_info",
)

# =====================
# Location section
# =====================
st.markdown("---")
st.subheader("Location")
loc1, loc2 = st.columns(2)
with loc1:
    city = text_input_help("City", value=st.session_state.get("city", ""), help_text="Your city or town.", key="city")
with loc2:
    state = text_input_help("State or Region", value=st.session_state.get("state", ""), help_text="Your state or area.", key="state")

# =====================
# Pricing approach selector
# =====================
st.markdown("---")
st.subheader("Choose pricing approach")

st.markdown(
    "**Cost plus pricing:** Start from your costs, then add a target margin to set a price. Good when you know your costs and want a simple result.  "
    "**Market based pricing:** Look at competitor prices and buyer willingness to pay, then choose a price that fits your product's position.  "
    "**Value based pricing:** Price according to the value your product creates for customers, like time or money saved compared to alternatives."
)

pricing_mode = selectbox_help(
    "Pricing method",
    ["Cost-plus", "Market-based", "Value-based"],
    index=0,
    help_text="Pick how you want to set your price. Cost plus uses your costs. Market based uses competitor prices. Value based uses the benefits you create.",
    key="pricing_mode",
)

with st.expander("What is Cost plus pricing?", expanded=True):
    st.write("- Add COGS, variable, and production costs per unit. ")
    st.write("- Choose a target margin for profit. ")
    st.write("- Price = Unit cost x (1 + margin).")
with st.expander("What is Market based pricing?", expanded=True):
    st.write("- Collect competitor prices and note differences. ")
    st.write("- Consider who will buy and typical spend. ")
    st.write("- Pick a price that fits your quality and stays above your minimum profitable price.")
with st.expander("What is Value based pricing?", expanded=True):
    st.write("- Find the value your product creates like time and money saved. ")
    st.write("- Compare with what customers use today and what that costs. ")
    st.write("- Set a price that reflects part of that value and is acceptable to customers.")

# =====================
# COST PLUS FLOW
# =====================
if pricing_mode == "Cost-plus":
    # Section 1: COGS
    st.markdown("---")
    st.header("Cost of Goods Sold (COGS)")

    add_mat_col = st.columns([3, 7])[0]
    if add_mat_col.button("Add material +", use_container_width=True):
        st.session_state.materials.append({"name": "", "unit_cost": 0.0})

    mat_rows = []
    for i, item in enumerate(st.session_state.materials):
        c1, c2, c3 = st.columns([3, 2, 1])
        name = c1.text_input(f"Material {i+1} name", value=item.get("name", ""), key=f"mat_name_{i}")
        with c3:
            _help_popover("What the item is called. Example: Paracord, clasp, sticker.")
        cost = c2.number_input(
            f"Material {i+1} cost per unit ($)",
            min_value=0.0,
            value=float(item.get("unit_cost", 0.0)),
            step=0.01,
            key=f"mat_cost_{i}",
        )
        with c3:
            pass
        st.session_state.materials[i] = {"name": name, "unit_cost": cost}
        mat_rows.append({"Material": name or f"Material {i+1}", "$ / unit": round(cost, 2)})

    materials_df = pd.DataFrame(mat_rows)
    materials_total = sum([m["unit_cost"] for m in st.session_state.materials])
    st.metric("Materials subtotal per unit", f"${materials_total:.2f}")

    # Section 2: Variable Costs
    st.markdown("---")
    st.header("Variable Costs")
    colV1, colV2 = st.columns(2)
    with colV1:
        shipping_unit = number_input_help(
            "Outbound shipping or delivery per unit ($)",
            min_value=0.0,
            value=st.session_state.get("shipping_unit", 3.50),
            step=0.10,
            help_text="Average cost to ship or deliver one item. If you hand deliver at school, use 0.",
            key="shipping_unit",
        )
    with colV2:
        variable_selling = number_input_help(
            "Other variable selling expense per unit ($)",
            min_value=0.0,
            value=st.session_state.get("variable_selling", 0.00),
            step=0.10,
            help_text="Any extra cost that happens only when you sell one more item. Example: marketplace fee per sale.",
            key="variable_selling",
        )

    variable_total = shipping_unit + variable_selling
    st.metric("Variable costs subtotal per unit", f"${variable_total:.2f}")

    # Section 3: Production Costs
    st.markdown("---")
    st.header("Production Costs")
    packaging_unit = number_input_help(
        "Packaging cost per unit ($)",
        min_value=0.0,
        value=st.session_state.get("packaging_unit", 0.50),
        step=0.05,
        help_text="Box, bag, or sleeve for one item.",
        key="packaging_unit",
    )

    st.markdown("### Machinery and tools amortized per unit")
    add_eqp_col = st.columns([3, 7])[0]
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
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        ename = c1.text_input(f"Equipment {j+1} name", value=eq.get("name", ""), key=f"eq_name_{j}")
        with c4:
            _help_popover("Tool name. Example: Bead kit, glue gun, jig.")
        default_units = int(eq.get("units_supported", eq.get("cap_units", 100)) or 100)
        units_supported = c2.number_input(
            "Products it can make total",
            min_value=1,
            value=default_units,
            step=1,
            help="",
            key=f"eq_units_{j}",
        )
        with c4:
            _help_popover("How many items this tool can help make before you must replace it. A guess is ok.")
        default_cost = float(eq.get("total_cost", eq.get("tcost", 0.0)) or 0.0)
        tcost = c3.number_input(
            f"Total cost {j+1} ($)",
            min_value=0.0,
            value=default_cost,
            step=1.0,
            key=f"eq_cost_{j}",
        )
        with c4:
            _help_popover("What you paid for the tool in total.")
        st.session_state.equipment[j] = {"name": ename, "units_supported": units_supported, "total_cost": tcost}
        per_unit = (tcost / units_supported) if units_supported > 0 else 0.0
        eq_rows.append({"Equipment": ename or f"Equipment {j+1}", "Per unit amortization ($)": round(per_unit, 4)})

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
    margin_pct = slider_help(
        "Target gross margin (%)",
        5,
        95,
        value=40,
        step=1,
        help_text="How much profit you want as a percent of price. 40 means 40 percent of the price is profit before fixed costs.",
        key="margin_pct",
    )
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

    additional_cost_info = text_area_help(
        "Additional cost information (special expenses or context)",
        value=st.session_state.get("additional_cost_info", ""),
        help_text="Anything else that adds to cost sometimes. Example: rush shipping for supplies.",
        key="additional_cost_info",
    )

    # Visuals
    comp_df = pd.DataFrame([
        {"Category": "COGS materials", "$ / unit": round(materials_total, 2)},
        {"Category": "Variable costs", "$ / unit": round(variable_total, 2)},
        {"Category": "Production costs", "$ / unit": round(production_total, 2)},
    ])
    fig = px.pie(comp_df, names="Category", values="$ / unit", title="Unit cost breakdown")
    fig.update_traces(textinfo='label+percent')
    st.plotly_chart(fig, use_container_width=True)

# =====================
# MARKET BASED FLOW
# =====================
elif pricing_mode == "Market-based":
    st.markdown("---")
    st.header("Market Inputs")

    # Competitor Analysis
    st.subheader("Competitor analysis")
    add_comp_col = st.columns([3, 7])[0]
    if add_comp_col.button("Add competitor +", use_container_width=True):
        st.session_state.competitors.append({"name": "", "price": 0.0, "differences": ""})

    comp_rows = []
    for i, comp in enumerate(st.session_state.competitors):
        c1, c2, c3 = st.columns([3, 2, 1])
        cname = c1.text_input(f"Competitor {i+1} name", value=comp.get("name", ""), key=f"comp_name_{i}")
        with c3:
            _help_popover("Who else sells something like yours. Example: Bracelet Booth, Online Shop X.")
        cprice = c2.number_input(
            f"Competitor {i+1} price ($)",
            min_value=0.0,
            value=float(comp.get("price", 0.0)),
            step=0.10,
            key=f"comp_price_{i}",
        )
        with c3:
            _help_popover("The price they charge for one item.")
        cdiff = text_area_help(
            f"Compare to your product: strengths and weaknesses for Competitor {i+1}",
            value=comp.get("differences", ""),
            help_text="How they are better or worse than you. Example: lower price but slower delivery.",
            key=f"comp_diff_{i}",
        )
        st.session_state.competitors[i] = {"name": cname, "price": cprice, "differences": cdiff}
        comp_rows.append({"Name": cname or f"Competitor {i+1}", "Price": round(cprice, 2), "Differences": cdiff})
    competitors_df = pd.DataFrame(comp_rows)

    # Cost foundation
    st.subheader("Cost foundation")
    mb_unit_cost = number_input_help(
        "Total production cost per unit ($)",
        min_value=0.0,
        value=float(st.session_state.get("mb_unit_cost", 2.0)),
        step=0.10,
        help_text="What it costs you to make one item in total.",
        key="mb_unit_cost",
    )
    mb_min_profitable = number_input_help(
        "Minimum profitable price ($)",
        min_value=0.0,
        value=float(st.session_state.get("mb_min_profitable", 3.0)),
        step=0.10,
        help_text="Lowest price where you do not lose money.",
        key="mb_min_profitable",
    )

    # Target market
    st.subheader("Target market")
    demo = text_input_help(
        "Customer demographic (age group, relationship to seller)",
        value=st.session_state.get("demo", ""),
        help_text="Who buys. Example: middle schoolers, parents, teachers, neighbors.",
        key="demo",
    )
    spend_range = text_input_help(
        "Typical spending range for this category ($)",
        value=st.session_state.get("spend_range", ""),
        help_text="What people usually pay for this kind of thing. Example: $5 to $12.",
        key="spend_range",
    )
    comp_level = selectbox_help(
        "Competition level",
        ["Very low", "Low", "Medium", "High", "Very high"],
        index=2,
        help_text="How many others sell the same type of item where you sell.",
        key="comp_level",
    )

    # Product positioning
    st.subheader("Product positioning")
    quality_level = selectbox_help(
        "Quality level",
        ["Budget", "Standard", "Premium"],
        index=1,
        help_text="Budget means cheapest. Premium means top quality and higher price.",
        key="quality_level",
    )
    usp = text_input_help(
        "Unique selling points",
        value=st.session_state.get("usp", ""),
        help_text="What makes yours special. Example: custom colors, same day delivery at school.",
        key="usp",
    )
    features = text_input_help(
        "Special features or benefits",
        value=st.session_state.get("features", ""),
        help_text="Extra things your product offers. Example: name engraving, gift wrap.",
        key="features",
    )

    # Additional notes
    st.subheader("Additional notes")
    market_notes = text_area_help(
        "Extra market factors or observations",
        value=st.session_state.get("market_notes", ""),
        help_text="Anything else about your market. Example: school rules, event dates, weather.",
        key="market_notes",
    )

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
    quality_map = {"Budget": 1, "Standard": 2, "Premium": 3}
    points = [{"Label": r["Name"], "Quality": 2, "Price": r["Price"]} for _, r in competitors_df.iterrows()]
    points.append({"Label": product_name or "Your product", "Quality": quality_map.get(quality_level, 2), "Price": comp_avg if comp_avg else mb_min_profitable})
    pos_df = pd.DataFrame(points)
    pos_fig = px.scatter(pos_df, x="Quality", y="Price", text="Label", title="Market positioning quality vs price", range_x=[0.5, 3.5])
    pos_fig.update_traces(textposition="top center")
    st.plotly_chart(pos_fig, use_container_width=True)

    # Price recommendation and sweet spot finder
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
    rec_row = pd.DataFrame([
        {"Name": product_name or "Your product", "Price": recommended}
    ])
    chart_df = pd.concat([chart_df, rec_row], ignore_index=True)
    bar = px.bar(chart_df, x="Name", y="Price", title="Competitor prices vs your recommendation")
    st.plotly_chart(bar, use_container_width=True)

# =====================
# VALUE BASED FLOW
# =====================
else:
    st.markdown("---")
    st.header("Value Inputs")

    # Core problem
    core_problem = text_input_help(
        "Core problem the product solves",
        value=st.session_state.get("core_problem", ""),
        help_text="What problem do you fix for the buyer. Example: bracelet fits better and lasts longer.",
        key="core_problem",
    )

    # Customer Value Discovery
    st.subheader("Customer value discovery")
    add_benefit_col = st.columns([3, 7])[0]
    if add_benefit_col.button("Add benefit +", use_container_width=True):
        st.session_state.vb_benefits.append({"benefit": "", "impact": 3, "consequence": ""})

    vb_rows = []
    for i, b in enumerate(st.session_state.vb_benefits):
        c1, c2, c3 = st.columns([4, 1, 1])
        benefit = c1.text_input(f"Benefit {i+1}", value=b.get("benefit", ""), key=f"vb_ben_{i}")
        with c3:
            _help_popover("Good thing your product gives the buyer. Example: saves time, looks cool, more durable.")
        impact = c2.slider(f"Impact {i+1} (1-5)", 1, 5, value=int(b.get("impact", 3)), key=f"vb_imp_{i}")
        with c3:
            _help_popover("How big that benefit is. 1 is tiny. 5 is huge.")
        consequence = text_area_help(
            f"Consequence if missing {i+1}",
            value=b.get("consequence", ""),
            help_text="What happens if they do not have your product. Example: takes longer, breaks sooner.",
            key=f"vb_con_{i}",
        )
        st.session_state.vb_benefits[i] = {"benefit": benefit, "impact": impact, "consequence": consequence}
        vb_rows.append({"Benefit": benefit or f"Benefit {i+1}", "Impact": impact, "Consequence": consequence})
    vb_df = pd.DataFrame(vb_rows)

    # Alternatives
    st.subheader("Alternatives customers use today")
    add_alt_col = st.columns([3, 7])[0]
    if add_alt_col.button("Add alternative +", use_container_width=True):
        st.session_state.vb_alternatives.append({"name": "", "cost": 0.0})

    alt_rows = []
    for i, a in enumerate(st.session_state.vb_alternatives):
        c1, c2, c3 = st.columns([3, 2, 1])
        aname = c1.text_input(f"Alternative {i+1} name", value=a.get("name", ""), key=f"vb_alt_name_{i}")
        with c3:
            _help_popover("What people do now instead of buying from you. Example: DIY, buy from big store.")
        acost = c2.number_input(
            f"Alternative {i+1} cost ($)",
            min_value=0.0,
            value=float(a.get("cost", 0.0)),
            step=0.10,
            key=f"vb_alt_cost_{i}",
        )
        with c3:
            _help_popover("What that alternative costs them for one item or one time.")
        st.session_state.vb_alternatives[i] = {"name": aname, "cost": acost}
        alt_rows.append({"Alternative": aname or f"Alternative {i+1}", "Cost": round(acost, 2)})
    alt_df = pd.DataFrame(alt_rows)

    # Savings
    st.subheader("Savings and willingness to pay")
    colS1, colS2, colS3 = st.columns(3)
    with colS1:
        money_saved = number_input_help(
            "Money saved per unit for customer ($)",
            min_value=0.0,
            value=float(st.session_state.get("money_saved", 0.0)),
            step=0.10,
            help_text="If they choose you, how many dollars do they save each time. If none, use 0.",
            key="money_saved",
        )
    with colS2:
        minutes_saved = number_input_help(
            "Minutes saved per unit for customer",
            min_value=0,
            value=int(st.session_state.get("minutes_saved", 0)),
            step=5,
            help_text="How many minutes you save them each time.",
            key="minutes_saved",
        )
    with colS3:
        value_of_time = number_input_help(
            "Value of time ($ per hour)",
            min_value=0.0,
            value=float(st.session_state.get("value_of_time", 12.0)),
            step=1.0,
            help_text="Pick a simple number for what an hour is worth to your buyer. Example: $12 per hour.",
            key="value_of_time",
        )

    colW1, colW2, colW3 = st.columns(3)
    with colW1:
        wtp_typical = number_input_help(
            "Typical willingness to pay ($)",
            min_value=0.0,
            value=float(st.session_state.get("wtp_typical", 5.0)),
            step=0.10,
            help_text="A fair price most buyers would pay.",
            key="wtp_typical",
        )
    with colW2:
        wtp_max = number_input_help(
            "Maximum price customers might accept ($)",
            min_value=0.0,
            value=float(st.session_state.get("wtp_max", 10.0)),
            step=0.10,
            help_text="The highest price before people say no.",
            key="wtp_max",
        )
    with colW3:
        wtp_min_expected = number_input_help(
            "Minimum price customers expect ($)",
            min_value=0.0,
            value=float(st.session_state.get("wtp_min_expected", 0.0)),
            step=0.10,
            help_text="The price that feels normal or not too cheap.",
            key="wtp_min_expected",
        )

    # Cost foundation
    st.subheader("Cost foundation")
    vb_unit_cost = number_input_help(
        "Production cost per unit ($)",
        min_value=0.0,
        value=float(st.session_state.get("vb_unit_cost", 2.0)),
        step=0.10,
        help_text="Your total cost to make one item.",
        key="vb_unit_cost",
    )
    vb_min_profitable = number_input_help(
        "Minimum profitable price ($)",
        min_value=0.0,
        value=float(st.session_state.get("vb_min_profitable", 3.0)),
        step=0.10,
        help_text="Lowest price where you do not lose money.",
        key="vb_min_profitable",
    )

    # Additional notes
    st.subheader("Additional notes")
    vb_notes = text_area_help(
        "Other value considerations or customer insights",
        value=st.session_state.get("vb_notes", ""),
        help_text="Anything else about value. Example: warranty, free repairs, bundle deals.",
        key="vb_notes",
    )

    # Derived calculators
    alt_costs = [row["Cost"] for _, row in alt_df.iterrows() if row.get("Cost") is not None]
    alt_avg = float(np.mean(alt_costs)) if len(alt_costs) > 0 else 0.0
    time_value = (minutes_saved / 60.0) * value_of_time
    estimated_value = max(0.0, (alt_avg - vb_unit_cost) + money_saved + time_value)

    # Value to price recommendation engine
    base_from_value = 0.6 * wtp_typical + 0.4 * estimated_value
    recommended_vb = max(vb_min_profitable, min(wtp_max, base_from_value))
    sweet_low_vb = max(vb_min_profitable, max(wtp_min_expected, recommended_vb * 0.95))
    sweet_high_vb = min(wtp_max if wtp_max > 0 else recommended_vb * 1.2, recommended_vb * 1.10)

    st.markdown("### Value recommendation")
    r1, r2, r3 = st.columns(3)
    r1.metric("Recommended price", f"${recommended_vb:.2f}")
    r2.metric("Sweet spot low", f"${sweet_low_vb:.2f}")
    r3.metric("Sweet spot high", f"${sweet_high_vb:.2f}")

    # Alternative cost comparison chart
    if not alt_df.empty:
        vb_chart_df = alt_df.copy()
        vb_chart_df = pd.concat([
            vb_chart_df, 
            pd.DataFrame([{
                "Alternative": product_name or "Your product", 
                "Cost": recommended_vb
            }])
        ], ignore_index=True)
        vb_bar = px.bar(
            vb_chart_df, 
            x="Alternative", 
            y="Cost", 
            title="Alternative Costs vs Your Recommended Price"
        )
        st.plotly_chart(vb_bar, use_container_width=True)

    # Interview questions helper
    with st.expander("Interview questions you can use", expanded=True):
        st.write("- What problem does this product solve for you right now?")
        st.write("- What do you use instead today and what does that cost you?")
        st.write("- How much time would this save you each time you use it?")
        st.write("- If you could not buy this, what would you do instead?")
        st.write("- At what price would you think this is a great deal? A bit expensive? Too expensive?")

# =====================
# AI analysis and outputs (shared)
# =====================
st.markdown("---")
st.header("AI Commercial Analysis")

n_customers = slider_help(
    "Number of simulated customer opinions",
    100,
    5000,
    1000,
    step=100,
    help_text="How many pretend reviews we create. More gives a smoother chart.",
    key="n_customers",
)

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
            "unit_cost": float(materials_total + variable_total + production_total),
            "target_margin_pct": int(margin_pct),
            "suggested_price": float((materials_total + variable_total + production_total) * (1 + margin_pct / 100)),
            "gross_profit_per_unit": float((materials_total + variable_total + production_total) * (margin_pct / 100)),
            "additional_cost_info": st.session_state.get("additional_cost_info", ""),
        })
    elif pricing_mode == "Market-based":
        # recompute safe defaults
        comp_prices = [row.get("price", 0.0) for row in st.session_state.competitors]
        comp_low = float(np.min(comp_prices)) if len(comp_prices) else 0.0
        comp_avg = float(np.mean(comp_prices)) if len(comp_prices) else 0.0
        comp_high = float(np.max(comp_prices)) if len(comp_prices) else 0.0
        if comp_avg and comp_avg > 0:
            recommended = max(st.session_state.get("mb_min_profitable", 0.0), comp_avg)
        else:
            recommended = max(st.session_state.get("mb_min_profitable", 0.0), st.session_state.get("mb_unit_cost", 0.0) * 1.3)
        sweet_low = max(st.session_state.get("mb_min_profitable", 0.0), recommended * 0.95)
        sweet_high = recommended * 1.10

        payload.update({
            "competitors": st.session_state.competitors,
            "mb_unit_cost": float(st.session_state.get("mb_unit_cost", 2.0)),
            "mb_min_profitable": float(st.session_state.get("mb_min_profitable", 3.0)),
            "demographic": st.session_state.get("demo", ""),
            "spending_range": st.session_state.get("spend_range", ""),
            "competition_level": st.session_state.get("comp_level", "Medium"),
            "quality_level": st.session_state.get("quality_level", "Standard"),
            "usp": st.session_state.get("usp", ""),
            "features": st.session_state.get("features", ""),
            "market_notes": st.session_state.get("market_notes", ""),
            "recommended_price": float(recommended),
            "sweet_spot_low": float(sweet_low),
            "sweet_spot_high": float(sweet_high),
            "comp_low": float(comp_low),
            "comp_avg": float(comp_avg),
            "comp_high": float(comp_high),
        })
    else:
        # recompute safe defaults
        alt_costs = [a.get("cost", 0.0) for a in st.session_state.vb_alternatives]
        alt_avg = float(np.mean(alt_costs)) if len(alt_costs) > 0 else 0.0
        time_value = (st.session_state.get("minutes_saved", 0) / 60.0) * st.session_state.get("value_of_time", 12.0)
        estimated_value = max(0.0, (alt_avg - st.session_state.get("vb_unit_cost", 0.0)) + st.session_state.get("money_saved", 0.0) + time_value)
        base_from_value = 0.6 * st.session_state.get("wtp_typical", 0.0) + 0.4 * estimated_value
        recommended_vb = max(st.session_state.get("vb_min_profitable", 0.0), min(st.session_state.get("wtp_max", 0.0), base_from_value))
        sweet_low_vb = max(st.session_state.get("vb_min_profitable", 0.0), max(st.session_state.get("wtp_min_expected", 0.0), recommended_vb * 0.95))
        sweet_high_vb = min(st.session_state.get("wtp_max", 0.0) if st.session_state.get("wtp_max", 0.0) > 0 else recommended_vb * 1.2, recommended_vb * 1.10)

        payload.update({
            "core_problem": st.session_state.get("core_problem", ""),
            "benefits": st.session_state.vb_benefits,
            "alternatives": st.session_state.vb_alternatives,
            "money_saved": float(st.session_state.get("money_saved", 0.0)),
            "minutes_saved": int(st.session_state.get("minutes_saved", 0)),
            "value_of_time": float(st.session_state.get("value_of_time", 12.0)),
            "estimated_value": float(estimated_value),
            "wtp_typical": float(st.session_state.get("wtp_typical", 5.0)),
            "wtp_max": float(st.session_state.get("wtp_max", 10.0)),
            "wtp_min_expected": float(st.session_state.get("wtp_min_expected", 0.0)),
            "vb_unit_cost": float(st.session_state.get("vb_unit_cost", 2.0)),
            "vb_min_profitable": float(st.session_state.get("vb_min_profitable", 3.0)),
            "vb_notes": st.session_state.get("vb_notes", ""),
            "recommended_price": float(recommended_vb),
            "sweet_spot_low": float(sweet_low_vb),
            "sweet_spot_high": float(sweet_high_vb),
            "alt_avg_cost": float(alt_avg),
        })

    payload["n_customers"] = int(n_customers)

    prompt = f"""
    Act as a pricing and go to market advisor for a youth entrepreneur. Use every field in Data to tailor your analysis, including location and audience. If pricing_mode is Market-based, ground advice in competitor landscape and willingness to pay. If Cost-plus, ground advice in unit economics. If Value-based, ground advice in customer benefits, alternatives, savings, and willingness to pay. Keep tone encouraging and professional.

    Data: {json.dumps(payload)}

    Tasks:
    1) Provide a concise competitiveness assessment using professional vocabulary.
    2) Return exactly {12 if n_customers>=1000 else 8} concise customer-style comments tailored to the audience and location, each with a practical improvement.
    3) Provide top 2 strengths and top 2 weaknesses with integer percentages that sum to 100 for each list, plus an "Other" value.
    4) Provide a star rating distribution (1-5 stars) for {n_customers} simulated reviews aligned to the analysis.

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
            messages=[
                {"role": "system", "content": "You are a pricing analysis function. Always return valid JSON matching the provided schema. Do not include commentary or code fences. Consider every field in Data and reflect it in the output."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            top_p=1,
            presence_penalty=0,
            frequency_penalty=0,
            n=1,
            max_tokens=1800,
        )
        raw = resp.choices[0].message.content
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

        # If Cost plus, show details
        if pricing_mode == "Cost-plus":
            metrics_rows = [
                {"Metric": "COGS materials", "Value": round(materials_total, 2)},
                {"Metric": "Variable costs", "Value": round(variable_total, 2)},
                {"Metric": "Production costs", "Value": round(production_total, 2)},
                {"Metric": "- Packaging per unit", "Value": round(packaging_unit, 2)},
                {"Metric": "- Equipment per unit", "Value": round(equipment_unit_total, 2)},
                {"Metric": "Unit cost total", "Value": round(materials_total + variable_total + production_total, 2)},
                {"Metric": "Target margin (%)", "Value": int(margin_pct)},
                {"Metric": "Suggested price", "Value": round((materials_total + variable_total + production_total) * (1 + margin_pct / 100), 2)},
                {"Metric": "Gross profit per unit", "Value": round((materials_total + variable_total + production_total) * (margin_pct / 100), 2)},
            ]
            st.markdown("### Detailed financials")
            st.dataframe(pd.DataFrame(metrics_rows), use_container_width=True, hide_index=True)
        elif pricing_mode == "Market-based":
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
        else:
            vbrows = [
                {"Metric": "Alt average cost", "Value": round(alt_avg, 2)},
                {"Metric": "Time value per unit", "Value": round(time_value, 2)},
                {"Metric": "Estimated value created", "Value": round(estimated_value, 2)},
                {"Metric": "Min profitable price", "Value": round(vb_min_profitable, 2)},
                {"Metric": "WTP typical", "Value": round(wtp_typical, 2)},
                {"Metric": "WTP max", "Value": round(wtp_max, 2)},
                {"Metric": "Recommended price", "Value": round(recommended_vb, 2)},
                {"Metric": "Sweet spot low", "Value": round(sweet_low_vb, 2)},
                {"Metric": "Sweet spot high", "Value": round(sweet_high_vb, 2)},
            ]
            st.markdown("### Value summary")
            st.dataframe(pd.DataFrame(vbrows), use_container_width=True, hide_index=True)

        # Star ratings pie chart
        stars = data.get("star_ratings", {}) or {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        total_reported = sum(int(v) for v in stars.values()) if all(str(v).isdigit() for v in stars.values()) else 0
        if total_reported != int(n_customers):
            vals = np.array([max(0, int(stars.get(str(k), 0))) for k in range(1, 6)], dtype=int)
            s = vals.sum()
            if s == 0:
                vals = np.array([0, 0, 0, int(n_customers * 0.4), int(n_customers * 0.6)], dtype=int)
                s = vals.sum()
            if s != n_customers:
                diff = int(n_customers) - int(s)
                vals[-1] += diff
            stars = {str(i + 1): int(vals[i]) for i in range(5)}
        star_df = pd.DataFrame({"Stars": ["1★", "2★", "3★", "4★", "5★"], "Count": [stars["1"], stars["2"], stars["3"], stars["4"], stars["5"]]})
        star_fig = px.pie(star_df, names="Stars", values="Count", title=f"Star Ratings Distribution ({int(n_customers)} reviews)")
        star_fig.update_traces(textinfo='label+percent')
        st.plotly_chart(star_fig, use_container_width=True)

    except Exception as e:
        st.error("AI response could not be parsed. Here is the raw output:")
        st.code(locals().get("raw", "<no raw output>"))
        st.exception(e)

st.markdown("---")
st.caption("Built with Streamlit and OpenAI • Cost plus, market based, and value based pricing paths with kid friendly help popovers. Deterministic mode is on (temperature=0) for consistent results.")

