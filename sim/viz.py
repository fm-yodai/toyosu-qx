"""
Visualization module for Toyosu-QX simulation results.

Provides functions to create interactive visualizations using Plotly:
- Animated 2D view of tare movements
- Sankey diagrams of delivery flows
- Heatmaps of demand patterns and utilization
- Time-series dashboards of KPIs
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================================================
# Data Loading and Preprocessing
# ============================================================================

def load_simulation_data(run_id: str, data_dir: str = "data/runs") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load simulation results from disk.

    Args:
        run_id: Simulation run identifier
        data_dir: Base directory for run data

    Returns:
        Tuple of (events_df, kpi_df, metadata)
    """
    run_path = Path(data_dir) / run_id

    # Load events
    events_df = pd.read_parquet(run_path / "events.parquet")

    # Load KPIs
    kpi_df = pd.read_parquet(run_path / "kpi.parquet")

    # Load metadata
    with open(run_path / "meta.jsonl", "r", encoding="utf-8") as f:
        metadata = json.loads(f.readline())

    return events_df, kpi_df, metadata


def parse_event_payload(events_df: pd.DataFrame, parse_json: bool = True) -> pd.DataFrame:
    """
    Parse JSON payload column in events dataframe.

    Args:
        events_df: Events dataframe
        parse_json: If True, parse JSON strings to dicts

    Returns:
        DataFrame with parsed payload column
    """
    df = events_df.copy()

    if parse_json and "payload" in df.columns:
        df["payload"] = df["payload"].apply(
            lambda x: json.loads(x) if pd.notna(x) and x else {}
        )

    return df


