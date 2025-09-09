# src/app.py
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv

import streamlit as st
import plotly.express as px

load_dotenv()

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Airbnb Market Dashboard",
    layout="wide",
)

DEFAULT_PARQUET = "data/clean_airbnb_listings.parquet"
CLEAN_PATH = os.getenv("OUT_PARQUET_PATH", DEFAULT_PARQUET)
RAW_CSV_FALLBACK = CLEAN_PATH.replace(".parquet", ".csv")

# ---------- DATA LOADER ----------
@st.cache_data(show_spinner=True)
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet(CLEAN_PATH)
    except Exception:
        # Fallback to CSV if parquet engine missing
        df = pd.read_csv(RAW_CSV_FALLBACK, low_memory=False)

    # Ensure expected naming (your cleaner already normalizes to snake_case)
    # We just guard here for safety.
    cols = {c.lower(): c for c in df.columns}
    # Minimal set used in the app:
    rename_map = {}
    for want in ["price","neighbourhood_group","room_type","availability_365",
                 "number_of_reviews","reviews_per_month","lat","long","id","host_id","host_name"]:
        if want not in df.columns and want in cols:
            rename_map[cols[want]] = want
    if rename_map:
        df = df.rename(columns=rename_map)

    # Coerce numeric columns if needed
    for c in ["price","availability_365","number_of_reviews","reviews_per_month","lat","long"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows without essential fields
    essential = [c for c in ["price","room_type","neighbourhood_group","lat","long"] if c in df.columns]
    if essential:
        df = df.dropna(subset=essential)

    return df

df = load_data()
if df.empty:
    st.error("No data loaded. Make sure you ran the cleaner and have a cleaned file.")
    st.stop()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Filters")

# Neighbourhood groups
if "neighbourhood_group" in df.columns:
    ng_options = sorted(df["neighbourhood_group"].dropna().unique().tolist())
    selected_ng = st.sidebar.multiselect("Neighbourhood group", ng_options, default=ng_options)
else:
    selected_ng = None

# Room types
if "room_type" in df.columns:
    rt_options = sorted(df["room_type"].dropna().unique().tolist())
    selected_rt = st.sidebar.multiselect("Room type", rt_options, default=rt_options)
else:
    selected_rt = None

# Price range (use robust bounds)
p_lo = float(df["price"].quantile(0.01)) if "price" in df.columns else 0.0
p_hi = float(df["price"].quantile(0.99)) if "price" in df.columns else 1000.0
price_range = st.sidebar.slider("Price range", min_value=0.0, max_value=max(p_hi, 1.0),
                                value=(p_lo, p_hi), step=1.0)

# Availability
a_min, a_max = 0, 365
if "availability_365" in df.columns:
    avail_range = st.sidebar.slider("Availability (days/year)", min_value=a_min, max_value=a_max,
                                    value=(a_min, a_max), step=1)
else:
    avail_range = (a_min, a_max)

# Reviews per month (optional finer filter)
if "reviews_per_month" in df.columns:
    rpm_hi = float(df["reviews_per_month"].quantile(0.99))
    rpm_range = st.sidebar.slider("Reviews per month", 0.0, max(0.5, rpm_hi), (0.0, max(0.5, rpm_hi)), 0.1)
else:
    rpm_range = (0.0, 999.0)

# Apply filters
mask = (
    (df["price"].between(price_range[0], price_range[1]))
    & (df["availability_365"].between(avail_range[0], avail_range[1]) if "availability_365" in df.columns else True)
    & (df["reviews_per_month"].between(rpm_range[0], rpm_range[1]) if "reviews_per_month" in df.columns else True)
)
if selected_ng is not None:
    mask &= df["neighbourhood_group"].isin(selected_ng)
if selected_rt is not None:
    mask &= df["room_type"].isin(selected_rt)

dff = df.loc[mask].copy()

# ---------- HEADER ----------
st.title("🏠 Airbnb Market Dashboard")
st.caption("Interactive analysis of listings, pricing, availability, and host activity.")

# ---------- KPI ROW ----------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Listings (filtered)", f"{len(dff):,}")
with col2:
    st.metric("Avg Price", f"{dff['price'].mean():.2f}" if "price" in dff else "—")
with col3:
    st.metric("Median Price", f"{dff['price'].median():.2f}" if "price" in dff else "—")
with col4:
    # Simple proxy: fewer available days => more booked; here show median availability
    if "availability_365" in dff:
        st.metric("Median Availability (days)", f"{dff['availability_365'].median():.0f}")
    else:
        st.metric("Median Availability (days)", "—")

st.divider()

# ---------- TABS ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Price Distribution",
    "Avg Price by Group",
    "Room Type Mix",
    "Correlations",
    "Map"
])

with tab1:
    st.subheader("Price Distribution")
    if "price" in dff:
        dplot = dff.copy()
        dplot["price_clip"] = dplot["price"].clip(upper=dplot["price"].quantile(0.99))
        fig = px.histogram(dplot, x="price_clip", nbins=50, marginal="box")
        fig.update_layout(xaxis_title="Price (clipped @99th pct)", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Price column not found.")

with tab2:
    st.subheader("Average Price by Neighbourhood Group")
    need = {"neighbourhood_group","price"}
    if need.issubset(dff.columns):
        s = (
            dff.groupby("neighbourhood_group")["price"]
               .mean()
               .sort_values(ascending=False)
               .round(2)
        )
        fig = px.bar(s, labels={"value":"Average Price","index":"Neighbourhood Group"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(s.rename("avg_price"))
    else:
        st.info("Required columns not available.")

with tab3:
    st.subheader("Room Type Distribution")
    if "room_type" in dff.columns:
        counts = dff["room_type"].value_counts()
        fig = px.pie(values=counts.values, names=counts.index, hole=0.35)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(counts.rename("count"))
    else:
        st.info("room_type column not found.")

with tab4:
    st.subheader("Correlations")
    cols = [c for c in ["price","number_of_reviews","reviews_per_month","availability_365"] if c in dff.columns]
    if cols:
        corr = dff[cols].corr(numeric_only=True)
        fig = px.imshow(corr, text_auto=True, aspect="auto")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(corr)
    else:
        st.info("Not enough numeric columns to compute correlations.")

with tab5:
    st.subheader("Listing Map (sample)")
    need = {"lat","long","price"}
    if need.issubset(dff.columns) and len(dff) > 0:
        sample_n = st.slider("Sample size for map", 500, min(10000, len(dff)), min(5000, len(dff)))
        smp = dff.sample(sample_n, random_state=42)[["lat","long","price","neighbourhood_group","room_type"]].copy()
        # Rename for Pydeck/Streamlit map (expects 'lat' and 'lon' or use pydeck directly)
        smp = smp.rename(columns={"long": "lon"})
        st.map(smp, latitude="lat", longitude="lon", size=3)
        st.caption("Tip: zoom and pan the map to explore clusters.")
        st.dataframe(smp.head(10))
    else:
        st.info("Missing lat/long/price columns for mapping.")

# ---------- TOP HOSTS (bonus table) ----------
st.divider()
st.subheader("Top Hosts by Listing Count (filtered)")
need = {"host_id","host_name","id"}
if need.issubset(dff.columns):
    top = (
        dff.groupby(["host_id","host_name"])["id"]
           .count()
           .sort_values(ascending=False)
           .head(15)
           .rename("listings_count")
           .reset_index()
    )
    st.dataframe(top)
else:
    st.info("Host columns not available.")
