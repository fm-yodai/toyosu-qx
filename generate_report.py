#!/usr/bin/env python3
"""
Generate HTML visualization report for simulation results.

Usage:
    python generate_report.py <run_id>
    python generate_report.py 2025-11-11_084402Z
    python generate_report.py 2025-11-11_084402Z --scenario config/scenario/default.yaml
"""

import argparse
import sys
from pathlib import Path

import yaml

from sim.viz import (
    create_demand_heatmap,
    create_delivery_sankey,
    create_grid_animation,
    create_kpi_dashboard,
    create_tare_animation,
    create_tare_utilization_heatmap,
)


def load_scenario(scenario_path: str) -> dict:
    """
    Load scenario configuration from YAML file.

    Args:
        scenario_path: Path to scenario YAML file

    Returns:
        Scenario configuration dictionary
    """
    with open(scenario_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_node_coordinates(scenario_path: str) -> dict[str, tuple[int, int]]:
    """
    Load node grid coordinates from scenario file.

    Args:
        scenario_path: Path to scenario YAML file

    Returns:
        Dictionary mapping node_id to (x, y) grid cell coordinates
    """
    scenario = load_scenario(scenario_path)

    node_coords = {}
    for node in scenario.get("nodes", []):
        node_coords[node["id"]] = (int(node["x"]), int(node["y"]))

    return node_coords


def load_grid_config(scenario_path: str) -> dict:
    """
    Load grid configuration from scenario file.

    Args:
        scenario_path: Path to scenario YAML file

    Returns:
        Grid configuration (width, height, cell_size_m)
    """
    scenario = load_scenario(scenario_path)

    grid_config = scenario.get("grid", {})
    return {
        "width": grid_config.get("width", 30),
        "height": grid_config.get("height", 30),
        "cell_size_m": grid_config.get("cell_size_m", 10.0),
    }


def generate_report(run_id: str, scenario_path: str | None = None, data_dir: str = "data/runs") -> None:
    """
    Generate comprehensive HTML report for a simulation run.

    Args:
        run_id: Simulation run identifier
        scenario_path: Path to scenario file (for node coordinates)
        data_dir: Base directory for run data
    """
    run_path = Path(data_dir) / run_id

    if not run_path.exists():
        print(f"Error: Run directory not found: {run_path}")
        sys.exit(1)

    print(f"Generating report for: {run_id}")
    print(f"Data directory: {run_path}")

    # Load node coordinates and grid config if scenario provided
    node_coords = {}
    grid_config = {"width": 30, "height": 30, "cell_size_m": 10.0}
    if scenario_path and Path(scenario_path).exists():
        node_coords = load_node_coordinates(scenario_path)
        grid_config = load_grid_config(scenario_path)
        print(f"Loaded {len(node_coords)} node coordinates from {scenario_path}")
        print(f"Grid: {grid_config['width']}x{grid_config['height']} cells ({grid_config['cell_size_m']}m/cell)")
    else:
        print("Warning: No scenario file provided. Animation will be skipped.")

    # Generate visualizations
    print("\n=== Generating Visualizations ===")

    # 1. KPI Dashboard
    print("1. Creating KPI dashboard...")
    try:
        fig_dashboard = create_kpi_dashboard(run_id, data_dir)
        dashboard_path = run_path / "dashboard.html"
        fig_dashboard.write_html(dashboard_path)
        print(f"   Saved: {dashboard_path}")
    except Exception as e:
        print(f"   Error creating dashboard: {e}")

    # 2. Demand Heatmap
    print("2. Creating demand heatmap...")
    try:
        fig_demand = create_demand_heatmap(run_id, data_dir)
        demand_path = run_path / "heatmap_demand.html"
        fig_demand.write_html(demand_path)
        print(f"   Saved: {demand_path}")
    except Exception as e:
        print(f"   Error creating demand heatmap: {e}")

    # 3. Tare Utilization Heatmap
    print("3. Creating tare utilization heatmap...")
    try:
        fig_util = create_tare_utilization_heatmap(run_id, data_dir)
        util_path = run_path / "heatmap_utilization.html"
        fig_util.write_html(util_path)
        print(f"   Saved: {util_path}")
    except Exception as e:
        print(f"   Error creating utilization heatmap: {e}")

    # 4. Delivery Sankey (2-layer)
    print("4. Creating 2-layer Sankey diagram...")
    try:
        fig_sankey2 = create_delivery_sankey(run_id, data_dir, flow_type="2-layer")
        sankey2_path = run_path / "sankey_2layer.html"
        fig_sankey2.write_html(sankey2_path)
        print(f"   Saved: {sankey2_path}")
    except Exception as e:
        print(f"   Error creating 2-layer Sankey: {e}")

    # 5. Delivery Sankey (3-layer)
    print("5. Creating 3-layer Sankey diagram...")
    try:
        fig_sankey3 = create_delivery_sankey(run_id, data_dir, flow_type="3-layer")
        sankey3_path = run_path / "sankey_3layer.html"
        fig_sankey3.write_html(sankey3_path)
        print(f"   Saved: {sankey3_path}")
    except Exception as e:
        print(f"   Error creating 3-layer Sankey: {e}")

    # 6. Tare Grid Animation (only if node coordinates available)
    if node_coords:
        print("6. Creating tare grid animation...")
        try:
            fig_anim = create_grid_animation(
                run_id,
                node_coords,
                grid_width=grid_config["width"],
                grid_height=grid_config["height"],
                cell_size_m=grid_config["cell_size_m"],
                data_dir=data_dir,
            )
            anim_path = run_path / "animation_grid.html"
            fig_anim.write_html(anim_path)
            print(f"   Saved: {anim_path}")
        except Exception as e:
            print(f"   Error creating grid animation: {e}")
    else:
        print("6. Skipping grid animation (no node coordinates)")

    # Generate comprehensive report
    print("\n=== Generating Comprehensive Report ===")
    report_path = run_path / "report.html"
    _generate_comprehensive_html(run_id, run_path, report_path, node_coords, grid_config)
    print(f"Saved comprehensive report: {report_path}")

    print(f"\n✓ Report generation complete!")
    print(f"  Main report: {report_path}")


def _generate_comprehensive_html(
    run_id: str,
    run_path: Path,
    output_path: Path,
    node_coords: dict,
    grid_config: dict,
) -> None:
    """Generate a single HTML file with all visualizations embedded."""
    from sim.viz import (
        create_demand_heatmap,
        create_delivery_sankey,
        create_grid_animation,
        create_kpi_dashboard,
        create_tare_utilization_heatmap,
    )

    html_parts = []

    # Header
    html_parts.append(
        f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Simulation Report: {run_id}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 40px;
            border-bottom: 2px solid #ccc;
            padding-bottom: 5px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .timestamp {{
            color: #888;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>Toyosu-QX Simulation Report</h1>
    <p class="timestamp">Run ID: <strong>{run_id}</strong></p>
    <p class="timestamp">Generated: {Path(output_path).stat().st_mtime if output_path.exists() else 'N/A'}</p>
"""
    )

    # Dashboard
    html_parts.append('<div class="section"><h2>KPI Dashboard</h2>')
    try:
        fig = create_kpi_dashboard(run_id, str(run_path.parent))
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    except Exception as e:
        html_parts.append(f"<p>Error: {e}</p>")
    html_parts.append("</div>")

    # Demand Heatmap
    html_parts.append('<div class="section"><h2>Demand Heatmap</h2>')
    try:
        fig = create_demand_heatmap(run_id, str(run_path.parent))
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    except Exception as e:
        html_parts.append(f"<p>Error: {e}</p>")
    html_parts.append("</div>")

    # Utilization Heatmap
    html_parts.append('<div class="section"><h2>Tare Utilization Heatmap</h2>')
    try:
        fig = create_tare_utilization_heatmap(run_id, str(run_path.parent))
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    except Exception as e:
        html_parts.append(f"<p>Error: {e}</p>")
    html_parts.append("</div>")

    # Sankey 2-layer
    html_parts.append('<div class="section"><h2>Delivery Flow: Wholesaler → Retailer</h2>')
    try:
        fig = create_delivery_sankey(run_id, str(run_path.parent), flow_type="2-layer")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    except Exception as e:
        html_parts.append(f"<p>Error: {e}</p>")
    html_parts.append("</div>")

    # Sankey 3-layer
    html_parts.append('<div class="section"><h2>Delivery Flow: Wholesaler → Tare → Retailer</h2>')
    try:
        fig = create_delivery_sankey(run_id, str(run_path.parent), flow_type="3-layer")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    except Exception as e:
        html_parts.append(f"<p>Error: {e}</p>")
    html_parts.append("</div>")

    # Grid Animation (if available)
    if node_coords:
        html_parts.append('<div class="section"><h2>Tare Movement on Grid</h2>')
        html_parts.append('<p>Tares move along corridors (horizontal/vertical only - Manhattan distance)</p>')
        try:
            fig = create_grid_animation(
                run_id,
                node_coords,
                grid_width=grid_config.get("width", 30),
                grid_height=grid_config.get("height", 30),
                cell_size_m=grid_config.get("cell_size_m", 10.0),
                data_dir=str(run_path.parent),
            )
            html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        except Exception as e:
            html_parts.append(f"<p>Error: {e}</p>")
        html_parts.append("</div>")

    # Footer
    html_parts.append(
        """
</body>
</html>
"""
    )

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate visualization report for simulation results")
    parser.add_argument("run_id", help="Simulation run ID (e.g., 2025-11-11_084402Z)")
    parser.add_argument(
        "--scenario",
        default=None,
        help="Path to scenario YAML file (for node coordinates)",
    )
    parser.add_argument(
        "--data-dir",
        default="data/runs",
        help="Base directory for run data",
    )

    args = parser.parse_args()

    generate_report(args.run_id, args.scenario, args.data_dir)


if __name__ == "__main__":
    main()