def extract_node_coordinates(events_df: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """
    Extract node coordinates from events (if available).

    Note: In the current implementation, node coordinates should be loaded
    from the scenario file. This is a placeholder for extracting from events.

    Args:
        events_df: Events dataframe

    Returns:
        Dictionary mapping node_id to (x, y) coordinates
    """
    # Placeholder: In practice, load from scenario YAML
    # For now, return empty dict
    return {}


# ============================================================================
# Animation: Tare Movement Visualization
# ============================================================================

def create_grid_animation(
    run_id: str,
    node_coords: dict[str, tuple[int, int]],
    grid_width: int = 30,
    grid_height: int = 30,
    cell_size_m: float = 10.0,
    time_bin_sec: int = 1,
    data_dir: str = "data/runs",
) -> go.Figure:
    """
    Create animated scatter plot showing tare movements on a 2D grid.

    The grid displays corridors where tares can only move horizontally
    or vertically (Manhattan distance movement).

    Uses POSITION_UPDATE events for precise per-second position tracking.

    Args:
        run_id: Simulation run identifier
        node_coords: Dictionary mapping node_id to (x, y) grid cell coordinates
        grid_width: Grid width in cells
        grid_height: Grid height in cells
        cell_size_m: Size of each cell in meters
        time_bin_sec: Time interval for animation frames (seconds), default 1
        data_dir: Base directory for run data

    Returns:
        Plotly Figure with animation on grid background
    """
    events_df, _, _ = load_simulation_data(run_id, data_dir)
    events_df = parse_event_payload(events_df)

    # Extract position events - prioritize position_update for per-second tracking
    position_events = events_df[
        (events_df["event"].isin(["position_update", "depart", "arrive", "load_start", "unload_start"])) &
        (events_df["tare_id"].notna())
    ].copy().sort_values(["tare_id", "ts"])

    if position_events.empty:
        print("Warning: No position events found")
        return go.Figure()

    # Extract x, y coordinates from payload (for position_update) or node (for other events)
    def get_x(row):
        if row["event"] == "position_update" and isinstance(row.get("payload"), dict):
            return row["payload"].get("x", 0)
        elif row.get("node") and row["node"] in node_coords:
            return node_coords[row["node"]][0]
        return 0

    def get_y(row):
        if row["event"] == "position_update" and isinstance(row.get("payload"), dict):
            return row["payload"].get("y", 0)
        elif row.get("node") and row["node"] in node_coords:
            return node_coords[row["node"]][1]
        return 0

    position_events["x"] = position_events.apply(get_x, axis=1)
    position_events["y"] = position_events.apply(get_y, axis=1)

    # Bin time for animation frames
    position_events["time_bin"] = (position_events["ts"] // time_bin_sec).astype(int) * time_bin_sec

    # For each time bin, get the last position of each tare
    position_by_frame = []
    all_time_bins = sorted(position_events["time_bin"].unique())

    for tare_id in position_events["tare_id"].unique():
        tare_positions = position_events[position_events["tare_id"] == tare_id].sort_values("ts")

        for time_bin in all_time_bins:
            # Get the last known position at or before this time bin
            positions_before = tare_positions[tare_positions["ts"] <= time_bin + time_bin_sec]
            if not positions_before.empty:
                last_pos = positions_before.iloc[-1]
                position_by_frame.append({
                    "tare_id": tare_id,
                    "time_bin": time_bin,
                    "x": last_pos["x"],
                    "y": last_pos["y"],
                    "state": last_pos.get("state", ""),
                    "load_kg": last_pos.get("load_kg"),
                })

    frame_df = pd.DataFrame(position_by_frame)

    if frame_df.empty:
        print("Warning: No frame data generated")
        return go.Figure()

    # Create animation
    fig = px.scatter(
        frame_df,
        x="x",
        y="y",
        animation_frame="time_bin",
        animation_group="tare_id",
        color="tare_id",
        hover_name="tare_id",
        hover_data={
            "state": True,
            "load_kg": True,
            "x": ":.2f",
            "y": ":.2f",
            "time_bin": False,
        },
        title=f"Tare Movement on Grid: {run_id}",
        labels={"x": "X (grid cell)", "y": "Y (grid cell)"},
    )

    # Add grid lines (corridors)
    for i in range(grid_width + 1):
        fig.add_shape(
            type="line",
            x0=i - 0.5, y0=-0.5, x1=i - 0.5, y1=grid_height - 0.5,
            line=dict(color="lightgray", width=1, dash="dot"),
            layer="below",
        )
    for j in range(grid_height + 1):
        fig.add_shape(
            type="line",
            x0=-0.5, y0=j - 0.5, x1=grid_width - 0.5, y1=j - 0.5,
            line=dict(color="lightgray", width=1, dash="dot"),
            layer="below",
        )

    # Set fixed axis ranges for grid
    fig.update_xaxes(range=[-1, grid_width], dtick=5, showgrid=False)
    fig.update_yaxes(range=[-1, grid_height], dtick=5, showgrid=False)

    # Make aspect ratio 1:1
    fig.update_layout(
        width=900,
        height=900,
        xaxis=dict(scaleanchor="y", scaleratio=1),
    )

    # Add node markers (wholesalers and retailers)
    wholesalers = {n: c for n, c in node_coords.items() if n.startswith("W")}
    retailers = {n: c for n, c in node_coords.items() if n.startswith("R")}

    # Wholesalers (blue squares)
    for node_id, (x, y) in wholesalers.items():
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers+text",
                marker=dict(size=20, color="blue", symbol="square", opacity=0.7),
                text=[node_id],
                textposition="top center",
                textfont=dict(size=10, color="blue"),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Wholesaler: {node_id}<br>Grid: ({x}, {y})",
            )
        )

    # Retailers (green diamonds)
    for node_id, (x, y) in retailers.items():
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers+text",
                marker=dict(size=16, color="green", symbol="diamond", opacity=0.7),
                text=[node_id],
                textposition="top center",
                textfont=dict(size=10, color="green"),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Retailer: {node_id}<br>Grid: ({x}, {y})",
            )
        )

    # Add legend annotation
    fig.add_annotation(
        text="◼ Wholesaler  ◆ Retailer  ● Tare",
        xref="paper", yref="paper",
        x=0.5, y=1.02,
        showarrow=False,
        font=dict(size=12),
    )

    return fig


