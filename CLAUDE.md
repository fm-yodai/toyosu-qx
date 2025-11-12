# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Toyosu-QX** is a discrete event simulation (DES) system for optimizing turret truck (ターレ) operations at Toyosu Market in Tokyo. The simulation models delivery logistics between wholesalers (仲卸) and retailers (小売) to reduce idle time, improve loading efficiency, and minimize total travel distance.

**Core technology stack**: Python 3.12+, SimPy (discrete event simulation), Plotly (visualization)

**Project phases**:
- **Phase 1** (current): 1-second granularity DES with rule-based planner, 2D visualization, KPI dashboard
- **Phase 2** (future): 10-second optimization tick with OR-Tools/quantum optimization integration

## Key Domain Concepts

This is a Japanese market logistics simulation. Key terms:
- **ターレ (Tare)**: Small delivery trucks with 200kg max capacity
- **仲卸**: Wholesalers who own tare trucks
- **小売**: Retailers (delivery destinations)
- **オーダ**: Delivery orders in 10/30/50kg lots
- **5分ルール**: If no additional load within 5 minutes (300s), depart with current load
- **混載**: Load consolidation (initially only same-destination allowed)

## Development Commands

The project uses `uv` for Python package management:

```bash
# Run the main simulation
python main.py

# Install dependencies (when pyproject.toml is updated)
uv sync

# Run with specific scenario (future)
python run.py --scenario config/scenario/default.yaml --config config/config.yaml --seed 42
```

## Architecture

### Planned Directory Structure (from architecture_python.md)

```
repo/
  run.py                  # Entry point (args: --scenario, --seed, --config)
  sim/
    engine.py             # SimPy event loop/resources
    planner_rule.py       # Rule-based planner
    demand.py             # Demand generation
    kpi.py                # KPI aggregation
    models.py             # Dataclasses: Tare, Order, Node
  config/
    config.yaml           # α/β coefficients, speed, departure triggers, consolidation policy
    scenario/default.yaml # Demand curves, wholesaler/retailer scale, operating window
  data/
    runs/                 # Output per run_id
      {run_id}/events.parquet
      {run_id}/kpi.parquet
      {run_id}/meta.jsonl
      {run_id}/report.html
  notebooks/
    analysis_marimo.py    # Phase 2: marimo UI (future)
```

### Core Components

1. **Simulation Core** (SimPy-based DES):
   - 1-second granularity event processing
   - Main events: loading start/end, departure/arrival, unloading start/end, trade confirmation
   - Event queue manages time-ordered discrete events

2. **Planner** (Rule-based → Optimization):
   - Phase 1: Simple rules (nearest idle truck, FIFO)
   - Phase 2: Pluggable interface for OR-Tools/QAOA/quantum annealing

3. **Demand Generator**:
   - Time-of-day intensity curves
   - Order generation in S/M/L (10/30/50kg) lots

4. **Logger & KPIs**:
   - Event stream → Parquet
   - KPIs: utilization rate, operating hours, travel distance, average load per trip, lead time distribution (mean/95th%), fulfillment rate, split delivery rate

5. **Visualization** (Plotly):
   - 2D animation replay
   - Time-series dashboard
   - Heatmaps, Sankey diagrams
   - Static HTML export

### Key Parameters (config.yaml)

```yaml
speed_kmph: 8.0           # Average speed in market
alpha_load: 0.3           # Loading time coefficient (s/kg)
beta_load: 10.0           # Loading base time (s)
trade_proc_sec: 30        # Transaction processing time
capacity_kg: 200          # Max tare capacity
depart_trigger:
  min_stay_sec: 300       # 5-minute rule
  min_load_ratio: 0.5     # Example: depart at 50% capacity
consolidation: same_destination_only
window: "04:00-12:00"     # Operating hours
```

### I/O Schema

| File | Key Columns | Notes |
|------|-------------|-------|
| `events.parquet` | ts, run_id, tare_id, node, event, state, load_w, payload | Second-granularity events |
| `kpi.parquet` | run_id, metric, value, window, ts | Utilization, distance, lead time, etc. |
| `meta.jsonl` | run_id, cmdline, config_hash, started_at, ended_at | Reproducibility/audit trail |
| `report.html` | Plotly graphs | Shareable static report |

## KPIs (from project-constitution.md)

**Tare metrics**: utilization rate, operating hours, travel distance, average load per trip (W/200kg)
**Retailer metrics**: lead time distribution (mean/95th%), fulfillment rate, split delivery rate
**Wholesaler metrics**: sales fulfillment rate, inventory waiting time, task queue length
**Social impact**: reduction in duplicate trips/idle time, CO₂ reduction, operational cost reduction

## Simplifications & Assumptions

- No traffic congestion, breakdowns, or parking constraints (Phase 1)
- Uniform speed (8 km/h)
- Linear time model for loading/unloading: t = α·W + β
- Same-destination consolidation only (initially)

## Future Expansion (Phase 2)

- 10-second optimization tick with state snapshots
- Pluggable optimization module (OR-Tools/quantum)
- Dynamic task reassignment
- Multi-destination consolidation
- Traffic/congestion modeling

## Definition of Done (from project-constitution.md)

- All KPIs (§3) reproducible via CSV/dashboard
- Baseline scenario reproduces with consistency checks (demand=supply)
- 10-second optimization **hook/interface** implemented (even if dummy)

## Important Files

- `docs/project-constitution.md`: Project charter with objectives, KPIs, milestones, risks
- `docs/glossary.md`: Domain terminology (Japanese terms with definitions)
- `docs/architecture_python.md`: Technical architecture, directory structure, runtime sequence
