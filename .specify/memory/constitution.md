<!--
  Sync Impact Report
  ==================
  Version change: 0.0.0 → 1.0.0 (MAJOR: initial constitution from template)

  Modified principles: N/A (initial creation)

  Added sections:
  - Core Principles (5 principles)
    - I. Reproducibility-First
    - II. Fair Comparison
    - III. Quantitative KPI-Driven
    - IV. Python Stack Unity
    - V. Synthetic Data Only
  - Experimental Constraints
  - Output Management
  - Governance

  Removed sections: N/A

  Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ compatible (no principle-specific references)
  - .specify/templates/tasks-template.md: ✅ compatible (no principle-specific references)
  - .specify/templates/commands/*.md: N/A (directory does not exist)

  Follow-up TODOs: None
-->

# 豊洲QX Constitution

## Core Principles

### I. Reproducibility-First

All numerical experiments MUST be fully reproducible.

- Random seed MUST be fixed and recorded for every simulation run
- All parameters (scenario, layout, demand profile, congestion coefficients) MUST be logged
- Every run MUST output `events`, `kpi`, and `meta` files for later reconstruction
- Batch execution MUST support multiple phases and seeds with automated comparison

**Rationale**: Research validity depends on reproducibility. Without complete parameter and
seed preservation, results cannot be verified or extended by future work.

### II. Fair Comparison

All optimization methods MUST be evaluated under identical conditions.

- Same scenario × same seed MUST be applied across all compared methods
- Methods compared: (1) Rule-based baseline, (2) Classical optimization,
  (3) Quantum annealing, (4) QAOA (gate-based quantum)
- Evaluation MUST include multiple iterations to report mean and variance
- No method-specific tuning that cannot be applied to others

**Rationale**: Unfair comparisons invalidate conclusions. Equal conditions ensure that
observed differences stem from method characteristics, not experimental setup.

### III. Quantitative KPI-Driven

Decisions MUST be supported by measurable, quantitative KPIs.

- Required KPIs: utilization rate, average load factor, travel distance, lead time
  distribution (mean/95th percentile), split delivery rate, waiting inventory time,
  unmet demand rate, computation time, replanning cycle
- All KPIs MUST be computed from logged event data
- Comparative reports MUST include KPI tables, graphs, and statistical summaries

**Rationale**: Qualitative assessments are insufficient for operational decisions.
Quantifiable metrics enable objective comparison and clear improvement targets.

### IV. Python Stack Unity

Research phase code MUST use a unified Python stack.

- Simulation: SimPy
- Data processing: Polars (preferred), Pandas (if necessary)
- Visualization: Plotly, marimo (for interactive notebooks)
- Reports: Auto-generated HTML with KPI tables and comparison graphs
- No mixing of multiple language ecosystems in the research phase

**Rationale**: A unified stack reduces integration overhead, simplifies dependency
management, and ensures all team members can contribute without language barriers.

### V. Synthetic Data Only

All experiments MUST use synthetic (generated) data exclusively.

- No real operational data or PII from 豊洲市場
- Demand profiles generated via rule-based random generation (time-band intensity,
  S/M/L basket sizes, destination distribution)
- 2D layouts with nodes and coordinates MUST be generalized, not actual floor plans

**Rationale**: Privacy protection and legal compliance. Synthetic data also enables
controlled experiments with known ground truth for validation.

## Experimental Constraints

The following constraints define project boundaries:

- **No production infrastructure**: This project focuses on research validation only
- **No complex UI**: Visualization limited to simulation outputs and reports
- **No real-time systems**: All simulations run in batch mode for reproducibility
- **Simulation granularity**: Second-level time steps for turret state
  (idle/load/move), position (x,y), and velocity
- **Animation output**: Each run MUST produce a 2D animation (video or HTML)
  showing turret state and movement at 1-second intervals

## Output Management

Deliverables and output artifacts MUST follow these standards:

- **Per-run outputs**: `events` (simulation trace), `kpi` (computed metrics),
  `meta` (parameters, seed, timestamp)
- **Comparison reports**: HTML format with KPI tables, graphs, and conclusion summary
- **Animation**: 2D visualization of turret state/position/movement per run
- **Scenario definitions**: Stored in a reproducible format with version control
- **Insight memo**: Recommendations for joint operation initiation conditions,
  quantum applicability guidelines

## Governance

This constitution governs all development and experimental activities in the project.

- This constitution SUPERSEDES ad-hoc practices and informal agreements
- Amendments require: (1) documented rationale, (2) team review, (3) version increment
- Version follows semantic versioning:
  - MAJOR: Principle removal or incompatible redefinition
  - MINOR: New principle or section addition
  - PATCH: Clarifications and wording improvements
- All pull requests MUST verify compliance with these principles
- Complexity beyond what is stated here MUST be justified in writing

**Version**: 1.0.0 | **Ratified**: 2025-11-29 | **Last Amended**: 2025-11-29