def create_tare_animation(
    run_id: str,
    node_coords: dict[str, tuple[float, float]],
    time_bin_sec: int = 60,
    data_dir: str = "data/runs",
) -> go.Figure:
    """
    Create animated scatter plot showing tare movements over time.

    Args:
        run_id: Simulation run identifier
        node_coords: Dictionary mapping node_id to (x, y) coordinates
        time_bin_sec: Time interval for animation frames (seconds)
        data_dir: Base directory for run data

    Returns:
        Plotly Figure with animation
    """
    events_df, _, _ = load_simulation_data(run_id, data_dir)
    events_df = parse_event_payload(events_df)

    # Extract position events
    position_events = events_df[
        (events_df["event"].isin(["depart", "arrive", "load_start", "unload_start"])) &
        (events_df["tare_id"].notna()) &
        (events_df["node"].notna())
    ].copy()

    if position_events.empty:
        print("Warning: No position events found")
        return go.Figure()

    # Add coordinates
    position_events["x"] = position_events["node"].map(lambda n: node_coords.get(n, (0, 0))[0])
    position_events["y"] = position_events["node"].map(lambda n: node_coords.get(n, (0, 0))[1])

    # Bin time for animation frames
    position_events["time_bin"] = (position_events["ts"] // time_bin_sec) * time_bin_sec
    position_events["time_label"] = position_events["time_bin"].apply(
        lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}"
    )

    # Create animation
    fig = px.scatter(
        position_events,
        x="x",
        y="y",
        animation_frame="time_bin",
        animation_group="tare_id",
        color="tare_id",
        hover_name="tare_id",
        hover_data={
            "node": True,
            "state": True,
            "load_kg": True,
            "x": False,
            "y": False,
            "time_bin": False,
        },
        title=f"Tare Movement Animation: {run_id}",
        labels={"x": "X Coordinate (m)", "y": "Y Coordinate (m)"},
    )

    # Set fixed axis ranges
    x_coords = [c[0] for c in node_coords.values()]
    y_coords = [c[1] for c in node_coords.values()]
    x_range = [min(x_coords) - 50, max(x_coords) + 50] if x_coords else [0, 500]
    y_range = [min(y_coords) - 50, max(y_coords) + 50] if y_coords else [0, 500]

    fig.update_xaxes(range=x_range)
    fig.update_yaxes(range=y_range)

    # Make aspect ratio 1:1
    fig.update_layout(
        width=900,
        height=700,
        xaxis=dict(scaleanchor="y", scaleratio=1),
    )

    # Add background nodes
    for node_id, (x, y) in node_coords.items():
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers+text",
                marker=dict(size=12, color="gray", symbol="square", opacity=0.5),
                text=[node_id],
                textposition="top center",
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Node: {node_id}",
            )
        )

    return fig


# ============================================================================
# Sankey Diagram: Delivery Flow Visualization
# ============================================================================

def create_delivery_sankey(
    run_id: str,
    data_dir: str = "data/runs",
    flow_type: str = "2-layer",  # "2-layer" or "3-layer"
) -> go.Figure:
    """
    Create Sankey diagram showing delivery flows.

    Args:
        run_id: Simulation run identifier
        data_dir: Base directory for run data
        flow_type: "2-layer" (wholesaler->retailer) or "3-layer" (wholesaler->tare->retailer)

    Returns:
        Plotly Figure with Sankey diagram
    """
    events_df, _, _ = load_simulation_data(run_id, data_dir)
    events_df = parse_event_payload(events_df)

    if flow_type == "2-layer":
        return _create_2layer_sankey(events_df, run_id)
    elif flow_type == "3-layer":
        return _create_3layer_sankey(events_df, run_id)
    else:
        raise ValueError(f"Invalid flow_type: {flow_type}")


def _create_2layer_sankey(events_df: pd.DataFrame, run_id: str) -> go.Figure:
    """Create 2-layer Sankey: wholesaler -> retailer."""
    # Extract deliveries
    deliveries = events_df[events_df["event"] == "order_delivered"].copy()

    if deliveries.empty:
        print("Warning: No deliveries found")
        return go.Figure()

    # Extract origin and destination from payload
    deliveries["wholesaler"] = deliveries["payload"].apply(lambda p: p.get("origin", "Unknown"))
    deliveries["retailer"] = deliveries["payload"].apply(lambda p: p.get("destination", "Unknown"))
    deliveries["weight_kg"] = deliveries["payload"].apply(lambda p: p.get("weight_kg", 0))

    # Aggregate flows
    flow_summary = deliveries.groupby(["wholesaler", "retailer"])["weight_kg"].sum().reset_index()

    # Build node list
    wholesalers = sorted(flow_summary["wholesaler"].unique())
    retailers = sorted(flow_summary["retailer"].unique())
    all_nodes = wholesalers + retailers

    # Build links
    flow_summary["source_idx"] = flow_summary["wholesaler"].apply(lambda x: all_nodes.index(x))
    flow_summary["target_idx"] = flow_summary["retailer"].apply(lambda x: all_nodes.index(x))

    # Node colors
    node_colors = ["#1f77b4"] * len(wholesalers) + ["#2ca02c"] * len(retailers)

    # Create Sankey
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes,
                    color=node_colors,
                ),
                link=dict(
                    source=flow_summary["source_idx"].tolist(),
                    target=flow_summary["target_idx"].tolist(),
                    value=flow_summary["weight_kg"].tolist(),
                    color=["rgba(31, 119, 180, 0.3)"] * len(flow_summary),
                ),
            )
        ]
    )

    fig.update_layout(
        title_text=f"Delivery Flow: Wholesaler → Retailer<br><sub>{run_id}</sub>",
        font_size=12,
        height=600,
    )

    return fig


