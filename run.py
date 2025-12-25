#!/usr/bin/env python3
"""
Toyosu-QX Simulation Runner

Entry point for running discrete event simulations of tare operations
at Toyosu Market.

Usage:
    python run.py --scenario config/scenario/default.yaml --config config/config.yaml --seed 42
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from sim.demand import DemandGenerator
from sim.engine import SimulationEngine
from sim.kpi import KPIAggregator
from sim.models import EventType, Grid, Node, NodeType, Tare, TareState
from sim.planner_rule import RuleBasedPlanner


def load_yaml(path: str) -> dict:
    """Load YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_run_id() -> str:
    """Generate unique run ID based on timestamp."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d_%H%M%SZ")


def config_hash(config: dict) -> str:
    """Generate hash of configuration for reproducibility."""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:8]


def setup_grid(scenario: dict) -> Grid:
    """Create grid object from scenario configuration."""
    grid_config = scenario.get("grid", {})
    return Grid(
        width=grid_config.get("width", 30),
        height=grid_config.get("height", 30),
        cell_size_m=grid_config.get("cell_size_m", 10.0),
    )


def setup_nodes(scenario: dict) -> dict[str, Node]:
    """Create node objects from scenario configuration."""
    nodes = {}
    for node_data in scenario.get("nodes", []):
        node_type = NodeType.WHOLESALER if node_data["type"] == "wholesaler" else NodeType.RETAILER
        node = Node(
            id=node_data["id"],
            type=node_type,
            x=int(node_data["x"]),  # Grid cell coordinate (integer)
            y=int(node_data["y"]),  # Grid cell coordinate (integer)
            name=node_data.get("name"),
        )
        nodes[node.id] = node
    return nodes


def setup_tares(scenario: dict, config: dict) -> dict[str, Tare]:
    """Create tare objects from scenario configuration."""
    tares = {}
    default_capacity = config.get("capacity_kg", 200)

    for tare_data in scenario.get("tares", []):
        tare = Tare(
            id=tare_data["id"],
            home=tare_data["home"],
            capacity_kg=tare_data.get("capacity_kg", default_capacity),
            state=TareState.IDLE,
            current_node=tare_data["home"],  # Start at home
        )
        tares[tare.id] = tare

    return tares


def run_simulation(
    run_id: str,
    config: dict,
    scenario: dict,
    seed: int | None = None,
) -> tuple[list, dict[str, Tare], dict]:
    """
    Run a single simulation.

    Args:
        run_id: Unique run identifier
        config: Configuration parameters
        scenario: Scenario definition
        seed: Random seed

    Returns:
        Tuple of (events, tares, orders_dict)
    """
    print(f"Initializing simulation: {run_id}")

    # Setup
    grid = setup_grid(scenario)
    nodes = setup_nodes(scenario)
    tares = setup_tares(scenario, config)

    print(f"  Grid: {grid.width}x{grid.height} cells ({grid.cell_size_m}m/cell)")
    print(f"  Nodes: {len(nodes)} ({sum(1 for n in nodes.values() if n.type == NodeType.WHOLESALER)} wholesalers, "
          f"{sum(1 for n in nodes.values() if n.type == NodeType.RETAILER)} retailers)")
    print(f"  Tares: {len(tares)}")

    # Create simulation engine with grid
    engine = SimulationEngine(run_id, config, nodes, tares, grid)

    # Create demand generator
    demand_gen = DemandGenerator(scenario, nodes, seed)

    # Create planner
    planner = RuleBasedPlanner(config, nodes, tares)

    # Generate all orders upfront (batch mode for Phase 1)
    sim_duration = scenario.get("sim_duration_sec", 28800)  # 8 hours default
    print(f"  Duration: {sim_duration}s ({sim_duration/3600:.1f}h)")

    orders = demand_gen.generate_orders(0, sim_duration)
    orders_dict = {o.id: o for o in orders}
    print(f"  Generated orders: {len(orders)}")

    # Event-driven simulation loop
    print("Running simulation...")

    # Schedule order arrivals
    for order in orders:
        engine.env.process(_order_arrival_process(engine, planner, order))

    # Schedule periodic planner execution (every second)
    engine.env.process(_planner_process(engine, planner, sim_duration))

    # Run simulation
    engine.run(until=sim_duration)

    print(f"Simulation complete. Events logged: {len(engine.events)}")

    return engine.get_events(), tares, orders_dict


def _order_arrival_process(engine, planner, order):
    """SimPy process for order arrival."""
    yield engine.env.timeout(order.created_at)

    # Log order generation
    engine.log_event(
        EventType.ORDER_GENERATED,
        payload={
            "order_id": order.id,
            "origin": order.origin,
            "destination": order.destination,
            "weight_kg": order.weight_kg,
        },
    )

    # Add to planner queue
    planner.add_order(order, engine.env.now)


def _planner_process(engine, planner, duration):
    """SimPy process for periodic planner execution."""
    while engine.env.now < duration:
        # Try to assign orders
        assignments = planner.assign_orders(engine.env.now)

        for tare, orders, destination in assignments:
            # Log assignment
            for order in orders:
                engine.log_event(
                    EventType.ORDER_ASSIGNED,
                    tare_id=tare.id,
                    payload={"order_id": order.id},
                )

            # Start tare process
            engine.env.process(engine.tare_process(tare, orders, destination))

        # Wait 1 second before next planning cycle
        yield engine.env.timeout(1)


def save_results(
    run_id: str,
    events: list,
    tares: dict,
    orders: dict,
    config: dict,
    scenario: dict,
    started_at: datetime,
    ended_at: datetime,
) -> Path:
    """Save simulation results to data/runs/{run_id}/."""
    output_dir = Path("data/runs") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save events as parquet
    events_data = []
    for e in events:
        events_data.append({
            "ts": e.ts,
            "run_id": e.run_id,
            "tare_id": e.tare_id,
            "node": e.node,
            "event": e.event.value,
            "state": e.state.value if e.state else None,
            "load_kg": e.load_kg,
            "payload": json.dumps(e.payload) if e.payload else None,
        })

    events_df = pd.DataFrame(events_data)
    events_df.to_parquet(output_dir / "events.parquet", index=False)
    print(f"Saved events: {output_dir / 'events.parquet'}")

    # Compute and save KPIs
    kpi_agg = KPIAggregator(run_id, config)
    metrics = kpi_agg.compute_kpis(events, tares, orders)
    kpi_df = kpi_agg.to_dataframe()
    kpi_df.to_parquet(output_dir / "kpi.parquet", index=False)
    print(f"Saved KPIs: {output_dir / 'kpi.parquet'}")
    print(f"  Total metrics: {len(metrics)}")

    # Save metadata
    meta = {
        "run_id": run_id,
        "config_hash": config_hash({**config, **scenario}),
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": (ended_at - started_at).total_seconds(),
        "num_events": len(events),
        "num_tares": len(tares),
        "num_orders": len(orders),
    }

    with open(output_dir / "meta.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")
    print(f"Saved metadata: {output_dir / 'meta.jsonl'}")

    return output_dir


def print_summary(kpi_df: pd.DataFrame) -> None:
    """Print summary of key metrics."""
    print("\n=== Simulation Summary ===")

    # System-level metrics
    system_metrics = kpi_df[kpi_df["metric"].str.startswith("system_")]
    for _, row in system_metrics.iterrows():
        print(f"  {row['metric']}: {row['value']:.2f}")

    # Order metrics
    order_metrics = kpi_df[kpi_df["metric"].str.startswith("lead_time") | (kpi_df["metric"] == "fulfillment_rate")]
    for _, row in order_metrics.iterrows():
        if "sec" in row["metric"]:
            print(f"  {row['metric']}: {row['value']:.1f}s ({row['value']/60:.1f}min)")
        else:
            print(f"  {row['metric']}: {row['value']:.2%}")

    print("=" * 30)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Toyosu-QX simulation")
    parser.add_argument(
        "--scenario",
        default="config/scenario/default.yaml",
        help="Path to scenario YAML file",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip report generation",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_yaml(args.config)
    scenario = load_yaml(args.scenario)

    # Override seed if specified
    if args.seed is not None:
        scenario["random_seed"] = args.seed

    # Generate run ID
    run_id = create_run_id()

    # Run simulation
    started_at = datetime.now(timezone.utc)
    events, tares, orders = run_simulation(
        run_id,
        config,
        scenario,
        seed=scenario.get("random_seed"),
    )
    ended_at = datetime.now(timezone.utc)

    # Save results
    output_dir = save_results(
        run_id, events, tares, orders, config, scenario, started_at, ended_at
    )

    # Load and print summary
    kpi_df = pd.read_parquet(output_dir / "kpi.parquet")
    print_summary(kpi_df)

    print(f"\nResults saved to: {output_dir}")

    # Generate visualization report
    if not args.no_report:
        print("\n=== Generating Visualization Report ===")
        try:
            from generate_report import generate_report
            generate_report(run_id, args.scenario)
        except Exception as e:
            print(f"Error generating report: {e}")
            print("You can generate the report later by running:")
            print(f"  python generate_report.py {run_id} --scenario {args.scenario}")


if __name__ == "__main__":
    main()
