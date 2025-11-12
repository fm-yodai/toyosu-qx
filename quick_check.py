#!/usr/bin/env python3
"""
Quick simulation results checker.

Usage:
    python quick_check.py <run_id>
    python quick_check.py $(ls -t data/runs/ | head -1)  # Check latest run
"""

import sys
from pathlib import Path

import pandas as pd


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Try to find the latest run
        runs_dir = Path("data/runs")
        if runs_dir.exists():
            runs = sorted(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            if runs:
                run_id = runs[0].name
                print(f"Using latest run: {run_id}\n")
            else:
                print("Usage: python quick_check.py <run_id>")
                print("No runs found in data/runs/")
                sys.exit(1)
        else:
            print("Usage: python quick_check.py <run_id>")
            sys.exit(1)
    else:
        run_id = sys.argv[1]

    run_dir = Path(f"data/runs/{run_id}")
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    # Load data
    kpi_df = pd.read_parquet(run_dir / "kpi.parquet")
    events_df = pd.read_parquet(run_dir / "events.parquet")

    print("=" * 50)
    print(f"Simulation Results: {run_id}")
    print("=" * 50)

    # System metrics
    print("\n📊 System Performance:")
    system = kpi_df[kpi_df["metric"].str.startswith("system_")]
    for _, row in system.iterrows():
        metric = row["metric"].replace("system_", "")
        if "distance" in metric:
            print(f"  {metric:25s}: {row['value']:>10.2f} m ({row['value']/1000:.2f} km)")
        else:
            print(f"  {metric:25s}: {row['value']:>10.2f}")

    # Order metrics
    print("\n📦 Order Metrics:")
    orders = kpi_df[
        kpi_df["metric"].str.startswith("lead_time")
        | (kpi_df["metric"] == "fulfillment_rate")
    ]
    for _, row in orders.iterrows():
        if "sec" in row["metric"]:
            print(
                f"  {row['metric']:25s}: {row['value']:>8.0f}s ({row['value']/60:>6.1f}min)"
            )
        else:
            print(f"  {row['metric']:25s}: {row['value']:>9.1%}")

    # Tare utilization summary
    print("\n🚛 Tare Utilization:")
    tare_utils = kpi_df[kpi_df["metric"].str.contains("_utilization")
                        & kpi_df["metric"].str.startswith("tare_")]
    if not tare_utils.empty:
        for _, row in tare_utils.iterrows():
            tare_id = row["metric"].split("_")[1]
            print(f"  {tare_id}: {row['value']:>6.1%}")

    # Average load per trip
    print("\n📦 Average Load per Trip:")
    tare_loads = kpi_df[kpi_df["metric"].str.contains("_avg_load_kg")]
    if not tare_loads.empty:
        for _, row in tare_loads.iterrows():
            tare_id = row["metric"].split("_")[1]
            load_pct = (row["value"] / 200) * 100
            print(f"  {tare_id}: {row['value']:>6.1f}kg ({load_pct:>5.1f}% of capacity)")

    # Event summary
    print("\n📝 Event Summary:")
    print(f"  Total events: {len(events_df)}")
    event_counts = events_df["event"].value_counts()
    for event, count in event_counts.items():
        print(f"    {event:20s}: {count:>6d}")

    # Time range
    sim_duration = events_df["ts"].max() - events_df["ts"].min()
    print(f"\n⏱️  Simulation Duration:")
    print(f"  {sim_duration:.0f}s ({sim_duration/3600:.2f}h)")

    print("\n" + "=" * 50)
    print(f"\nDetailed data available at: {run_dir}")


if __name__ == "__main__":
    main()