def _create_3layer_sankey(events_df: pd.DataFrame, run_id: str) -> go.Figure:
    """Create 3-layer Sankey: wholesaler -> tare -> retailer."""
    # Extract loading events (wholesaler -> tare)
    loading = events_df[events_df["event"] == "load_start"].copy()
    loading["wholesaler"] = loading["node"]
    loading["weight_kg"] = loading["payload"].apply(lambda p: p.get("weight_kg", 0))

    wholesaler_to_tare = loading.groupby(["wholesaler", "tare_id"])["weight_kg"].sum().reset_index()

    # Extract deliveries (tare -> retailer)
    deliveries = events_df[events_df["event"] == "order_delivered"].copy()
    deliveries["retailer"] = deliveries["payload"].apply(lambda p: p.get("destination", "Unknown"))
    deliveries["weight_kg"] = deliveries["payload"].apply(lambda p: p.get("weight_kg", 0))

    tare_to_retailer = deliveries.groupby(["tare_id", "retailer"])["weight_kg"].sum().reset_index()

    if wholesaler_to_tare.empty or tare_to_retailer.empty:
        print("Warning: Insufficient data for 3-layer Sankey")
        return go.Figure()

    # Build node list
    wholesalers = sorted(wholesaler_to_tare["wholesaler"].unique())
    tares = sorted(wholesaler_to_tare["tare_id"].unique())
    retailers = sorted(tare_to_retailer["retailer"].unique())
    all_nodes = wholesalers + tares + retailers

    # Build links
    flows = []

    # Wholesaler -> Tare
    for _, row in wholesaler_to_tare.iterrows():
        flows.append(
            {
                "source": all_nodes.index(row["wholesaler"]),
                "target": all_nodes.index(row["tare_id"]),
                "value": row["weight_kg"],
            }
        )

    # Tare -> Retailer
    for _, row in tare_to_retailer.iterrows():
        flows.append(
            {
                "source": all_nodes.index(row["tare_id"]),
                "target": all_nodes.index(row["retailer"]),
                "value": row["weight_kg"],
            }
        )

    # Node colors
    node_colors = (
        ["#1f77b4"] * len(wholesalers)  # Blue for wholesalers
        + ["#ff7f0e"] * len(tares)  # Orange for tares
        + ["#2ca02c"] * len(retailers)  # Green for retailers
    )

    # Create Sankey
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes,
                    color=node_colors,
                ),
                link=dict(
                    source=[f["source"] for f in flows],
                    target=[f["target"] for f in flows],
                    value=[f["value"] for f in flows],
                ),
            )
        ]
    )

    fig.update_layout(
        title_text=f"3-Layer Delivery Flow: Wholesaler → Tare → Retailer<br><sub>{run_id}</sub>",
        font_size=10,
        height=700,
    )

    return fig


# ============================================================================
# Heatmap: Demand and Utilization Patterns
# ============================================================================

