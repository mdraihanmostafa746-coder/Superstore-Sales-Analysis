import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Superstore Sales Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main {background-color: #f7f9fc;}
        .block-container {padding-top: 1.7rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e8edf4;
            padding: 16px 18px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(20, 35, 60, 0.04);
        }
        div[data-testid="stMetricLabel"] p {font-size: 0.9rem;}
        h1, h2, h3 {color: #172b4d;}
    </style>
    """,
    unsafe_allow_html=True,
)

REQUIRED_COLUMNS = [
    "Order Date", "Ship Mode", "Segment", "Region", "Category",
    "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit"
]


# ---------------------------------------------------------
# Data loading and preparation
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    from io import BytesIO

    data = pd.read_csv(BytesIO(file_bytes))
    return data


def prepare_data(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data.columns = data.columns.str.strip()

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(
            "The uploaded CSV is missing these required columns: "
            + ", ".join(missing)
        )

    data["Order Date"] = pd.to_datetime(data["Order Date"], errors="coerce")
    for column in ["Sales", "Quantity", "Discount", "Profit"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(
        subset=["Order Date", "Sales", "Quantity", "Discount", "Profit"]
    )
    return data


st.sidebar.title("📊 Superstore Analytics")
st.sidebar.caption("Explore sales, profit and product performance.")
uploaded_file = st.sidebar.file_uploader(
    "Upload Superstore CSV",
    type=["csv"],
    help="Upload the samplesuperstore.csv dataset used in the analysis notebook.",
)

default_path = Path("data") / "samplesuperstore.csv"

try:
    if uploaded_file is not None:
        raw_df = load_csv(uploaded_file.getvalue())
        data_source = uploaded_file.name
    elif default_path.exists():
        raw_df = pd.read_csv(default_path)
        data_source = str(default_path)
    else:
        st.title("Superstore Sales Analysis")
        st.info(
            "Upload your `samplesuperstore.csv` file using the sidebar, "
            "or place it at `data/samplesuperstore.csv`."
        )
        st.stop()

    df = prepare_data(raw_df)
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.stop()

if df.empty:
    st.error("No usable rows remain after parsing the required columns.")
    st.stop()


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("Superstore Sales Analysis")
st.markdown(
    "An interactive dashboard to explore **sales, profitability, "
    "regional performance and product-level insights**."
)
st.caption(
    f"Data source: {data_source}  •  "
    f"{len(df):,} usable records  •  {df['Order Date'].min():%d %b %Y} "
    f"to {df['Order Date'].max():%d %b %Y}"
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("Dashboard Filters")

def add_all_option(values):
    return ["All"] + sorted(values.dropna().astype(str).unique().tolist())


regions = st.sidebar.multiselect(
    "Region",
    options=sorted(df["Region"].dropna().astype(str).unique()),
    default=sorted(df["Region"].dropna().astype(str).unique()),
)
categories = st.sidebar.multiselect(
    "Category",
    options=sorted(df["Category"].dropna().astype(str).unique()),
    default=sorted(df["Category"].dropna().astype(str).unique()),
)
segments = st.sidebar.multiselect(
    "Segment",
    options=sorted(df["Segment"].dropna().astype(str).unique()),
    default=sorted(df["Segment"].dropna().astype(str).unique()),
)
ship_modes = st.sidebar.multiselect(
    "Ship Mode",
    options=sorted(df["Ship Mode"].dropna().astype(str).unique()),
    default=sorted(df["Ship Mode"].dropna().astype(str).unique()),
)

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

filtered = df.copy()
if regions:
    filtered = filtered[filtered["Region"].isin(regions)]
if categories:
    filtered = filtered[filtered["Category"].isin(categories)]
if segments:
    filtered = filtered[filtered["Segment"].isin(segments)]
if ship_modes:
    filtered = filtered[filtered["Ship Mode"].isin(ship_modes)]

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Order Date"].dt.date.between(start_date, end_date)
    ]
elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
    filtered = filtered[filtered["Order Date"].dt.date >= date_range[0]]

if filtered.empty:
    st.warning("No records match the selected filters. Change the filters to continue.")
    st.stop()


# ---------------------------------------------------------
# KPI cards
# ---------------------------------------------------------
total_sales = filtered["Sales"].sum()
total_profit = filtered["Profit"].sum()
total_quantity = filtered["Quantity"].sum()
order_count = (
    filtered["Order ID"].nunique()
    if "Order ID" in filtered.columns
    else len(filtered)
)
profit_margin = (total_profit / total_sales * 100) if total_sales else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sales", f"${total_sales:,.2f}")
k2.metric("Total Profit", f"${total_profit:,.2f}")
k3.metric("Orders", f"{order_count:,}")
k4.metric("Units Sold", f"{total_quantity:,}")
k5.metric("Profit Margin", f"{profit_margin:.2f}%")

st.divider()


# ---------------------------------------------------------
# Sales overview
# ---------------------------------------------------------
st.subheader("Sales Overview")
left, right = st.columns(2)

with left:
    category_sales = (
        filtered.groupby("Category", as_index=False)["Sales"]
        .sum()
        .sort_values("Sales", ascending=False)
    )
    fig = px.bar(
        category_sales,
        x="Category",
        y="Sales",
        color="Category",
        title="Total Sales by Category",
        text_auto=".2s",
    )
    fig.update_layout(showlegend=False, yaxis_title="Sales ($)", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

with right:
    region_sales = (
        filtered.groupby("Region", as_index=False)["Sales"]
        .sum()
        .sort_values("Sales", ascending=False)
    )
    fig = px.bar(
        region_sales,
        x="Region",
        y="Sales",
        color="Region",
        title="Total Sales by Region",
        text_auto=".2s",
    )
    fig.update_layout(showlegend=False, yaxis_title="Sales ($)", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# Monthly sales trend
monthly_sales = (
    filtered.set_index("Order Date")
    .resample("MS")["Sales"]
    .sum()
    .reset_index()
)
fig = px.line(
    monthly_sales,
    x="Order Date",
    y="Sales",
    markers=True,
    title="Monthly Sales Trend",
)
fig.update_layout(xaxis_title="Order Month", yaxis_title="Sales ($)")
st.plotly_chart(fig, use_container_width=True)

st.divider()


# ---------------------------------------------------------
# Profitability analysis
# ---------------------------------------------------------
st.subheader("Profitability Analysis")
left, right = st.columns(2)

with left:
    category_profit = (
        filtered.groupby("Category", as_index=False)["Profit"]
        .sum()
        .sort_values("Profit", ascending=False)
    )
    fig = px.bar(
        category_profit,
        x="Category",
        y="Profit",
        color="Profit",
        color_continuous_scale="RdYlGn",
        title="Total Profit by Category",
        text_auto=".2s",
    )
    fig.update_layout(xaxis_title="", yaxis_title="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)

with right:
    region_profit = (
        filtered.groupby("Region", as_index=False)["Profit"]
        .sum()
        .sort_values("Profit", ascending=False)
    )
    fig = px.bar(
        region_profit,
        x="Region",
        y="Profit",
        color="Profit",
        color_continuous_scale="RdYlGn",
        title="Total Profit by Region",
        text_auto=".2s",
    )
    fig.update_layout(xaxis_title="", yaxis_title="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)

fig = px.scatter(
    filtered,
    x="Discount",
    y="Profit",
    color="Category",
    hover_data=["Product Name", "Sales", "Quantity"],
    opacity=0.65,
    title="Discount vs Profit",
)
fig.update_layout(xaxis_title="Discount", yaxis_title="Profit ($)")
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "This chart shows association between discount and profit; "
    "it does not establish that discounts directly cause lower profit."
)

st.divider()


# ---------------------------------------------------------
# Product performance
# ---------------------------------------------------------
st.subheader("Product Performance")

top_sales = (
    filtered.groupby("Product Name", as_index=False)["Sales"]
    .sum()
    .nlargest(10, "Sales")
    .sort_values("Sales")
)
top_profit = (
    filtered.groupby("Product Name", as_index=False)["Profit"]
    .sum()
    .nlargest(10, "Profit")
    .sort_values("Profit")
)
bottom_profit = (
    filtered.groupby("Product Name", as_index=False)["Profit"]
    .sum()
    .nsmallest(10, "Profit")
    .sort_values("Profit")
)

tab1, tab2, tab3 = st.tabs(
    ["Top Products by Sales", "Top Products by Profit", "Lowest Products by Profit"]
)

with tab1:
    fig = px.bar(
        top_sales, x="Sales", y="Product Name", orientation="h",
        title="Top 10 Products by Sales", text_auto=".2s"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = px.bar(
        top_profit, x="Profit", y="Product Name", orientation="h",
        title="Top 10 Products by Profit", text_auto=".2s",
        color="Profit", color_continuous_scale="Greens"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = px.bar(
        bottom_profit, x="Profit", y="Product Name", orientation="h",
        title="10 Products with Lowest Total Profit", text_auto=".2s",
        color="Profit", color_continuous_scale="Reds"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()


# ---------------------------------------------------------
# Detailed data explorer and export
# ---------------------------------------------------------
st.subheader("Data Explorer")
search_text = st.text_input("Search product name", placeholder="Type a product name...")
table_df = filtered.copy()

if search_text.strip():
    table_df = table_df[
        table_df["Product Name"].astype(str).str.contains(
            search_text.strip(), case=False, na=False
        )
    ]

display_columns = [
    col for col in [
        "Order Date", "Order ID", "Customer Name", "Region", "Category",
        "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit"
    ] if col in table_df.columns
]
st.dataframe(
    table_df[display_columns],
    use_container_width=True,
    hide_index=True,
)

csv_data = table_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download filtered data (CSV)",
    data=csv_data,
    file_name="superstore_filtered_data.csv",
    mime="text/csv",
)

st.caption(
    "Built with Python, Pandas, Plotly and Streamlit. "
    "All dashboard metrics and charts update based on the selected filters."
)
