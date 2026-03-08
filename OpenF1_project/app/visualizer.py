import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import pandas as pd
import numpy as np


# ── Shared theme ─────────────────────────────────────────────────────────────

_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#161b22",
    font=dict(family="'Segoe UI', Arial, sans-serif", color="#c9d1d9", size=13),
    title_font=dict(size=20, color="#f0f6fc", family="'Segoe UI', Arial, sans-serif"),
    margin=dict(t=80, b=60, l=70, r=40),
    hoverlabel=dict(bgcolor="#1c2128", bordercolor="#30363d", font_size=13),
)

_GRID = dict(
    showgrid=True,
    gridwidth=1,
    gridcolor="#21262d",
    zeroline=False,
)


# ── Utility formatters ────────────────────────────────────────────────────────

def format_lap_time(seconds):
    """Format seconds as MM:SS.mmm for tooltips."""
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{minutes:02}:{sec:02}.{millis:03}"


def format_seconds_to_mmss(seconds):
    """Format seconds as MM:SS for axis labels."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02}:{secs:02}"


# ── Pirelli compound colours ──────────────────────────────────────────────────

COMPOUND_COLORS = {
    "SOFT": "#e8002d",
    "MEDIUM": "#ffd600",
    "HARD": "#f0f0f0",
    "INTERMEDIATE": "#43b047",
    "WET": "#0067ff",
    "Unknown": "#6e7681",
}


# ── Lap Times ─────────────────────────────────────────────────────────────────

def plot_lap_times(lap_time_df: pd.DataFrame, color_map: dict):
    """
    Line chart of lap times per driver.

    Pit-out laps are rendered as larger diamond markers.
    The overall fastest lap is highlighted with a gold star annotation.
    """
    if lap_time_df.empty:
        st.warning("No lap data available for this session.")
        return None

    lap_time_df = lap_time_df.copy()
    lap_time_df["formatted_lap_time"] = lap_time_df["lap_duration"].apply(format_lap_time)
    lap_time_df["is_pit_out_lap"] = lap_time_df["is_pit_out_lap"].fillna(False).astype(bool)

    # Identify overall fastest lap (excluding pit-out laps)
    clean_laps = lap_time_df[~lap_time_df["is_pit_out_lap"]]
    fastest_idx = clean_laps["lap_duration"].idxmin() if not clean_laps.empty else None
    fastest_row = clean_laps.loc[fastest_idx] if fastest_idx is not None else None

    fig = go.Figure()

    for driver in sorted(lap_time_df["name_acronym"].dropna().unique()):
        driver_data = lap_time_df[lap_time_df["name_acronym"] == driver].sort_values("lap_number")
        color = color_map.get(driver, "#6e7681")

        normal = driver_data[~driver_data["is_pit_out_lap"]]
        pit_out = driver_data[driver_data["is_pit_out_lap"]]

        hover = [
            f"<b>{driver}</b><br>Lap {row['lap_number']}<br>{row['formatted_lap_time']}"
            for _, row in driver_data.iterrows()
        ]

        # Main line
        fig.add_trace(go.Scatter(
            x=driver_data["lap_number"],
            y=driver_data["lap_duration"],
            mode="lines",
            name=driver,
            line=dict(color=color, width=2.5),
            hoverinfo="text",
            hovertext=hover,
            legendgroup=driver,
        ))

        # Normal lap markers (small, subtle)
        fig.add_trace(go.Scatter(
            x=normal["lap_number"],
            y=normal["lap_duration"],
            mode="markers",
            name=driver,
            marker=dict(color=color, size=5, opacity=0.7),
            hoverinfo="skip",
            showlegend=False,
            legendgroup=driver,
        ))

        # Pit-out lap markers (larger diamond)
        if not pit_out.empty:
            pit_hover = [
                f"<b>{driver}</b><br>Lap {row['lap_number']}<br>{row['formatted_lap_time']}<br>🔧 Out-lap"
                for _, row in pit_out.iterrows()
            ]
            fig.add_trace(go.Scatter(
                x=pit_out["lap_number"],
                y=pit_out["lap_duration"],
                mode="markers",
                name=driver,
                marker=dict(color=color, size=12, symbol="diamond", line=dict(color="white", width=1)),
                hoverinfo="text",
                hovertext=pit_hover,
                showlegend=False,
                legendgroup=driver,
            ))

    # Fastest lap annotation
    if fastest_row is not None:
        fig.add_annotation(
            x=fastest_row["lap_number"],
            y=fastest_row["lap_duration"],
            text=f"⚡ Fastest  {fastest_row['name_acronym']}  {fastest_row['formatted_lap_time']}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#ffd700",
            font=dict(color="#ffd700", size=12, family="'Segoe UI', Arial, sans-serif"),
            bgcolor="#1c2128",
            bordercolor="#ffd700",
            borderwidth=1,
            borderpad=5,
            ax=40,
            ay=-40,
        )

    # Y-axis ticks in MM:SS
    tick_vals = sorted(lap_time_df["lap_duration"].dropna().unique())
    tick_vals = [round(v, 0) for v in tick_vals if 60 <= v <= 200]
    tick_vals = sorted(set(tick_vals))[::5]

    fig.update_layout(
        title="Lap Times by Driver",
        xaxis_title="Lap",
        yaxis_title="Lap Time",
        hovermode="closest",
        height=620,
        legend=dict(
            orientation="v",
            x=1.01, y=1,
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#30363d",
        ),
        **_DARK,
    )
    fig.update_xaxes(**_GRID)
    fig.update_yaxes(
        tickvals=tick_vals,
        ticktext=[format_seconds_to_mmss(v) for v in tick_vals],
        **_GRID,
    )

    return fig


# ── Tire Strategy ─────────────────────────────────────────────────────────────

def plot_tire_strategy(stints_df, color_map: dict):
    """
    Horizontal bar chart of tyre strategy per driver.
    Each bar segment represents one stint, coloured by compound.
    """
    if stints_df.empty:
        st.warning("No stint data available.")
        return None

    fig = go.Figure()

    for _, row in stints_df.iterrows():
        compound = row["compound"].upper()
        acronym = row["name_acronym"]
        bar_color = COMPOUND_COLORS.get(compound, "#6e7681")

        fig.add_trace(go.Bar(
            x=[row["lap_count"]],
            y=[acronym],
            base=row["lap_start"],
            orientation="h",
            marker=dict(
                color=bar_color,
                line=dict(color="#0e1117", width=1.5),
            ),
            hovertemplate=(
                f"<b>{acronym}</b><br>"
                f"Compound: {compound}<br>"
                f"Laps on set: {row['lap_count']}<br>"
                f"Laps {row['lap_start']}–{row['lap_end']}"
                "<extra></extra>"
            ),
            name="",
            showlegend=False,
        ))

    for acronym in stints_df["name_acronym"].unique():
        fig.add_annotation(
            x=-3,
            y=acronym,
            xref="x",
            yref="y",
            text=f"<b>{acronym}</b>",
            showarrow=False,
            font=dict(color=color_map.get(acronym, "#c9d1d9"), size=12),
            align="right",
        )

    layout = {**_DARK, "margin": dict(l=120, t=80, b=60, r=40)}
    fig.update_layout(
        title="Tyre Strategy by Driver",
        xaxis_title="Lap Number",
        yaxis_title="",
        barmode="stack",
        height=600,
        **layout,
    )
    fig.update_yaxes(showticklabels=False, **_GRID)
    fig.update_xaxes(**_GRID)

    return fig


# ── Tyre Degradation ──────────────────────────────────────────────────────────

def plot_tyre_degradation(deg_df: pd.DataFrame, color_map: dict):
    """
    Scatter plot of lap time vs. laps on tyre, per compound.
    Includes a linear regression trend line with the degradation rate labelled.
    """
    if deg_df.empty:
        st.warning("No tyre degradation data available for this session.")
        return None

    fig = go.Figure()

    for compound in sorted(deg_df["compound"].unique()):
        c_data = deg_df[deg_df["compound"] == compound].copy()
        compound_upper = compound.upper()
        color = COMPOUND_COLORS.get(compound_upper, "#6e7681")

        driver_col = c_data["name_acronym"] if "name_acronym" in c_data.columns else c_data["driver_number"]

        fig.add_trace(go.Scatter(
            x=c_data["laps_on_tyre"],
            y=c_data["lap_duration"],
            mode="markers",
            name=compound_upper,
            marker=dict(color=color, opacity=0.6, size=8, line=dict(width=0.8, color="#0e1117")),
            customdata=np.stack([driver_col, c_data["lap_number"]], axis=-1),
            hovertemplate=(
                f"<b>{compound_upper}</b><br>"
                "Driver: %{customdata[0]}<br>"
                "Lap: %{customdata[1]}<br>"
                "Laps on tyre: %{x}<br>"
                "Lap time: %{y:.3f}s<extra></extra>"
            ),
        ))

        if len(c_data) >= 3:
            x_vals = c_data["laps_on_tyre"].values
            y_vals = c_data["lap_duration"].values
            coeffs = np.polyfit(x_vals, y_vals, 1)
            trend = np.poly1d(coeffs)
            x_range = np.linspace(x_vals.min(), x_vals.max(), 60)
            deg_per_lap = coeffs[0]

            fig.add_trace(go.Scatter(
                x=x_range,
                y=trend(x_range),
                mode="lines",
                name=f"{compound_upper} ({deg_per_lap:+.3f}s/lap)",
                line=dict(color=color, width=2.5, dash="dot"),
                hoverinfo="skip",
            ))

    fig.update_layout(
        title="Tyre Degradation by Compound",
        xaxis_title="Laps on Tyre",
        yaxis_title="Lap Duration (s)",
        height=540,
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        **_DARK,
    )
    fig.update_xaxes(**_GRID)
    fig.update_yaxes(**_GRID)

    return fig


# ── Sector Times ──────────────────────────────────────────────────────────────

SECTOR_LABELS = {
    "duration_sector_1": "Sector 1",
    "duration_sector_2": "Sector 2",
    "duration_sector_3": "Sector 3",
}


def plot_sector_times(sector_df: pd.DataFrame, color_map: dict):
    """
    Three-panel subplot showing sector times per driver across all laps.
    Each panel shares the x-axis (lap number). A dashed median line per sector
    gives a quick benchmark reference.
    """
    if sector_df.empty:
        st.warning("No sector time data available for this session.")
        return None

    sector_cols = [c for c in ["duration_sector_1", "duration_sector_2", "duration_sector_3"] if c in sector_df.columns]
    if not sector_cols:
        st.warning("Sector columns not available for this session.")
        return None

    name_col = "name_acronym" if "name_acronym" in sector_df.columns else "driver_number"
    drivers = sorted(sector_df[name_col].dropna().unique())
    n = len(sector_cols)

    fig = make_subplots(
        rows=n,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[SECTOR_LABELS[c] for c in sector_cols],
        vertical_spacing=0.06,
    )

    for i, col in enumerate(sector_cols, start=1):
        # Median reference line for this sector
        median_val = sector_df[col].median()
        if pd.notna(median_val):
            fig.add_hline(
                y=median_val,
                line=dict(color="#58a6ff", width=1, dash="dash"),
                opacity=0.4,
                row=i, col=1,
            )

        for driver in drivers:
            d_data = sector_df[sector_df[name_col] == driver].sort_values("lap_number")
            if d_data.empty or d_data[col].isna().all():
                continue

            fig.add_trace(
                go.Scatter(
                    x=d_data["lap_number"],
                    y=d_data[col],
                    mode="lines+markers",
                    name=str(driver),
                    line=dict(color=color_map.get(str(driver), "#6e7681"), width=2),
                    marker=dict(size=4, opacity=0.8),
                    showlegend=(i == 1),
                    legendgroup=driver,
                    hovertemplate=(
                        f"<b>{driver}</b><br>"
                        f"{SECTOR_LABELS[col]}: %{{y:.3f}}s<br>"
                        "Lap: %{x}<extra></extra>"
                    ),
                ),
                row=i, col=1,
            )

        fig.update_yaxes(title_text="Time (s)", row=i, col=1, **_GRID)

    fig.update_xaxes(title_text="Lap", row=n, col=1, **_GRID)

    fig.update_layout(
        title="Sector Times by Driver",
        height=280 * n,
        hovermode="closest",
        legend=dict(orientation="v", x=1.01, y=1, bgcolor="rgba(0,0,0,0)", bordercolor="#30363d"),
        **_DARK,
    )

    # Style subplot title fonts to match theme
    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(size=14, color="#8b949e", family="'Segoe UI', Arial, sans-serif")

    return fig


# ── Pit Stop Durations ────────────────────────────────────────────────────────

def plot_pit_stop(pit_stop_df: pd.DataFrame, color_map: dict):
    """
    Lollipop chart of pit stop durations per driver.

    Each dot is one pit stop event. Drivers are sorted fastest-to-slowest by
    their best stop. A stem line runs from the y-axis to the dot for readability.
    Lap numbers are annotated directly on each dot. A dashed vertical line marks
    the field average.
    """
    if pit_stop_df.empty:
        st.warning("No pit stop data available for this session.")
        return None

    pit_stop_df = pit_stop_df.copy()
    pit_stop_df["driver_number"] = pit_stop_df["driver_number"].astype(str)

    # Sort: fastest best-stop at the top
    best_per_driver = pit_stop_df.groupby("name_acronym")["pit_duration"].min()
    driver_order = best_per_driver.sort_values(ascending=True).index.tolist()
    avg_duration = pit_stop_df["pit_duration"].mean()

    fig = go.Figure()

    for driver in driver_order:
        d_data = pit_stop_df[pit_stop_df["name_acronym"] == driver].sort_values("pit_duration")
        color = color_map.get(driver, "#6e7681")

        for stop_num, (_, row) in enumerate(d_data.iterrows(), start=1):
            duration = row["pit_duration"]
            lap = int(row["lap_number"])

            # Stem: horizontal line from 0 to the dot
            fig.add_trace(go.Scatter(
                x=[0, duration],
                y=[driver, driver],
                mode="lines",
                line=dict(color=color, width=2, dash="solid"),
                opacity=0.35,
                showlegend=False,
                hoverinfo="skip",
            ))

            # Dot
            fig.add_trace(go.Scatter(
                x=[duration],
                y=[driver],
                mode="markers+text",
                marker=dict(color=color, size=18, line=dict(color="white", width=1.5)),
                text=f"L{lap}",
                textposition="middle center",
                textfont=dict(color="white", size=9, family="'Segoe UI', Arial, sans-serif"),
                name=driver,
                showlegend=(stop_num == 1),
                legendgroup=driver,
                hovertemplate=(
                    f"<b>{driver}</b><br>"
                    f"Stop {stop_num}<br>"
                    f"Lap: {lap}<br>"
                    f"Duration: {duration:.3f}s<extra></extra>"
                ),
            ))

    # Field average reference line
    fig.add_vline(
        x=avg_duration,
        line=dict(color="#58a6ff", width=1.5, dash="dash"),
        annotation_text=f"Field avg  {avg_duration:.2f}s",
        annotation_position="top right",
        annotation_font=dict(color="#58a6ff", size=12),
    )

    row_height = 52
    fig.update_layout(
        title="Pit Stop Durations by Driver",
        xaxis_title="Time in Pit Lane (s)",
        yaxis_title="",
        height=max(420, row_height * len(driver_order) + 140),
        hovermode="closest",
        legend=dict(orientation="v", x=1.01, y=1, bgcolor="rgba(0,0,0,0)", bordercolor="#30363d"),
        **_DARK,
    )
    fig.update_xaxes(rangemode="tozero", **_GRID)
    fig.update_yaxes(categoryorder="array", categoryarray=driver_order, **_GRID)

    return fig