def create_demand_heatmap(
    run_id: str,
    data_dir: str = "data/runs",
    time_bin_sec: int = 3600,  # 1 hour
) -> go.Figure:
    """
    Create heatmap of demand by time and wholesaler.

    Args:
        run_id: Simulation run identifier
        data_dir: Base directory for run data
        time_bin_sec: Time bin size in seconds

    Returns:
        Plotly Figure with heatmap
    """
    events_df, _, _ = load_simulation_data(run_id, data_dir)
    events_df = parse_event_payload(events_df)

    # Extract order generation events
    orders = events_df[events_df["event"] == "order_generated"].copy()

    if orders.empty:
        print("Warning: No orders found")
        return go.Figure()

    # Extract wholesaler and weight from payload
    orders["wholesaler"] = orders["payload"].apply(lambda p: p.get("origin", "Unknown"))
    orders["weight_kg"] = orders["payload"].apply(lambda p: p.get("weight_kg", 0))

    # Bin time
    orders["time_bin"] = (orders["ts"] // time_bin_sec) * time_bin_sec
    orders["time_label"] = orders["time_bin"].apply(
        lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}"
    )

    # Aggregate
    demand_pivot = orders.pivot_table(
        index="wholesaler",
        columns="time_label",
        values="weight_kg",
        aggfunc="sum",
        fill_value=0,
    )

    # Create heatmap
    fig = px.imshow(
        demand_pivot,
        labels=dict(x="Time", y="Wholesaler", color="Demand (kg)"),
        color_continuous_scale="YlOrRd",
        title=f"Demand Heatmap by Time and Wholesaler<br><sub>{run_id}</sub>",
        aspect="auto",
    )

    fig.update_xaxes(side="bottom")
    fig.update_layout(width=1000, height=500)

    return fig


def create_tare_utilization_heatmap(
    run_id: str,
    data_dir: str = "data/runs",
    time_bin_sec: int = 60,  # 1 minute
) -> go.Figure:
    """
    Create heatmap of tare utilization state over time.

    Args:
        run_id: Simulation run identifier
        data_dir: Base directory for run data
        time_bin_sec: Time bin size in seconds

    Returns:
        Plotly Figure with heatmap
    """
    events_df, _, _ = load_simulation_data(run_id, data_dir)

    # Extract state change events
    state_events = events_df[
        (events_df["tare_id"].notna()) & (events_df["state"].notna())
    ].copy()

    if state_events.empty:
        print("Warning: No tare state events found")
        return go.Figure()

    # Map states to numbers
    state_map = {"idle": 0, "loading": 1, "traveling": 2, "unloading": 3, "trade_proc": 3}
    state_events["state_num"] = state_events["state"].map(state_map)

    # Bin time
    state_events["time_bin"] = (state_events["ts"] // time_bin_sec).astype(int)

    # Get unique tares and time bins
    tare_ids = sorted(state_events["tare_id"].unique())
    max_time_bin = int(state_events["time_bin"].max())

    # Build matrix (forward fill states)
    state_matrix = []
    for tare_id in tare_ids:
        tare_states = state_events[state_events["tare_id"] == tare_id].sort_values("ts")

        # Remove duplicates by keeping last value for each time_bin
        tare_states_unique = tare_states.groupby("time_bin").last()["state_num"]

        # Reindex and forward fill
        full_range = range(0, max_time_bin + 1)
        full_states = tare_states_unique.reindex(full_range, method="ffill", fill_value=0)
        state_matrix.append(full_states.values)

    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=state_matrix,
            x=list(range(max_time_bin + 1)),
            y=tare_ids,
            colorscale=[
                [0.00, "lightgray"],  # idle
                [0.33, "orange"],  # loading
                [0.67, "blue"],  # traveling
                [1.00, "green"],  # unloading
            ],
            colorbar=dict(
                title="State",
                tickvals=[0, 1, 2, 3],
                ticktext=["Idle", "Loading", "Traveling", "Unloading"],
            ),
            hovertemplate="Tare: %{y}<br>Time: %{x} min<br>State: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Tare Utilization Heatmap<br><sub>{run_id}</sub>",
        xaxis_title="Time (min)",
        yaxis_title="Tare ID",
        width=1200,
        height=400,
    )

    return fig


# ============================================================================
# Time Series Dashboard: KPI Trends
# ============================================================================

