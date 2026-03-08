import streamlit as st
from app.data_loader import (
    fetch_data,
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers
)
from app.data_processor import (
    process_lap_data,
    process_stints,
    process_pit_stops,
    build_driver_color_map,
    process_tyre_degradation,
    process_sector_times,
)
from app.visualizer import (
    plot_lap_times,
    plot_tire_strategy,
    plot_pit_stop,
    plot_tyre_degradation,
    plot_sector_times,
)

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

st.title("🏎️ Formula 1 Strategy Dashboard")
st.markdown("Built By Ojas Pawar")

col1, col2 = st.columns(2)

with col1:
    available_years = [2023, 2024, 2025]
    selected_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1)

    @st.cache_data
    def fetch_all_meetings(year):
        return fetch_data("meetings", {"year": year})

    all_meetings = fetch_all_meetings(selected_year)

    if all_meetings.empty:
        st.error("No meetings found for this year.")
        st.stop()

    available_countries = sorted(all_meetings["country_name"].dropna().unique())
    selected_country = st.selectbox("Select Country", available_countries)

    filtered_meetings = all_meetings[all_meetings["country_name"] == selected_country].copy()
    filtered_meetings["label"] = filtered_meetings["meeting_name"] + " - " + filtered_meetings["location"]
    filtered_meetings = filtered_meetings.sort_values(by="meeting_key", ascending=False)

with col2:
    selected_meeting = st.selectbox("Select Grand Prix", filtered_meetings["label"], disabled=True)
    selected_meeting_key = filtered_meetings.loc[
        filtered_meetings["label"] == selected_meeting, "meeting_key"
    ].values[0]
    sessions = fetch_sessions(selected_meeting_key)
    selected_session = st.selectbox("Select Session", sessions["label"])
    sessions["session_type"] = sessions["label"].str.extract(r"^(.*?)\s\(")
    selected_session_type = sessions.loc[sessions["label"] == selected_session, "session_type"].values[0]
    selected_session_key = sessions.loc[sessions["label"] == selected_session, "session_key"].values[0]

st.markdown(f"### 🏁 Session Overview: `{selected_session}`")
with st.expander("📋 Session Details", expanded=False):
    st.write(f"**Meeting Key:** {selected_meeting_key}")
    st.write(f"**Session Key:** {selected_session_key}")

# Fetch driver info once — shared across all sections
driver_df = fetch_drivers(selected_session_key)
driver_df["driver_number"] = driver_df["driver_number"].astype(str)
driver_color_map = build_driver_color_map(driver_df)
driver_info = driver_df[["driver_number", "name_acronym"]]

# Fetch raw data once — reused by multiple sections
lap_df = fetch_laps(selected_session_key)
stints = fetch_stints(selected_session_key)

# ── Lap Times ─────────────────────────────────────────────────────────────────
with st.expander(f"📈 Lap Times — {selected_session_type} · {selected_country} {selected_year}", expanded=True):
    processed_df = process_lap_data(lap_df)
    processed_df["driver_number"] = processed_df["driver_number"].astype(str)
    processed_df = processed_df.merge(driver_info, on="driver_number", how="left")

    if processed_df.empty:
        st.warning("No lap time data found.")
    else:
        all_drivers = sorted(processed_df["name_acronym"].dropna().unique())
        selected_lap_drivers = st.multiselect(
            "Filter drivers", all_drivers, default=all_drivers, key="lap_drivers"
        )
        filtered_laps = processed_df[processed_df["name_acronym"].isin(selected_lap_drivers)]
        fig = plot_lap_times(filtered_laps, driver_color_map)
        if fig:
            st.plotly_chart(fig, width="stretch")

# ── Tire Strategy ─────────────────────────────────────────────────────────────
with st.expander(f"🛞 Tyre Strategy — {selected_session_type} · {selected_country} {selected_year}", expanded=True):
    stints_df = process_stints(stints)
    stints_df["driver_number"] = stints_df["driver_number"].astype(str)
    stints_df = stints_df.merge(driver_info, on="driver_number", how="left")

    if stints_df.empty:
        st.warning("No tire strategy data found.")
    else:
        fig = plot_tire_strategy(stints_df, driver_color_map)
        if fig:
            st.plotly_chart(fig, width="stretch")

# ── Pit Stops ─────────────────────────────────────────────────────────────────
with st.expander(f"⏱ Pit Stop Durations — {selected_session_type} · {selected_country} {selected_year}", expanded=True):
    pit_stop = fetch_pit_stop(selected_session_key)
    pit_stop_df = process_pit_stops(pit_stop)
    pit_stop_df["driver_number"] = pit_stop_df["driver_number"].astype(str)
    pit_stop_df = pit_stop_df.merge(driver_info, on="driver_number", how="left")

    if pit_stop_df.empty:
        st.warning("No pit stop data found.")
    else:
        all_pit_drivers = sorted(pit_stop_df["name_acronym"].dropna().unique())
        selected_pit_drivers = st.multiselect(
            "Filter drivers", all_pit_drivers, default=all_pit_drivers, key="pit_drivers"
        )
        filtered_pit = pit_stop_df[pit_stop_df["name_acronym"].isin(selected_pit_drivers)]
        fig = plot_pit_stop(filtered_pit, driver_color_map)
        if fig:
            st.plotly_chart(fig, width="stretch")

# ── Tyre Degradation ──────────────────────────────────────────────────────────
with st.expander(f"📉 Tyre Degradation — {selected_session_type} · {selected_country} {selected_year}", expanded=True):
    deg_df = process_tyre_degradation(lap_df, stints)
    if deg_df.empty:
        st.warning("No tyre degradation data found.")
    else:
        deg_df["driver_number"] = deg_df["driver_number"].astype(str)
        deg_df = deg_df.merge(driver_info, on="driver_number", how="left")
        fig = plot_tyre_degradation(deg_df, driver_color_map)
        if fig:
            st.plotly_chart(fig, width="stretch")

# ── Sector Times ──────────────────────────────────────────────────────────────
with st.expander(f"⏱️ Sector Times — {selected_session_type} · {selected_country} {selected_year}", expanded=True):
    sector_df = process_sector_times(lap_df)
    if sector_df.empty:
        st.warning("No sector time data found.")
    else:
        sector_df["driver_number"] = sector_df["driver_number"].astype(str)
        sector_df = sector_df.merge(driver_info, on="driver_number", how="left")

        all_sector_drivers = sorted(sector_df["name_acronym"].dropna().unique())
        selected_sector_drivers = st.multiselect(
            "Filter drivers", all_sector_drivers, default=all_sector_drivers, key="sector_drivers"
        )
        filtered_sector = sector_df[sector_df["name_acronym"].isin(selected_sector_drivers)]
        fig = plot_sector_times(filtered_sector, driver_color_map)
        if fig:
            st.plotly_chart(fig, width="stretch")

if processed_df.empty:
    st.info("Lap data is not available for this session.")
