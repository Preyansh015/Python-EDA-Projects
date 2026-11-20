from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Ola Ride Bookings EDA Dashboard",
    page_icon="🚖",
    layout="wide",
)

sns.set_theme(style="whitegrid")


@st.cache_data
def load_and_clean_data(csv_path: str = "rideBookings.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Strip extra quotation marks from IDs
    for col in ["Booking ID", "Customer ID"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('"', "", regex=False).str.strip()

    # Parse Date, Time, and Hour
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce").dt.hour

    # Normalize cancellation & incomplete flag columns
    flag_cols = [
        "Cancelled Rides by Customer",
        "Cancelled Rides by Driver",
        "Incomplete Rides",
    ]
    for col in flag_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    return df


# Load data with friendly fallback if CSV is not in the working directory
data_file = Path("rideBookings.csv")
if not data_file.exists():
    st.error(
        "`rideBookings.csv` was not found in the current folder. "
        "Place `rideBookings.csv` alongside `app.py` to run the dashboard."
    )
    st.stop()

df_raw = load_and_clean_data(str(data_file))

# Header section
col_title, col_gif = st.columns([3, 1.3], vertical_alignment="center")
with col_title:
    st.title("🚖 Ola Ride Bookings: Exploratory Data Analysis")
    st.markdown(
        "Interactive exploration of booking fulfillment, cancellation drivers, "
        "fleet revenue, fare-distance relationships, and turnaround times (`VTAT` & `CTAT`)."
    )
with col_gif:
    gif_path = Path("Gemini_Generated_Gif_khnncfkhnncfkhnn.gif")
    if gif_path.exists():
        st.image(str(gif_path), use_container_width=True)

# Sidebar filters
st.sidebar.header("🎛️ Filter Bookings")

vehicle_options = sorted(df_raw["Vehicle Type"].dropna().unique().tolist())
selected_vehicles = st.sidebar.multiselect(
    "Vehicle Type",
    options=vehicle_options,
    default=vehicle_options,
)

status_options = sorted(df_raw["Booking Status"].dropna().unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Booking Status",
    options=status_options,
    default=status_options,
)

payment_options = sorted(df_raw["Payment Method"].dropna().unique().tolist())
selected_payments = st.sidebar.multiselect(
    "Payment Method (Started Rides)",
    options=payment_options,
    default=payment_options,
)

hour_range = st.sidebar.slider(
    "Hour of Day (0–23)",
    min_value=0,
    max_value=23,
    value=(0, 23),
)

# Apply filters (keep rows where Payment Method is NaN unless user restricts payment filter)
df = df_raw[
    df_raw["Vehicle Type"].isin(selected_vehicles)
    & df_raw["Booking Status"].isin(selected_statuses)
    & df_raw["Hour"].between(hour_range[0], hour_range[1], inclusive="both")
]

if len(selected_payments) < len(payment_options):
    df = df[df["Payment Method"].isin(selected_payments)]

if df.empty:
    st.warning("No bookings match the selected filter combination. Adjust your filters on the left.")
    st.stop()

# Top-level KPI row
total_bookings = len(df)
completed_count = (df["Booking Status"] == "Completed").sum()
driver_cancel_count = (df["Booking Status"] == "Cancelled by Driver").sum()
completion_rate = (completed_count / total_bookings) * 100
driver_cancel_rate = (driver_cancel_count / total_bookings) * 100
avg_fare = df["Booking Value"].mean()
avg_vtat = df["Avg VTAT"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Bookings", f"{total_bookings:,}")
k2.metric("Completion Rate", f"{completion_rate:.1f}%", f"{completed_count:,} rides")
k3.metric("Driver Cancellations", f"{driver_cancel_rate:.1f}%", f"{driver_cancel_count:,} rides", delta_color="inverse")
k4.metric("Avg Booking Value", f"₹{avg_fare:,.2f}" if pd.notna(avg_fare) else "N/A")
k5.metric("Avg Driver Wait (VTAT)", f"{avg_vtat:.2f} min" if pd.notna(avg_vtat) else "N/A")

st.divider()

# Tabs aligned with Business Questions 1-4 & Conclusion
tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Cancellations & Incomplete Rides",
    "2️⃣ Fleet Revenue & Pricing",
    "3️⃣ Wait Times (VTAT vs. CTAT)",
    "4️⃣ Recommendations & Data",
])

with tab1:
    st.subheader("Are incomplete or cancelled rides driven by vehicle type, payment method, fare, or route?")

    c1, c2 = st.columns([1.1, 1.4])
    with c1:
        status_counts = df["Booking Status"].value_counts()
        fig, ax = plt.subplots(figsize=(6, 4))
        status_counts.sort_values().plot(kind="barh", ax=ax, color="#4C78A8")
        ax.set_title("Booking Count by Status")
        ax.set_xlabel("Number of Bookings")
        ax.set_ylabel("")
        st.pyplot(fig)
        plt.close(fig)

    with c2:
        inc_by_veh = df[df["Booking Status"] == "Incomplete"]["Vehicle Type"].value_counts()
        if not inc_by_veh.empty:
            fig, ax = plt.subplots(figsize=(6, 4))
            explode = [0.08] + [0.0] * (len(inc_by_veh) - 1)
            ax.pie(
                inc_by_veh.values,
                labels=inc_by_veh.index,
                autopct="%1.1f%%",
                explode=explode,
                startangle=140,
            )
            ax.set_title("Incomplete Rides Share by Vehicle Type")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No incomplete rides in the current filter selection.")

    st.markdown("**Normalized Booking Status (%) by Vehicle Type**")
    veh_ct = (pd.crosstab(df["Vehicle Type"], df["Booking Status"], normalize="index") * 100).round(2)
    st.dataframe(veh_ct, use_container_width=True)

    col_pay, col_fare = st.columns(2)
    with col_pay:
        st.markdown("**Started Rides Outcome (%) by Payment Method**")
        started_df = df[df["Payment Method"].notna()]
        if not started_df.empty:
            pay_ct = (
                pd.crosstab(started_df["Payment Method"], started_df["Booking Status"], normalize="index") * 100
            ).round(2)
            st.dataframe(pay_ct, use_container_width=True)
        else:
            st.info("No started rides with payment method in selection.")

    with col_fare:
        st.markdown("**Booking Value (Mean & Median) by Status**")
        fare_stats = df.groupby("Booking Status")["Booking Value"].agg(["count", "mean", "median"]).round(2)
        st.dataframe(fare_stats, use_container_width=True)

with tab2:
    st.subheader("Fleet Revenue, Pickup Location Fares & Distance Correlation")

    col_rev, col_loc = st.columns(2)
    with col_rev:
        rev_by_veh = df.groupby("Vehicle Type")["Booking Value"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        rev_by_veh.plot(kind="bar", ax=ax, color="#2E8B57")
        ax.set_title("Total Booking Value by Vehicle Type")
        ax.set_ylabel("Total Booking Value (₹)")
        ax.set_xlabel("")
        plt.xticks(rotation=30, ha="right")
        st.pyplot(fig)
        plt.close(fig)

    with col_loc:
        loc_df = (
            df.groupby("Pickup Location")["Booking Value"]
            .agg(ride_count="count", avg_fare="mean")
            .dropna(subset=["avg_fare"])
            .sort_values("avg_fare", ascending=False)
            .head(10)
        )
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        loc_df["avg_fare"].plot(kind="bar", ax=ax, color="#1F77B4")
        ax.set_title("Top 10 Pickup Locations by Average Booking Value")
        ax.set_ylabel("Average Booking Value (₹)")
        ax.set_xlabel("")
        plt.xticks(rotation=35, ha="right")
        st.pyplot(fig)
        plt.close(fig)

    st.markdown("**Ride Distance vs. Booking Value Correlation**")
    valid_pair = df[["Ride Distance", "Booking Value"]].dropna()
    if len(valid_pair) > 1:
        corr_val = valid_pair["Ride Distance"].corr(valid_pair["Booking Value"])
        st.write(f"Pearson Correlation Coefficient (`r`): **`{corr_val:.4f}`**")
        sample_pair = valid_pair.sample(min(len(valid_pair), 3000), random_state=42)
        fig, ax = plt.subplots(figsize=(8, 3.8))
        sns.scatterplot(data=sample_pair, x="Ride Distance", y="Booking Value", alpha=0.35, ax=ax)
        ax.set_title("Sampled Ride Distance vs. Booking Value (up to 3,000 points)")
        st.pyplot(fig)
        plt.close(fig)

with tab3:
    st.subheader("How do driver arrival time (Avg VTAT) and trip duration (Avg CTAT) differ by status?")

    tat_df = df.groupby("Booking Status")[["Avg VTAT", "Avg CTAT"]].mean().round(2)
    col_tat_tbl, col_tat_chart = st.columns([1, 1.4])

    with col_tat_tbl:
        st.markdown("**Mean Turnaround Times (Minutes)**")
        st.dataframe(tat_df, use_container_width=True)

    with col_tat_chart:
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        tat_df.plot(kind="bar", ax=ax)
        ax.set_title("Average VTAT & CTAT by Booking Status")
        ax.set_ylabel("Minutes")
        ax.set_xlabel("")
        plt.xticks(rotation=25, ha="right")
        st.pyplot(fig)
        plt.close(fig)

with tab4:
    st.subheader("Key Takeaways & Business Recommendations")
    st.markdown(
        """
        - **Curb Driver Cancellations First:** Driver cancellations represent the largest single share of unfulfilled rides (~18% overall). Peak-hour completion incentives and clearer cancellation guardrails can recover lost demand.
        - **Reduce Pickup Wait Times (`Avg VTAT`):** Customer-cancelled rides show noticeably higher average driver arrival wait times (~12.5 min) than completed rides (~8.5 min). Tighter peak dispatch matching and live ETA updates help prevent rider drop-offs.
        - **Protect High-Volume Fleet Supply:** **Auto** leads cumulative booking value driven by high ride volume, making Auto supply and fast dispatch a high-leverage operational focus.
        """
    )

    st.markdown("**Filtered Dataset Preview**")
    st.dataframe(df.head(100), use_container_width=True)