def create_kpi_dashboard(run_id: str, data_dir: str = "data/runs") -> go.Figure:
    """
    Create comprehensive KPI dashboard with multiple subplots.

    Args:
        run_id: Simulation run identifier
        data_dir: Base directory for run data

    Returns:
        Plotly Figure with dashboard
    """
    events_df, kpi_df, _ = load_simulation_data(run_id, data_dir)

    # Create 2x2 subplots
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "System Utilization",
            "Cumulative Distance",
            "Order Lead Time Distribution",
            "Deliveries by Hour",
        ),
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
    )

    # 1. Utilization (if time-series data available)
    utilization_ts = _calculate_utilization_timeseries(events_df)
    if not utilization_ts.empty:
        fig.add_trace(
            go.Scatter(
                x=utilization_ts["ts"],
                y=utilization_ts["utilization"],
                mode="lines",
                name="Utilization",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )

    # 2. Cumulative distance
    distance_ts = _calculate_cumulative_distance(events_df)
    if not distance_ts.empty:
        fig.add_trace(
            go.Scatter(
                x=distance_ts["ts"],
                y=distance_ts["cumulative_distance_m"],
                mode="lines",
                name="Distance",
                line=dict(color="green", width=2),
                fill="tozeroy",
            ),
            row=1,
            col=2,
        )

    # 3. Lead time distribution
    lead_times = _extract_lead_times(events_df)
    if not lead_times.empty:
        fig.add_trace(
            go.Histogram(x=lead_times["lead_time_sec"] / 60, name="Lead Time", nbinsx=30),
            row=2,
            col=1,
        )

    # 4. Deliveries by hour
    deliveries_by_hour = _calculate_deliveries_by_hour(events_df)
    if not deliveries_by_hour.empty:
        fig.add_trace(
            go.Bar(x=deliveries_by_hour["hour"], y=deliveries_by_hour["count"], name="Deliveries"),
            row=2,
            col=2,
        )

    # Update axes
    fig.update_xaxes(title_text="Time (s)", row=1, col=1)
    fig.update_xaxes(title_text="Time (s)", row=1, col=2)
    fig.update_xaxes(title_text="Lead Time (min)", row=2, col=1)
    fig.update_xaxes(title_text="Hour", row=2, col=2)

    fig.update_yaxes(title_text="Utilization", row=1, col=1)
    fig.update_yaxes(title_text="Distance (m)", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=2)

    fig.update_layout(
        title_text=f"KPI Dashboard<br><sub>{run_id}</sub>",
        showlegend=False,
        height=800,
        width=1400,
    )

    return fig


# ============================================================================
# Helper Functions for Time Series Calculations
# ============================================================================

def _calculate_utilization_timeseries(
    events_df: pd.DataFrame, interval_sec: int = 300
) -> pd.DataFrame:
    """Calculate utilization over time bins."""
    state_events = events_df[(events_df["tare_id"].notna()) & (events_df["state"].notna())].copy()

    if state_events.empty:
        return pd.DataFrame()

    state_events["time_bin"] = (state_events["ts"] // interval_sec) * interval_sec

    utilization_data = []
    for time_bin in sorted(state_events["time_bin"].unique()):
        bin_events = state_events[state_events["time_bin"] == time_bin]
        tare_states = bin_events.groupby("tare_id").last()["state"]

        active = (tare_states != "idle").sum()
        total = len(tare_states)
        util = active / total if total > 0 else 0

        utilization_data.append({"ts": time_bin, "utilization": util})

    return pd.DataFrame(utilization_data)


def _calculate_cumulative_distance(events_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cumulative distance from arrival events."""
    arrivals = events_df[events_df["event"] == "arrive"].copy()

    if arrivals.empty:
        return pd.DataFrame()

    # Extract distance from payload
    arrivals = parse_event_payload(arrivals)
    arrivals["distance_m"] = arrivals["payload"].apply(lambda p: p.get("distance_m", 0))
    arrivals = arrivals.sort_values("ts")
    arrivals["cumulative_distance_m"] = arrivals["distance_m"].cumsum()

    return arrivals[["ts", "cumulative_distance_m"]]


def _extract_lead_times(events_df: pd.DataFrame) -> pd.DataFrame:
    """Extract lead times from delivered orders."""
    deliveries = events_df[events_df["event"] == "order_delivered"].copy()

    if deliveries.empty:
        return pd.DataFrame()

    deliveries = parse_event_payload(deliveries)
    deliveries["lead_time_sec"] = deliveries["payload"].apply(lambda p: p.get("lead_time_sec", 0))

    return deliveries[["ts", "lead_time_sec"]]


def _calculate_deliveries_by_hour(events_df: pd.DataFrame) -> pd.DataFrame:
    """Count deliveries by hour."""
    deliveries = events_df[events_df["event"] == "order_delivered"].copy()

    if deliveries.empty:
        return pd.DataFrame()

    deliveries["hour"] = (deliveries["ts"] / 3600).astype(int)
    deliveries_by_hour = deliveries.groupby("hour").size().reset_index(name="count")

    return deliveries_by_hour
