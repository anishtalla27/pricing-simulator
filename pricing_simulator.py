import streamlit as st
import openai
import plotly.express as px
import json
from openai import OpenAI


# Use Streamlit secrets for the API key
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

st.set_page_config(page_title="Pricing Simulator", page_icon=":rocket:", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at center, #175e88 0%, #276da0 60%, #eaf6fb 100%);
        min-height: 100vh;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# HEADER with fun emoji and high-tech feel
st.markdown(
    """
    <div style='text-align: center; font-size: 38px; font-weight: bold; color: #13c0ff;'>
        🚀 <span style='color:#13c0ff;'>Pricing Simulator Lab</span> 🛒
    </div>
    <div style='text-align: center; font-size: 18px; color: #444;'>  
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# PRODUCT DETAILS SECTION
st.subheader("📝 Product Details")
product_name = st.text_input("What will you call your product?", placeholder="EcoGlow Water Bottle")
product_desc = st.text_area("Describe your product!", placeholder="A reusable water bottle that glows in the dark and keeps drinks cold.")
audience = st.text_input("Who is this product for?", placeholder="e.g., kids, teens, parents")

st.markdown("")

# LOCATION
st.subheader("📍 Customer Location")
city = st.text_input("City", placeholder="e.g., Dallas")
state = st.text_input("State", placeholder="e.g., Texas")

st.markdown("---")

pricing_method = st.selectbox(
    "💸 Which Pricing Method Do You Want to Use?",
    ("Cost-Plus", "Market-Based"),
    help="Cost-Plus: Set your price based on your costs. Market-Based: Set your price based on the competition."
)

# --- DYNAMIC COMPETITOR INPUTS ---
if "competitors" not in st.session_state:
    st.session_state.competitors = []

def add_competitor():
    st.session_state.competitors.append({"name": "", "price": 0.0, "details": ""})

def clear_competitors():
    st.session_state.competitors = []

if pricing_method == "Cost-Plus":
    st.subheader("🔧 Cost-Plus Pricing Setup")
    with st.expander("What is Cost-Plus Pricing?"):
        st.info("Add up all the costs it takes to make your product (like materials, packaging, and marketing), then add a little extra on top for profit. This way, you know you’re covering your expenses and making money!")
    prod_cost = st.number_input("Production Cost per Unit ($)", min_value=0.0, value=1.0)
    marketing_cost = st.number_input("Marketing Cost per Unit ($)", min_value=0.0, value=0.5)
    packaging_cost = st.number_input("Packaging Cost per Unit ($)", min_value=0.0, value=0.3)
    transport_cost = st.number_input("Transport Cost per Unit ($)", min_value=0.0, value=0.2)
    other_cost = st.number_input("Other Costs per Unit ($)", min_value=0.0, value=0.0)
    margin = st.slider("Profit Margin (%)", min_value=5, max_value=100, value=40)
    total_cost = prod_cost + marketing_cost + packaging_cost + transport_cost + other_cost
    price = total_cost * (1 + margin/100)
    st.success(f"💡 Suggested Price: **${price:.2f}**")
elif pricing_method == "Market-Based":
    st.subheader("🏆 Market-Based Pricing Setup")
    with st.expander("What is Market-Based Pricing?"):
        st.info("Set your price by looking at what other, similar products are selling for. You check out your competition and choose a price that helps you stand out or fit in with the market.")
    st.markdown("#### 🏢 Add Your Competitors")
    col_add, col_clear = st.columns([2, 1])
    with col_add:
        if st.button("➕ Add Competitor"):
            add_competitor()
    with col_clear:
        if st.button("🗑️ Clear All"):
            clear_competitors()
    for idx, competitor in enumerate(st.session_state.competitors):
        st.markdown(f"<b>Competitor #{idx+1}</b>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2,1,3])
        with c1:
            name = st.text_input("Name (optional)", competitor.get("name", ""), key=f"name_{idx}")
        with c2:
            price_val = st.number_input("Price", value=competitor.get("price", 0.0), key=f"price_{idx}")
        with c3:
            details = st.text_input("Product Details (optional)", competitor.get("details", ""), key=f"details_{idx}")
        st.session_state.competitors[idx] = {"name": name, "price": price_val, "details": details}
    your_price = st.number_input("Your Product Price ($)", min_value=0.0, value=1.0)
    price = your_price

n_customers = st.slider("How many customer responses do you want to simulate?", min_value=100, max_value=5000, value=1000, step=100, help="More customers = more data!")

def build_competitor_prompt(competitors):
    if not competitors or all(c["price"] == 0.0 for c in competitors):
        return "There are no clear competitors in the market."
    lines = []
    for c in competitors:
        if c["price"] and c["price"] > 0:
            desc = f'Price: ${c["price"]:.2f}'
            if c["name"]:
                desc = f'Name: {c["name"]}, {desc}'
            if c["details"]:
                desc = f'{desc}, Details: {c["details"]}'
            lines.append(desc)
    if not lines:
        return "There are no clear competitors in the market."
    return "Here are the main competitors in the market:\n" + "\n".join(lines)

def generate_customer_responses(product_name, product_desc, price, n_customers, pricing_method, city, state, competitors_str):
    prompt = f"""
    Imagine {n_customers} potential customers from {city}, {state} for a product called "{product_name}" ({product_desc}).
    The product is being sold at ${price:.2f} using the {pricing_method} pricing method.
    Audience: {audience}.
    {competitors_str}
    Considering typical incomes and consumer attitudes in {city}, {state}, what percentage of customers would buy it at this price?
    What is the general customer sentiment?

    Please generate around 8 sample customer comments. Most comments should include easy, realistic suggestions for improvement that a young student entrepreneur could actually try (like making the product in more colors, making it cheaper, adding a fun feature, or improving packaging). A couple of comments can be positive or encouraging, but do not include advanced or expensive business advice. All suggestions should be friendly and simple enough for a 10-14 year old to understand and possibly do.

    Provide your answer as a JSON: {{"buy_percentage": ..., "sentiment": "...", "comments": ["...", "...", "..."]}}
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )
    content = response.choices[0].message.content
    return content

st.markdown("---")
st.markdown("### 🎲 Run Your Simulation")
if st.button("🧪 Simulate Customer Responses"):
    if not product_name or not price or not city or not state:
        st.warning("⚠️ Please enter product name, price, city, and state.")
    else:
        st.info("Simulating responses with AI. Please wait... 🤖")
        competitors_str = build_competitor_prompt(st.session_state.competitors) if pricing_method == "Market-Based" else ""
        ai_result = generate_customer_responses(
            product_name, product_desc, price, n_customers, pricing_method, city, state, competitors_str
        )
        try:
            ai_result_clean = ai_result.strip().strip("```json").strip("```").strip()
            ai_json = json.loads(ai_result_clean)
            buy_percentage = ai_json.get("buy_percentage", 0)
            sentiment = ai_json.get("sentiment", "")
            comments = ai_json.get("comments", [])

            st.markdown("## 📊 Customer Purchase Results")
            col1, col2 = st.columns(2)
            col1.metric("Buy Percentage", f"{buy_percentage}%")
            col2.metric("Est. Buyers", f"{int(buy_percentage * n_customers / 100)} / {n_customers}")

            st.success(f"**General Sentiment:** {sentiment}")

            fig = px.pie(
                names=["Willing to Buy", "Not Willing to Buy"],
                values=[buy_percentage, 100 - buy_percentage],
                color_discrete_sequence=["#13c0ff", "#ffd700"],
                title="Customer Willingness to Buy"
            )
            st.plotly_chart(fig)

            if pricing_method == "Market-Based" and st.session_state.competitors:
                st.subheader("🏢 Market Competitors")
                comp_table = [
                    {
                        "Name": c["name"] if c["name"] else "(N/A)",
                        "Price": c["price"] if c["price"] else "(N/A)",
                        "Details": c["details"] if c["details"] else "(N/A)"
                    }
                    for c in st.session_state.competitors if c["price"]
                ]
                if comp_table:
                    st.table(comp_table)

            st.markdown("### 💬 Sample Customer Comments")
            if comments:
                for i, comment in enumerate(comments):
                    st.info(f"🗣️  {comment}")
            else:
                st.write("No comments available.")

        except Exception as e:
            st.error("There was a problem parsing the AI's response. Here is the raw output:")
            st.code(ai_result)

st.markdown("---")
st.caption("Made with Streamlit & OpenAI | For learning and fun! ✨")

